from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy import func

from database import engine, get_db, Base
import models
import schemas
from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_coordinador,
    require_docente,
)

app = FastAPI(
    title="API de Sistema de Sinópticos - Duoc UC",
    version="2.1.0",
    description="Backend desacoplado para consumo desde cliente React (Sábana de Programación Oficial)"
)

# Configuración de CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas en la base de datos si no existen
Base.metadata.create_all(bind=engine)

# Palabras clave para sugerencias de área docente
PALABRA_CLAVE_AREA = {
    "informatica": ["programacion", "base de datos", "software", "sistemas", "desarrollo", "web"],
    "redes": ["redes", "telecomunicaciones", "cisco", "infraestructura"],
    "matematica": ["matematica", "algebra", "calculo", "estadistica"],
    "administracion": ["administracion", "gestion", "comercio", "logistica", "marketing"],
    "contabilidad": ["contabilidad", "finanzas", "costos", "tributaria"],
    "ingles": ["ingles", "english"],
    "lenguaje": ["lenguaje", "comunicacion", "redaccion"],
}

def area_para_asignatura(nombre_asignatura: str):
    nombre = nombre_asignatura.lower()
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre for p in palabras):
            return area
    return None

LUNES_INICIO_SEMESTRE = date(2026, 8, 10)
SEMANAS_DEFAULT = 17

def fechas_para_bloque(dia_semana: int, semanas: int = SEMANAS_DEFAULT):
    inicio = LUNES_INICIO_SEMESTRE + timedelta(days=dia_semana - 1)
    fin = inicio + timedelta(weeks=semanas)
    return inicio, fin

def obtener_jornada_id(db, jornada):
    valor = (jornada.value if hasattr(jornada, 'value') else str(jornada)).lower()
    fila = db.query(models.Jornada).filter(func.lower(models.Jornada.nombre) == valor).first()
    return fila.id if fila else None
    

@app.get("/")
def home():
    return {"status": "online", "mensaje": "API de Sistema de Sinópticos funcionando correctamente"}


# ===========================================================================
# 1. AUTENTICACIÓN Y SESIÓN
# ===========================================================================

