from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from typing import Optional, List

from database import engine, get_db, Base
import models
import schemas
from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
)

app = FastAPI(
    title="API de Sistema de Sinópticos",
    version="2.0.0",
    description="Backend desacoplado para consumo desde cliente React"
)

# Configuración de CORS para permitir conexiones desde React (Vite)
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

Base.metadata.create_all(bind=engine)

# Palabras clave por área
PALABRA_CLAVE_AREA = {
    "informatica": ["programacion", "base de datos", "software", "sistemas"],
    "redes": ["redes"],
    "matematica": ["matematica", "algebra", "calculo"],
}

def area_para_asignatura(nombre_asignatura: str):
    nombre = nombre_asignatura.lower()
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre for p in palabras):
            return area
    return None


# ===========================================================================
# AUTENTICACIÓN
# ===========================================================================

@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, datos.email, datos.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    
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
# ENDPOINTS DE RECURSOS (API REST)
# ===========================================================================

@app.get("/api/asignaturas", response_model=List[schemas.AsignaturaOut])
def listar_asignaturas(carrera_id: Optional[int] = None, db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    query = db.query(models.Asignatura).filter(models.Asignatura.activo == True)
    if carrera_id is not None:
        query = query.join(
            models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
        ).filter(models.PlanEstudio.carrera_id == carrera_id)
    return query.all()


@app.post("/api/asignaturas", response_model=schemas.AsignaturaOut)
def crear_asignatura(datos: schemas.AsignaturaCreate, db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    nueva = models.Asignatura(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/carreras", response_model=List[schemas.CarreraOut])
def listar_carreras(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.Carrera).filter(models.Carrera.activo == True).order_by(models.Carrera.nombre).all()


@app.post("/api/carreras", response_model=schemas.CarreraOut)
def crear_carrera(datos: schemas.CarreraCreate, db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    nueva = models.Carrera(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/planes-estudio", response_model=List[schemas.PlanEstudioOut])
def listar_planes_estudio(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.PlanEstudio).filter(models.PlanEstudio.activo == True).all()


@app.get("/api/semestres", response_model=List[schemas.SemestreOut])
def listar_semestres(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.Semestre).filter(models.Semestre.activo == True).order_by(
        models.Semestre.anio.desc(), models.Semestre.numero.desc()
    ).all()


@app.get("/api/profesores", response_model=List[schemas.ProfesorOut])
def listar_profesores(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.Profesor).filter(models.Profesor.activo == True).all()


@app.get("/api/salas", response_model=List[schemas.SalaOut])
def listar_salas(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.Sala).filter(models.Sala.activo == True).all()


@app.get("/api/bloques-horario", response_model=List[schemas.BloqueHorarioOut])
def listar_bloques_horario(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    return db.query(models.BloqueHorario).order_by(
        models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
    ).all()


# --- Algoritmo de Generación e Ítems de Sinóptico ---

@app.post("/api/sinopticos/generar")
def generar_sinoptico(datos: schemas.GenerarSinopticoRequest, db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    asignaturas = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == datos.carrera_id,
        models.Asignatura.activo == True
    ).all()

    if not asignaturas:
        raise HTTPException(status_code=404, detail="No se encontraron asignaturas para la carrera especificada.")

    jornada = asignaturas[0].jornada
    bloques = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.jornada == jornada
    ).order_by(models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio).all()

    profesores = db.query(models.Profesor).filter(models.Profesor.activo == True).all()
    salas = db.query(models.Sala).filter(models.Sala.activo == True).all()

    profesor_ocupado = defaultdict(set)
    sala_ocupada = defaultdict(set)

    nuevo_sinoptico = models.Sinoptico(carrera_id=datos.carrera_id, semestre_id=datos.semestre_id)
    db.add(nuevo_sinoptico)
    db.flush()

    sin_asignar = []
    profesor_carga = defaultdict(int)
    sala_carga = defaultdict(int)

    for asignatura in asignaturas:
        area_requerida = area_para_asignatura(asignatura.nombre)
        candidatos_prof = sorted(profesores, key=lambda p: (
            0 if (area_requerida and p.area_docente.value == area_requerida) else 1,
            profesor_carga[p.id]
        ))
        candidatos_sala = sorted(salas, key=lambda s: sala_carga[s.id])

        asignado = False
        for b in bloques:
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

                    item = models.SinopticoItem(
                        sinoptico_id=nuevo_sinoptico.id,
                        asignatura_id=asignatura.id,
                        profesor_id=p.id,
                        sala_id=s.id,
                        bloque_horario_id=b.id
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

    db.commit()
    db.refresh(nuevo_sinoptico)

    return {
        "sinoptico_id": nuevo_sinoptico.id,
        "asignaturas_sin_asignar": sin_asignar
    }


@app.get("/api/sinopticos")
def listar_sinopticos(db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
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
            "semestre": f"{semestre.anio}-{semestre.numero}",
            "creado_en": sinoptico.creado_en,
        }
        for sinoptico, carrera, semestre in filas
    ]


@app.get("/api/sinopticos/{sinoptico_id}/eventos")
def eventos_sinoptico(sinoptico_id: int, db: Session = Depends(get_db), _: models.Usuario = Depends(get_current_user)):
    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )

    if not filas:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado o sin asignaturas asignadas.")

    eventos = []
    for item, asignatura, profesor, sala, bloque in filas:
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
                "jornada": bloque.jornada.value,
            }
        })
    return eventos


# ===========================================================================
# GESTIÓN DE USUARIOS (Solo Administrador)
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
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    db.refresh(nuevo)
    return nuevo


@app.delete("/api/admin/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current: models.Usuario = Depends(require_admin),
):
    if current.id == usuario_id:
        raise HTTPException(status_code=400, detail="No puede eliminarse a sí mismo")
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
    return None