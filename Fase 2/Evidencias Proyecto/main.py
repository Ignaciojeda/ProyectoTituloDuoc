from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File
import io
from datetime import time, datetime, date, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, Query
from unicodedata import normalize
import random
import re
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from typing import Optional, List
from sqlalchemy import func
from pydantic import BaseModel


class ColorUpdateRequest(BaseModel):
    color: str

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
    version="2.3.0",
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
DIAS_CLASES = {1, 2, 3, 4, 5}  # lunes a viernes
VENTANA_MIN = 2
VENTANA_MAX = 3
MODULOS_POR_SESION = 2  # una clase = 2 módulos seguidos

# Color (hexadecimal) con el que nacen los bloques si nadie elige otro
COLOR_DEFAULT = "#2563eb"

def fechas_para_bloque(dia_semana: int, semanas: int = SEMANAS_DEFAULT):
    inicio = LUNES_INICIO_SEMESTRE + timedelta(days=dia_semana - 1)
    fin = inicio + timedelta(weeks=semanas)
    return inicio, fin

def sesiones_por_semana(asignatura):
    horas = getattr(asignatura, "horas", None) or 4
    return max(1, min(4, int(-(-horas // 2))))  # horas/2 redondeado hacia arriba, entre 1 y 4

def pares_consecutivos(bloques):
    por_dia = defaultdict(list)
    for b in sorted(bloques, key=lambda b: (b.dia_semana, b.hora_inicio)):
        por_dia[b.dia_semana].append(b)
    pares = []
    for dia in sorted(por_dia):
        lista = por_dia[dia]
        for i in range(len(lista) - 1):
            pares.append((lista[i], lista[i + 1]))
    return pares

def ranuras_con_ventanas(bloques):
    """Clases de 2 módulos con 1 a 4 módulos libres entre una y otra, de lunes a viernes."""
    por_dia = defaultdict(list)
    for b in sorted(bloques, key=lambda b: (b.dia_semana, b.hora_inicio)):
        if b.dia_semana in DIAS_CLASES:
            por_dia[b.dia_semana].append(b)
    secuencias = []
    for lista in por_dia.values():
        seq = []
        i = random.randint(0, 2)
        while i + 1 < len(lista):
            seq.append((lista[i], lista[i + 1]))
            i += MODULOS_POR_SESION + random.randint(VENTANA_MIN, VENTANA_MAX)
        secuencias.append(seq)
    random.shuffle(secuencias)
    ranuras = []
    for k in range(max((len(s) for s in secuencias), default=0)):
        for seq in secuencias:
            if k < len(seq):
                ranuras.append(seq[k])
    return ranuras

def obtener_jornada_id(db, jornada):
    valor = (jornada.value if hasattr(jornada, 'value') else str(jornada)).lower()
    fila = db.query(models.Jornada).filter(func.lower(models.Jornada.nombre) == valor).first()
    return fila.id if fila else None

def generar_seccion(db, sinoptico_id, asignatura, jornada):
    valor = jornada.value if hasattr(jornada, 'value') else str(jornada)
    existente = db.query(models.SinopticoItem.seccion).filter(
        models.SinopticoItem.sinoptico_id == sinoptico_id,
        models.SinopticoItem.asignatura_id == asignatura.id,
        models.SinopticoItem.seccion.isnot(None),
    ).first()
    if existente:
        return existente[0]
    return f"{asignatura.codigo}-001{valor[:1].upper()}"

def limpiar_texto(texto: str) -> str:
    """Elimina tildes, caracteres especiales y convierte a minúsculas para comparaciones flexibles."""
    if not texto:
        return ""
    texto = normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9\s]', '', texto).lower().strip()

def formatear_hora_hhmm(val) -> str:
    """Convierte cualquier objeto de hora, datetime o string a formato HH:MM."""
    if isinstance(val, (time, datetime)):
        return val.strftime("%H:%M")
    val_str = str(val).strip()
    match = re.search(r'(\d{1,2}):(\d{2})', val_str)
    if match:
        h, m = match.groups()
        return f"{int(h):02d}:{m}"
    return val_str[:5]


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


@app.get("/api/carreras/{carrera_id}/areas-docentes")
def areas_docentes_carrera(
    carrera_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    """
    Deduce qué áreas de docente (AreaDocenteTipo) son propias de una carrera,
    a partir de las palabras clave de sus asignaturas (mismo criterio que usa
    la generación automática). El frontend usa esto para resaltar, en los
    selectores de profesor, a quienes pertenecen al área de la carrera.
    """
    asignaturas = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == carrera_id,
        models.Asignatura.activo == True,
    ).all()

    areas = set()
    for a in asignaturas:
        area = area_para_asignatura(a.nombre)
        if area:
            areas.add(area)

    return {"areas": sorted(areas)}


@app.get("/api/planes-estudio", response_model=List[schemas.PlanEstudioOut])
def listar_planes_estudio(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.PlanEstudio).filter(models.PlanEstudio.activo == True).all()


@app.get("/api/semestres", response_model=List[schemas.SemestreOut])
def listar_semestres(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    return db.query(models.Semestre).filter(models.Semestre.activo == True).order_by(
        models.Semestre.anio.desc(), models.Semestre.numero.desc()
    ).all()


@app.get("/api/asignaturas", response_model=List[schemas.AsignaturaOut])
def listar_asignaturas(
    carrera_id: Optional[int] = None,
    nivel_semestral: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    query = db.query(models.Asignatura).filter(models.Asignatura.activo == True)
    if carrera_id is not None:
        query = query.join(
            models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
        ).filter(models.PlanEstudio.carrera_id == carrera_id)
    if nivel_semestral is not None:
        query = query.filter(models.Asignatura.nivel_semestral == nivel_semestral)
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
def listar_profesores(
    bloque_horario_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente)
):
    """
    Lista profesores activos.
    Si recibe bloque_horario_id en los Query Parameters, filtra estrictamente.
    """
    query = db.query(models.Profesor).filter(models.Profesor.activo == True)

    if bloque_horario_id is not None:
        query = query.join(
            models.DisponibilidadDocente,
            models.Profesor.id == models.DisponibilidadDocente.profesor_id
        ).filter(
            models.DisponibilidadDocente.bloque_horario_id == int(bloque_horario_id),
            models.DisponibilidadDocente.disponible.is_(True)
        ).distinct()

    return query.order_by(models.Profesor.nombre).all()


@app.post("/api/profesores/disponibilidad/upload")
async def subir_disponibilidad_docente(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador)
):
    try:
        contenido_bytes = await archivo.read()
        buffer = io.BytesIO(contenido_bytes)
        df = pd.read_excel(buffer)

        df['nombre_docente'] = df['nombre_docente'].ffill()

        dias_map = {
            'lunes': 1, 'martes': 2, 'miercoles': 3,
            'jueves': 4, 'viernes': 5, 'sabado': 6
        }

        profesores_bd = db.query(models.Profesor).filter(models.Profesor.activo == True).all()
        bloques_bd = db.query(models.BloqueHorario).all()

        db.query(models.DisponibilidadDocente).delete()
        db.commit()

        registros_creados = 0

        for _, row in df.iterrows():
            nombre_doc_raw = str(row['nombre_docente']).strip() if pd.notnull(row['nombre_docente']) else None
            if not nombre_doc_raw or nombre_doc_raw.lower() == 'nan':
                continue

            nombre_doc_clean = limpiar_texto(nombre_doc_raw)

            # Match de Profesor por palabras clave principales
            prof = None
            for p in profesores_bd:
                nombre_bd_clean = limpiar_texto(f"{p.nombre} {p.apellido}")
                palabras_doc = set(nombre_doc_clean.split())
                palabras_bd = set(nombre_bd_clean.split())

                if len(palabras_doc.intersection(palabras_bd)) >= 2:
                    prof = p
                    break

            if not prof:
                continue

            hora_excel_hhmm = formatear_hora_hhmm(row['hora_inicio'])

            for col_dia, dia_num in dias_map.items():
                if col_dia in row and pd.notnull(row[col_dia]):
                    es_disponible = bool(int(row[col_dia]) == 1)

                    if es_disponible:
                        bloque = None
                        for b in bloques_bd:
                            if b.dia_semana == dia_num:
                                b_hora_hhmm = formatear_hora_hhmm(b.hora_inicio)
                                if b_hora_hhmm == hora_excel_hhmm:
                                    bloque = b
                                    break

                        if bloque:
                            nueva_disp = models.DisponibilidadDocente(
                                profesor_id=prof.id,
                                bloque_horario_id=bloque.id,
                                disponible=True
                            )
                            db.add(nueva_disp)
                            registros_creados += 1

        db.commit()
        return {
            "ok": True,
            "mensaje": f"Disponibilidad cargada exitosamente. Se registraron {registros_creados} bloques disponibles.",
            "registros_procesados": registros_creados
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la disponibilidad: {str(e)}"
        )


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

@app.post("/api/sinopticos", status_code=201)
def crear_sinoptico_vacio(
    datos: schemas.GenerarSinopticoRequest,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """
    Crea un sinóptico vacío (sin generar automáticamente ninguna clase), para
    que el coordinador lo arme manualmente desde cero usando el '+' de la grilla.
    """
    nuevo = models.Sinoptico(
        carrera_id=datos.carrera_id,
        semestre_id=datos.semestre_id,
        jornada=datos.jornada,
    )
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un sinóptico con esa carrera/semestre/jornada.")
    db.refresh(nuevo)
    return {"sinoptico_id": nuevo.id, "asignaturas_sin_asignar": []}


@app.post("/api/sinopticos/generar")
def generar_sinoptico(
    datos: schemas.GenerarSinopticoRequest,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador)
):
    """Generación automática asignando bloques respetando la disponibilidad docente sin choques horarios."""

    # 1. Validar existencia de asignaturas activas para la carrera/escuela
    #    (opcionalmente filtradas por nivel_semestral, si viene en la petición)
    query_asig = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == datos.carrera_id,
        models.Asignatura.activo == True
    )
    nivel_semestral = getattr(datos, "nivel_semestral", None)
    if nivel_semestral:
        query_asig = query_asig.filter(models.Asignatura.nivel_semestral == nivel_semestral)
    asignaturas = query_asig.all()

    if not asignaturas:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron asignaturas activas para la carrera ID {datos.carrera_id}."
        )

    # 2. Convertir el valor de jornada de forma segura
    jornada_val = datos.jornada.value if hasattr(datos.jornada, 'value') else str(datos.jornada).lower()
    es_mixta = jornada_val == "mixta"

    # 3. Crear el registro del sinóptico
    nuevo_sinoptico = models.Sinoptico(
        carrera_id=datos.carrera_id,
        semestre_id=datos.semestre_id,
        jornada=datos.jornada
    )
    db.add(nuevo_sinoptico)
    db.flush()
    jornada_id_fijo = obtener_jornada_id(db, datos.jornada)

    # 4. Consultar bloques horarios para la jornada indicada.
    #    Si la jornada es "mixta", se consideran TODOS los bloques (diurnos y
    #    vespertinos); cada sesión asignada conserva la jornada real de su bloque.
    if es_mixta:
        bloques = db.query(models.BloqueHorario).order_by(
            models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
        ).all()
    else:
        bloques = db.query(models.BloqueHorario).filter(
            models.BloqueHorario.jornada == jornada_val
        ).order_by(models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio).all()

        if not bloques:
            bloques = db.query(models.BloqueHorario).order_by(
                models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
            ).all()

    profesores = db.query(models.Profesor).filter(models.Profesor.activo == True).all()
    salas = db.query(models.Sala).filter(models.Sala.activo == True).all()

    # Cargar mapa de disponibilidades cargadas (profesor_id -> set of bloque_horario_id)
    disponibilidades = db.query(models.DisponibilidadDocente).filter(
        models.DisponibilidadDocente.disponible == True
    ).all()

    profesor_disponible_map = defaultdict(set)
    for disp in disponibilidades:
        profesor_disponible_map[disp.profesor_id].add(disp.bloque_horario_id)

    profesor_ocupado = defaultdict(set)
    sala_ocupada = defaultdict(set)

    # Precargar la ocupación existente en otros sinópticos
    items_existentes = db.query(
        models.SinopticoItem.profesor_id,
        models.SinopticoItem.sala_id,
        models.SinopticoItem.bloque_horario_id,
    ).all()
    for prof_id, sala_id, bloque_id in items_existentes:
        if prof_id is not None:
            profesor_ocupado[prof_id].add(bloque_id)
        if sala_id is not None:
            sala_ocupada[sala_id].add(bloque_id)

    sin_asignar = []
    profesor_carga = defaultdict(int)
    sala_carga = defaultdict(int)
    carga_dia = defaultdict(int)
    bloques_usados = set()  # bloques ya ocupados por una clase de ESTE sinóptico

    ranuras = ranuras_con_ventanas(bloques)
    todas_las_sesiones = pares_consecutivos(bloques)

    def asignar_sesion(sesion, asignatura, candidatos_prof, candidatos_sala):
        ids = [b.id for b in sesion]
        # La jornada real de la sesión es la del primer bloque que la compone
        # (relevante solo cuando el sinóptico es "mixto", donde el pool de
        # bloques mezcla diurnos y vespertinos).
        jornada_sesion = sesion[0].jornada
        jornada_id_sesion = obtener_jornada_id(db, jornada_sesion) if es_mixta else jornada_id_fijo
        letra_sesion = (jornada_sesion.value if hasattr(jornada_sesion, 'value') else str(jornada_sesion))[:1].upper() if es_mixta else jornada_val[:1].upper()

        for p in candidatos_prof:
            if p.id in profesor_disponible_map and any(i not in profesor_disponible_map[p.id] for i in ids):
                continue
            if any(i in profesor_ocupado[p.id] for i in ids):
                continue
            for s in candidatos_sala:
                if any(i in sala_ocupada[s.id] for i in ids):
                    continue
                for b in sesion:
                    profesor_ocupado[p.id].add(b.id)
                    sala_ocupada[s.id].add(b.id)
                    bloques_usados.add(b.id)
                    carga_dia[b.dia_semana] += 1
                    inicio, fin = fechas_para_bloque(b.dia_semana)
                    db.add(models.SinopticoItem(
                        sinoptico_id=nuevo_sinoptico.id,
                        asignatura_id=asignatura.id,
                        profesor_id=p.id,
                        sala_id=s.id,
                        bloque_horario_id=b.id,
                        seccion=f"{asignatura.codigo}-001{letra_sesion}",
                        id_seccion=None,
                        fecha_inicio=inicio,
                        fecha_final=fin,
                        jornada_id=jornada_id_sesion,
                        color=COLOR_DEFAULT,
                    ))
                profesor_carga[p.id] += 1
                sala_carga[s.id] += 1
                return p, s
        return None

    # 5. Algoritmo de distribución de clases
    for asignatura in asignaturas:
        area_requerida = area_para_asignatura(asignatura.nombre)

        candidatos_prof = sorted(profesores, key=lambda p: (
            0 if (area_requerida and p.area_docente and hasattr(p.area_docente, 'value') and p.area_docente.value == area_requerida) else 1,
            profesor_carga[p.id]
        ))
        candidatos_sala = sorted(salas, key=lambda s: sala_carga[s.id])
        dias_del_ramo = set()
        colocadas = 0

        for _ in range(sesiones_por_semana(asignatura)):
            libres = [x for x in ranuras if not any(b.id in bloques_usados for b in x)]
            libres.sort(key=lambda x: x[0].dia_semana in dias_del_ramo)  # días distintos primero
            respaldo = [x for x in todas_las_sesiones if not any(b.id in bloques_usados for b in x)]
            respaldo.sort(key=lambda x: (x[0].dia_semana > 5, carga_dia[x[0].dia_semana]))

            for sesion in libres + respaldo:
                r = asignar_sesion(sesion, asignatura, candidatos_prof, candidatos_sala)
                if r:
                    p, s = r
                    # el mismo profesor y sala para todas las clases del ramo
                    candidatos_prof = [p] + [x for x in candidatos_prof if x.id != p.id]
                    candidatos_sala = [s] + [x for x in candidatos_sala if x.id != s.id]
                    dias_del_ramo.add(sesion[0].dia_semana)
                    colocadas += 1
                    break

        if colocadas == 0:
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
            "jornada": sinoptico.jornada.value if hasattr(sinoptico.jornada, 'value') else str(sinoptico.jornada),
            "creado_en": sinoptico.creado_en,
        }
        for sinoptico, carrera, semestre in filas
    ]