@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(datos: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    user = authenticate_user(db, datos.email, datos.password)

    if not user:
        db.add(models.LoginLog(
            usuario_id=None, email_intentado=str(datos.email).lower(),
            exito=False, motivo_fallo="credenciales inválidas", ip_origen=ip,
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not user.activo:
        db.add(models.LoginLog(
            usuario_id=user.id, email_intentado=str(datos.email).lower(),
            exito=False, motivo_fallo="cuenta inactiva", ip_origen=ip,
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está deshabilitada. Contacte al administrador.",
        )

    db.add(models.LoginLog(
        usuario_id=user.id, email_intentado=str(datos.email).lower(),
        exito=True, motivo_fallo=None, ip_origen=ip,
    ))
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/api/auth/me", response_model=schemas.UsuarioOut)
def obtener_usuario_actual(current_user: models.Usuario = Depends(get_current_user)):
    return current_user


# ===========================================================================
# 2. TABLAS MAESTRAS (Jornadas, Carreras, Planes, Semestres, Profesores, Salas)
# ===========================================================================

@app.get("/api/jornadas", response_model=List[schemas.JornadaOut])
def listar_jornadas(db: Session = Depends(get_db)):
    """Obtiene el catálogo de Jornadas (Diurna, Vespertina, Mixta)."""
    return db.query(models.Jornada).order_by(models.Jornada.id).all()


@app.get("/api/carreras", response_model=List[schemas.CarreraOut])
def listar_carreras(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.Carrera).filter(models.Carrera.activo == True).order_by(models.Carrera.nombre).all()


@app.post("/api/carreras", response_model=schemas.CarreraOut)
def crear_carrera(datos: schemas.CarreraCreate, db: Session = Depends(get_db), _: models.Usuario = Depends(require_coordinador)):
    nueva = models.Carrera(**datos.model_dump())
    db.add(nueva)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una carrera/escuela con ese código.")
    db.refresh(nueva)
    return nueva


@app.get("/api/planes-estudio", response_model=List[schemas.PlanEstudioOut])
def listar_planes_estudio(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.PlanEstudio).filter(models.PlanEstudio.activo == True).all()


@app.get("/api/semestres", response_model=List[schemas.SemestreOut])
def listar_semestres(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.Semestre).filter(models.Semestre.activo == True).order_by(
        models.Semestre.anio.desc(), models.Semestre.numero.desc()
    ).all()


@app.get("/api/asignaturas", response_model=List[schemas.AsignaturaOut])
def listar_asignaturas(carrera_id: Optional[int] = None, db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    query = db.query(models.Asignatura).filter(models.Asignatura.activo == True)
    if carrera_id is not None:
        query = query.join(
            models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
        ).filter(models.PlanEstudio.carrera_id == carrera_id)
    return query.order_by(models.Asignatura.codigo).all()


@app.post("/api/asignaturas", response_model=schemas.AsignaturaOut)
def crear_asignatura(datos: schemas.AsignaturaCreate, db: Session = Depends(get_db), _: models.Usuario = Depends(require_coordinador)):
    nueva = models.Asignatura(**datos.model_dump())
    db.add(nueva)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una asignatura con ese código.")
    db.refresh(nueva)
    return nueva


@app.get("/api/profesores", response_model=List[schemas.ProfesorOut])
def listar_profesores(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.Profesor).filter(models.Profesor.activo == True).order_by(models.Profesor.nombre).all()


@app.get("/api/salas", response_model=List[schemas.SalaOut])
def listar_salas(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.Sala).filter(models.Sala.activo == True).order_by(models.Sala.nombre).all()


@app.get("/api/bloques-horario", response_model=List[schemas.BloqueHorarioOut])
def listar_bloques_horario(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.BloqueHorario).order_by(
        models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
    ).all()


# ===========================================================================
# 3. ALGORITMO Y EDITOR DE SINÓPTICOS
# ===========================================================================

@app.post("/api/sinopticos/generar")
def generar_sinoptico(
    datos: schemas.GenerarSinopticoRequest, 
    db: Session = Depends(get_db), 
    _: models.Usuario = Depends(require_coordinador)
):
    """Generación automática asignando bloques sin choques horarios de forma segura."""
    
    # 1. Validar existencia de asignaturas activas para la carrera/escuela
    asignaturas = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == datos.carrera_id,
        models.Asignatura.activo == True
    ).all()

    if not asignaturas:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontraron asignaturas activas para la carrera ID {datos.carrera_id}."
        )

    # 2. Convertir el valor de jornada de forma segura
    jornada_val = datos.jornada.value if hasattr(datos.jornada, 'value') else str(datos.jornada).lower()

    # 3. CREAR EL SINÓPTICO INCLUYENDO LA JORNADA (Resuelve el error NotNullViolation)
    nuevo_sinoptico = models.Sinoptico(
        carrera_id=datos.carrera_id,
        semestre_id=datos.semestre_id,
        jornada=datos.jornada
    )
    db.add(nuevo_sinoptico)
    db.flush()  # Asigna el nuevo_sinoptico.id
    jornada_id = obtener_jornada_id(db, datos.jornada)

    # 4. Consultar bloques horarios para la jornada indicada
    bloques = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.jornada == jornada_val
    ).order_by(models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio).all()

    if not bloques:
        # Fallback si no encuentra coincidencias estrictas de Enum
        bloques = db.query(models.BloqueHorario).order_by(
            models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
        ).all()

    profesores = db.query(models.Profesor).filter(models.Profesor.activo == True).all()
    salas = db.query(models.Sala).filter(models.Sala.activo == True).all()

    profesor_ocupado = defaultdict(set)
    sala_ocupada = defaultdict(set)

    sin_asignar = []
    profesor_carga = defaultdict(int)
    sala_carga = defaultdict(int)
    bloque_carga = defaultdict(int)

    # 5. Algoritmo de distribución de bloques
    for asignatura in asignaturas:
        area_requerida = area_para_asignatura(asignatura.nombre)
        
        # Ordenar profesores candidatos evitando AttributeError si p.area_docente es None
        candidatos_prof = sorted(profesores, key=lambda p: (
            0 if (area_requerida and p.area_docente and hasattr(p.area_docente, 'value') and p.area_docente.value == area_requerida) else 1,
            profesor_carga[p.id]
        ))
        candidatos_sala = sorted(salas, key=lambda s: sala_carga[s.id])
        candidatos_bloques = sorted(bloques, key=lambda b: bloque_carga[b.id])

        asignado = False
        for b in candidatos_bloques:
            for p in candidatos_prof:
                if b.id in profesor_ocupado[p.id]:
                    continue
                for s in candidatos_sala:
                    if b.id in sala_ocupada[s.id]:
                        continue
                    
                    profesor_ocupado[p.id].add(b.id)
                    sala_ocupada[s.id].add(b.id)
                    profesor_carga[p.id] += 1
                    sala_carga[s.id] += 1
                    bloque_carga[b.id] += 1
                    inicio, fin = fechas_para_bloque(b.dia_semana)

                    item = models.SinopticoItem(
                        sinoptico_id=nuevo_sinoptico.id,
                        asignatura_id=asignatura.id,
                        profesor_id=p.id,
                        sala_id=s.id,
                        bloque_horario_id=b.id,
                        seccion=f"{asignatura.codigo}-001D",
                        id_seccion="24478875",
                        fecha_inicio=inicio,
                        fecha_final=fin,
                        jornada_id=jornada_id,
                    )
                    db.add(item)
                    asignado = True
                    break
                if asignado:
                    break
            if asignado:
                break

        if not asignado:
            sin_asignar.append(asignatura.codigo)

    try:
        db.commit()
        db.refresh(nuevo_sinoptico)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el sinóptico en la base de datos: {str(e)}"
        )

    return {
        "sinoptico_id": nuevo_sinoptico.id,
        "asignaturas_sin_asignar": sin_asignar
    }

@app.get("/api/sinopticos")
def listar_sinopticos(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    filas = (
        db.query(models.Sinoptico, models.Carrera, models.Semestre)
        .join(models.Carrera, models.Sinoptico.carrera_id == models.Carrera.id)
        .join(models.Semestre, models.Sinoptico.semestre_id == models.Semestre.id)
        .order_by(models.Sinoptico.creado_en.desc())
        .all()
    )
    return [
        {
            "id": sinoptico.id,
            "carrera": carrera.nombre,
            "codigo_carrera": carrera.codigo,
            "semestre": f"{semestre.anio}-{semestre.numero}",
            "creado_en": sinoptico.creado_en,
        }
        for sinoptico, carrera, semestre in filas
    ]


@app.get("/api/sinopticos/{sinoptico_id}/eventos")
def eventos_sinoptico(sinoptico_id: int, db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario, models.Jornada)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .outerjoin(models.Jornada, models.SinopticoItem.jornada_id == models.Jornada.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )

    if not filas:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado o sin eventos asignados.")

    eventos = []
    for item, asignatura, profesor, sala, bloque, jornada in filas:
        eventos.append({
            "id": item.id,
            "title": asignatura.nombre,
            "daysOfWeek": [bloque.dia_semana],
            "startTime": bloque.hora_inicio.strftime("%H:%M:%S"),
            "endTime": bloque.hora_fin.strftime("%H:%M:%S"),
            "extendedProps": {
                "codigo": asignatura.codigo,
                "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else "Sin asignar",
                "sala": sala.nombre if sala else "Sin asignar",
                "jornada": jornada.nombre if jornada else bloque.jornada.value,
                "id_seccion": item.id_seccion,
                "seccion": item.seccion,
                "asignatura_id": item.asignatura_id,
                "profesor_id": item.profesor_id,
                "sala_id": item.sala_id,
                "bloque_horario_id": item.bloque_horario_id,
                "jornada_id": item.jornada_id,
                "capacidad_inicial": item.capacidad_inicial,
            }
        })
    return eventos


@app.post("/api/sinopticos/items", response_model=schemas.SinopticoItemOut, status_code=201)
def agregar_item_sinoptico(
    datos: schemas.SinopticoItemCreate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == datos.sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")

    bloque = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.id == datos.bloque_horario_id
    ).first()
    if not bloque:
        raise HTTPException(status_code=404, detail="El bloque horario indicado no existe.")
    inicio, fin = fechas_para_bloque(bloque.dia_semana)

    if datos.profesor_id is not None:
        choque_profesor = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.profesor_id == datos.profesor_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_profesor:
            raise HTTPException(status_code=409, detail="Ese profesor ya tiene otra clase asignada en ese bloque horario.")

    if datos.sala_id is not None:
        choque_sala = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.sala_id == datos.sala_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_sala:
            raise HTTPException(status_code=409, detail="Esa sala ya está ocupada por otra clase en ese bloque horario.")

    campos = datos.model_dump()
    campos["jornada_id"] = campos.get('jornada_id') or obtener_jornada_id(db, sinoptico.jornada)
    nuevo_item = models.SinopticoItem(**campos, fecha_inicio=inicio, fecha_final=fin)
    db.add(nuevo_item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ese profesor o esa sala ya quedaron ocupados en ese horario. Intente de nuevo."
        )
    db.refresh(nuevo_item)
    return nuevo_item


@app.put("/api/sinopticos/items/{item_id}", response_model=schemas.SinopticoItemOut)
def editar_item_sinoptico(
    item_id: int,
    datos: schemas.SinopticoItemUpdate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El bloque de horario indicado no existe.")

    bloque = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.id == datos.bloque_horario_id
    ).first()
    if not bloque:
        raise HTTPException(status_code=404, detail="El bloque horario indicado no existe.")

    if datos.profesor_id is not None:
        choque_profesor = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.id != item_id,
            models.SinopticoItem.profesor_id == datos.profesor_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_profesor:
            raise HTTPException(status_code=409, detail="Ese profesor ya tiene otra clase asignada en ese bloque horario.")

    if datos.sala_id is not None:
        choque_sala = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.id != item_id,
            models.SinopticoItem.sala_id == datos.sala_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_sala:
            raise HTTPException(status_code=409, detail="Esa sala ya está ocupada por otra clase en ese bloque horario.")

    if datos.jornada_id is not None:
        item.jornada_id = datos.jornada_id
    elif item.jornada_id is None:
        item.jornada_id = obtener_jornada_id(db, item.sinoptico.jornada)

    item.asignatura_id = datos.asignatura_id
    item.profesor_id = datos.profesor_id
    item.sala_id = datos.sala_id
    item.bloque_horario_id = datos.bloque_horario_id
    item.id_seccion = datos.id_seccion
    item.seccion = datos.seccion
    item.capacidad_inicial = datos.capacidad_inicial
    item.fecha_inicio, item.fecha_final = fechas_para_bloque(bloque.dia_semana)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Error al guardar el evento por choque de restricciones."
        )
    db.refresh(item)
    return item


@app.patch("/api/sinopticos/items/{item_id}/mover")
def mover_item_sinoptico(
    item_id: int,
    datos: schemas.MoverItemRequest,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Mueve un evento de horario en el calendario mediante Drag & Drop."""
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El bloque de horario indicado no existe.")

    nuevo_bloque = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.dia_semana == datos.dia_semana,
        models.BloqueHorario.hora_inicio == datos.hora_inicio,
        models.BloqueHorario.hora_fin == datos.hora_fin,
        models.BloqueHorario.jornada == datos.jornada,
    ).first()
    if not nuevo_bloque:
        raise HTTPException(
            status_code=404,
            detail="No existe un bloque horario registrado para ese día y módulo."
        )

    if nuevo_bloque.id == item.bloque_horario_id:
        return {"ok": True, "item_id": item.id, "bloque_horario_id": nuevo_bloque.id}

    if item.profesor_id is not None:
        choque_profesor = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.id != item_id,
            models.SinopticoItem.profesor_id == item.profesor_id,
            models.SinopticoItem.bloque_horario_id == nuevo_bloque.id,
        ).first()
        if choque_profesor:
            raise HTTPException(
                status_code=409,
                detail="El profesor de esta clase ya tiene otra clase asignada en ese horario."
            )

    if item.sala_id is not None:
        choque_sala = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.id != item_id,
            models.SinopticoItem.sala_id == item.sala_id,
            models.SinopticoItem.bloque_horario_id == nuevo_bloque.id,
        ).first()
        if choque_sala:
            raise HTTPException(
                status_code=409,
                detail="La sala de esta clase ya está ocupada por otra clase en ese horario."
            )

    item.fecha_inicio, item.fecha_final = fechas_para_bloque(nuevo_bloque.dia_semana)
    item.bloque_horario_id = nuevo_bloque.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Choque detectado al mover el bloque. Revisa la asignación de la sala o profesor."
        )
    db.refresh(item)
    return {"ok": True, "item_id": item.id, "bloque_horario_id": nuevo_bloque.id}


@app.delete("/api/sinopticos/items/{item_id}", status_code=204)
def eliminar_item_sinoptico(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El bloque de horario indicado no existe.")
    db.delete(item)
    db.commit()
    return None


@app.delete("/api/sinopticos/{sinoptico_id}", status_code=204)
def eliminar_sinoptico(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")
    db.delete(sinoptico)
    db.commit()
    return None


# ===========================================================================
# 4. GESTIÓN DE USUARIOS Y AUDITORÍA (Solo Administrador)
# ===========================================================================

@app.get("/api/admin/usuarios", response_model=List[schemas.UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _: models.Usuario = Depends(require_admin)):
    return db.query(models.Usuario).order_by(models.Usuario.nombre).all()


@app.post("/api/admin/usuarios", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(
    datos: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_admin),
):
    nuevo = models.Usuario(
        nombre=datos.nombre,
        email=str(datos.email).lower(),
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email.")
    db.refresh(nuevo)
    return nuevo


@app.get("/api/admin/auditoria", response_model=List[schemas.LoginLogOut])
def listar_auditoria(
    limite: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_admin),
):
    return db.query(models.LoginLog).order_by(models.LoginLog.creado_en.desc()).limit(limite).all()


@app.delete("/api/admin/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current: models.Usuario = Depends(require_admin),
):
    if current.id == usuario_id:
        raise HTTPException(status_code=400, detail="No puede eliminarse a sí mismo.")
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    db.delete(user)
    db.commit()
    return None