@app.get("/api/sinopticos/{sinoptico_id}/eventos")
def eventos_sinoptico(sinoptico_id: int, db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado.")

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

    # OJO: ya no se lanza 404 cuando el sinóptico existe pero aún no tiene
    # eventos (p. ej. recién creado vacío con "Crear sinóptico vacío").
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
                "color": item.color,
            }
        })
    return eventos


@app.get("/api/salas/{sala_id}/eventos")
def eventos_sala(sala_id: int, db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    sala = db.query(models.Sala).filter(models.Sala.id == sala_id).first()
    if not sala:
        raise HTTPException(status_code=404, detail="La sala indicada no existe.")

    filas = (
        db.query(
            models.SinopticoItem, models.Asignatura, models.Profesor,
            models.BloqueHorario, models.Jornada, models.Sinoptico,
            models.Carrera, models.Semestre,
        )
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .outerjoin(models.Jornada, models.SinopticoItem.jornada_id == models.Jornada.id)
        .join(models.Sinoptico, models.SinopticoItem.sinoptico_id == models.Sinoptico.id)
        .join(models.Carrera, models.Sinoptico.carrera_id == models.Carrera.id)
        .join(models.Semestre, models.Sinoptico.semestre_id == models.Semestre.id)
        .filter(models.SinopticoItem.sala_id == sala_id)
        .all()
    )

    eventos = []
    for item, asignatura, profesor, bloque, jornada, sinoptico, carrera, semestre in filas:
        eventos.append({
            "id": item.id,
            "title": asignatura.nombre,
            "daysOfWeek": [bloque.dia_semana],
            "startTime": bloque.hora_inicio.strftime("%H:%M:%S"),
            "endTime": bloque.hora_fin.strftime("%H:%M:%S"),
            "extendedProps": {
                "codigo": asignatura.codigo,
                "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else "Sin asignar",
                "jornada": jornada.nombre if jornada else bloque.jornada.value,
                "carrera": carrera.nombre,
                "semestre": f"{semestre.anio}-{semestre.numero}",
                "sinoptico_id": sinoptico.id,
                "color": item.color,
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

    asignatura = db.query(models.Asignatura).filter(models.Asignatura.id == datos.asignatura_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="La asignatura indicada no existe.")

    bloque = db.query(models.BloqueHorario).filter(models.BloqueHorario.id == datos.bloque_horario_id).first()
    if not bloque:
        raise HTTPException(status_code=404, detail="El bloque horario indicado no existe.")
    inicio, fin = fechas_para_bloque(bloque.dia_semana)

    # Validar choque de profesor SOLO si se especificó uno
    if datos.profesor_id is not None:
        choque_profesor = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.profesor_id == datos.profesor_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_profesor:
            raise HTTPException(status_code=409, detail="Ese profesor ya tiene otra clase asignada en ese bloque horario.")

    # Validar choque de sala SOLO si se especificó una
    if datos.sala_id is not None:
        choque_sala = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.sala_id == datos.sala_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_sala:
            raise HTTPException(status_code=409, detail="Esa sala ya está ocupada por otra clase en ese bloque horario.")

    # Si el sinóptico es "mixto", la jornada del item se toma del bloque elegido;
    # si no, se usa la jornada fija del sinóptico.
    sinoptico_jornada_val = sinoptico.jornada.value if hasattr(sinoptico.jornada, 'value') else str(sinoptico.jornada)
    jornada_para_item = bloque.jornada if sinoptico_jornada_val == "mixta" else sinoptico.jornada

    nuevo_item = models.SinopticoItem(
        sinoptico_id=datos.sinoptico_id,
        asignatura_id=datos.asignatura_id,
        profesor_id=datos.profesor_id,
        sala_id=datos.sala_id,
        bloque_horario_id=datos.bloque_horario_id,
        seccion=generar_seccion(db, datos.sinoptico_id, asignatura, jornada_para_item),
        id_seccion=None,
        capacidad_inicial=datos.capacidad_inicial,
        fecha_inicio=inicio,
        fecha_final=fin,
        jornada_id=obtener_jornada_id(db, jornada_para_item),
        color=datos.color or COLOR_DEFAULT,
    )
    db.add(nuevo_item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Error de restricción al guardar el ramo.")

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

    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == item.sinoptico_id).first()
    sinoptico_jornada_val = sinoptico.jornada.value if hasattr(sinoptico.jornada, 'value') else str(sinoptico.jornada)
    jornada_para_item = bloque.jornada if sinoptico_jornada_val == "mixta" else sinoptico.jornada

    if datos.asignatura_id != item.asignatura_id:
        asignatura = db.query(models.Asignatura).filter(models.Asignatura.id == datos.asignatura_id).first()
        if not asignatura:
            raise HTTPException(status_code=404, detail="La asignatura indicada no existe.")
        item.seccion = generar_seccion(db, item.sinoptico_id, asignatura, jornada_para_item)

    if datos.jornada_id is not None:
        item.jornada_id = datos.jornada_id
    else:
        item.jornada_id = obtener_jornada_id(db, jornada_para_item)

    item.asignatura_id = datos.asignatura_id
    item.profesor_id = datos.profesor_id
    item.sala_id = datos.sala_id
    item.bloque_horario_id = datos.bloque_horario_id
    item.capacidad_inicial = datos.capacidad_inicial
    if datos.color:
        item.color = datos.color
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
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El bloque de horario indicado no existe.")

    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == item.sinoptico_id).first()
    sinoptico_jornada_val = sinoptico.jornada.value if hasattr(sinoptico.jornada, 'value') else str(sinoptico.jornada)

    # Si el sinóptico es "mixto", el bloque se busca por día/hora sin exigir una
    # jornada específica (puede caer en un bloque diurno o vespertino).
    query_bloque = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.dia_semana == datos.dia_semana,
        models.BloqueHorario.hora_inicio == datos.hora_inicio,
        models.BloqueHorario.hora_fin == datos.hora_fin,
    )
    if sinoptico_jornada_val != "mixta":
        query_bloque = query_bloque.filter(models.BloqueHorario.jornada == datos.jornada)
    nuevo_bloque = query_bloque.first()

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
    if sinoptico_jornada_val == "mixta":
        item.jornada_id = obtener_jornada_id(db, nuevo_bloque.jornada)
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


@app.patch("/api/sinopticos/{sinoptico_id}/asignaturas/{asignatura_id}/color")
def actualizar_color_asignatura(
    sinoptico_id: int,
    asignatura_id: int,
    datos: ColorUpdateRequest,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """
    Iguala el color de TODOS los bloques de una asignatura dentro de un mismo
    sinóptico (no afecta a esa asignatura en otros sinópticos).
    """
    items = db.query(models.SinopticoItem).filter(
        models.SinopticoItem.sinoptico_id == sinoptico_id,
        models.SinopticoItem.asignatura_id == asignatura_id,
    ).all()
    if not items:
        raise HTTPException(status_code=404, detail="No hay bloques de esa asignatura en este sinóptico.")

    for item in items:
        item.color = datos.color

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar el color de la asignatura.")

    return {"ok": True, "actualizados": len(items)}


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