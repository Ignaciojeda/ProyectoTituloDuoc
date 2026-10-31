from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Response
from zoneinfo import ZoneInfo
from pdf_sinoptico import construir_pdf_sinoptico
from excel_sinoptico import construir_excel_sinoptico
from excel_sabana import construir_excel_sabana
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


class SemanasUpdateRequest(BaseModel):
    # Números de semana (1..17) en que se dicta la asignatura. Lista con todas = todas las semanas.
    semanas: List[int]

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
    "informatica": ["programacion", "base de datos", "software", "sistemas", "desarrollo", "web", "informatica", "computacion"],
    "redes": ["redes", "telecomunicaciones", "cisco", "infraestructura"],
    "matematica": ["matematica", "algebra", "calculo", "estadistica"],
    "administracion": ["administracion", "gestion", "comercio", "logistica", "marketing", "negocios", "recursos humanos"],
    "contabilidad": ["contabilidad", "finanzas", "costos", "tributaria"],
    "ingles": ["ingles", "english"],
    "lenguaje": ["lenguaje", "comunicacion", "redaccion"],
    "prevencion_riesgos": ["prevencion", "riesgos", "seguridad laboral", "higiene industrial"],
    "trabajo_social": ["trabajo social", "social", "comunitari", "familia"],
    "diseno_grafico": ["diseno", "grafico", "ilustracion", "tipografia", "multimedia"],
    "turismo": ["turismo", "hoteleria", "turistic"],
    "gastronomia": ["gastronomia", "cocina", "culinari", "pasteleria", "panaderia", "alimentos"],
    "enfermeria": ["enfermeria", "clinic", "anatomia", "salud", "farmacologia"],
}

def area_para_asignatura(nombre_asignatura: str):
    nombre = limpiar_texto(nombre_asignatura)
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre for p in palabras):
            return area
    return None

def areas_de_carrera(nombre_carrera: str, nombres_asignaturas):
    """
    Áreas docentes propias de una carrera. Se prioriza el nombre de la carrera
    (ej. 'Administración y Negocios' -> administracion) y se suman solo las áreas
    que aparecen en una parte relevante de sus asignaturas, para que un ramo suelto
    (ej. 'Sistemas de información' en Administración) no marque a todo un área.
    """
    areas = set()
    nombre_c = limpiar_texto(nombre_carrera)
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre_c for p in palabras):
            areas.add(area)

    conteo = defaultdict(int)
    for n in nombres_asignaturas:
        area = area_para_asignatura(n)
        if area:
            conteo[area] += 1
    total = len(nombres_asignaturas) or 1
    for area, cant in conteo.items():
        if cant >= 2 and cant / total >= 0.15:
            areas.add(area)

    if not areas and conteo:
        areas.add(max(conteo, key=conteo.get))
    return areas

LUNES_INICIO_SEMESTRE = date(2026, 8, 10)
SEMANAS_DEFAULT = 18
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

def parse_semanas(valor):
    """'1,3,5' -> [1,3,5]. None o vacío = todas las semanas (devuelve None)."""
    if not valor:
        return None
    try:
        lista = sorted({int(x) for x in str(valor).split(",") if x.strip()})
    except ValueError:
        return None
    lista = [w for w in lista if 1 <= w <= SEMANAS_DEFAULT]
    if not lista or len(lista) == SEMANAS_DEFAULT:
        return None
    return lista


def serializar_semanas(lista):
    """Lista de semanas -> texto para guardar; todas las semanas se guarda como NULL."""
    lista = sorted({int(w) for w in lista if 1 <= int(w) <= SEMANAS_DEFAULT})
    if not lista or len(lista) == SEMANAS_DEFAULT:
        return None
    return ",".join(str(w) for w in lista)


def fechas_para_item(dia_semana: int, semanas_texto=None):
    """Igual que fechas_para_bloque, pero acotado a la primera y última semana elegidas."""
    lista = parse_semanas(semanas_texto)
    if not lista:
        return fechas_para_bloque(dia_semana)
    offset = timedelta(days=dia_semana - 1)
    inicio = LUNES_INICIO_SEMESTRE + timedelta(weeks=lista[0] - 1) + offset
    fin = LUNES_INICIO_SEMESTRE + timedelta(weeks=lista[-1]) + offset
    return inicio, fin

def sesiones_por_semana(asignatura):
    horas = getattr(asignatura, "horas", None) or 4
    return max(1, min(4, int(-(-horas // 2))))  # horas/2 redondeado hacia arriba, entre 1 y 4

def tamanos_sesiones(asignatura):
    """Módulos de cada sesión semanal. Ej: horas=3 -> [2, 1], horas=4 -> [2, 2], horas=1 -> [1]"""
    horas = getattr(asignatura, "horas", None) or 4
    horas = max(1, min(8, int(horas)))
    tamanos = [2] * (horas // 2)
    if horas % 2:
        tamanos.append(1)
    return tamanos

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
    # Sin enumeración (-001) ni letra de jornada: solo las siglas/código de la asignatura
    return f"{asignatura.codigo}"

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
    carrera = db.query(models.Carrera).filter(models.Carrera.id == carrera_id).first()
    asignaturas = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == carrera_id,
        models.Asignatura.activo == True,
    ).all()

    areas = areas_de_carrera(carrera.nombre if carrera else "", [a.nombre for a in asignaturas])

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
    excluir_item_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente)
):
    """
    Lista profesores activos.
    Si recibe bloque_horario_id, devuelve SOLO los que están disponibles en ese
    bloque y que además no tienen ya otra clase asignada en él (en cualquier sinóptico).
    excluir_item_id: al editar una clase, esa misma clase no cuenta como "ocupado".
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

        ocupados = db.query(models.SinopticoItem.profesor_id).filter(
            models.SinopticoItem.bloque_horario_id == int(bloque_horario_id),
            models.SinopticoItem.profesor_id.isnot(None),
        )
        if excluir_item_id is not None:
            ocupados = ocupados.filter(models.SinopticoItem.id != int(excluir_item_id))
        ids_ocupados = [r[0] for r in ocupados.all()]
        if ids_ocupados:
            query = query.filter(~models.Profesor.id.in_(ids_ocupados))

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

        def _match_profesor(nombre_doc_raw):
            if not nombre_doc_raw or str(nombre_doc_raw).strip().lower() == 'nan':
                return None
            nombre_doc_clean = limpiar_texto(str(nombre_doc_raw).strip())
            palabras_doc = set(nombre_doc_clean.split())
            for p in profesores_bd:
                nombre_bd_clean = limpiar_texto(f"{p.nombre} {p.apellido}")
                palabras_bd = set(nombre_bd_clean.split())
                if len(palabras_doc.intersection(palabras_bd)) >= 2:
                    return p
            return None

        # Primero identificamos a qué profesores corresponde ESTE archivo.
        profesores_en_archivo_ids = set()
        for nombre_doc_raw in df['nombre_docente'].unique():
            prof_match = _match_profesor(nombre_doc_raw)
            if prof_match:
                profesores_en_archivo_ids.add(prof_match.id)

        # Solo se reemplaza lo que vino de un Excel anterior PARA LOS PROFESORES
        # incluidos en este archivo; lo de otros profesores (cargado en subidas
        # anteriores) y lo agregado a mano (origen='manual') se conserva.
        if profesores_en_archivo_ids:
            db.query(models.DisponibilidadDocente).filter(
                models.DisponibilidadDocente.origen == "excel",
                models.DisponibilidadDocente.profesor_id.in_(profesores_en_archivo_ids),
            ).delete(synchronize_session=False)
            db.commit()

        ya_registrados = {
            (d.profesor_id, d.bloque_horario_id)
            for d in db.query(models.DisponibilidadDocente).all()
        }

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

                        if bloque and (prof.id, bloque.id) not in ya_registrados:
                            nueva_disp = models.DisponibilidadDocente(
                                profesor_id=prof.id,
                                bloque_horario_id=bloque.id,
                                disponible=True,
                                origen="excel",
                            )
                            db.add(nueva_disp)
                            ya_registrados.add((prof.id, bloque.id))
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


@app.get("/api/profesores/disponibilidad")
def resumen_disponibilidad_profesores(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    """Cantidad de bloques disponibles por profesor (para listarlos con su resumen)."""
    filas = (
        db.query(models.DisponibilidadDocente.profesor_id, func.count(models.DisponibilidadDocente.id))
        .filter(models.DisponibilidadDocente.disponible.is_(True))
        .group_by(models.DisponibilidadDocente.profesor_id)
        .all()
    )
    return {str(profesor_id): total for profesor_id, total in filas}

@app.get("/api/profesores/horas-semestre")
def horas_semestre_profesores(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Carga total del semestre por profesor, según las clases que tiene en todos los sinópticos."""
    filas = (
        db.query(
            models.SinopticoItem.profesor_id,
            models.SinopticoItem.semanas,
            models.BloqueHorario.hora_inicio,
            models.BloqueHorario.hora_fin,
        )
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .filter(models.SinopticoItem.profesor_id.isnot(None))
        .all()
    )
    res = {}
    for prof_id, semanas_txt, ini, fin in filas:
        lista = parse_semanas(semanas_txt)
        n_sem = len(lista) if lista else SEMANAS_DEFAULT  # sin semanas marcadas = todas
        minutos = (fin.hour * 60 + fin.minute) - (ini.hour * 60 + ini.minute)
        r = res.setdefault(str(prof_id), {"modulos_semana": 0, "modulos_semestre": 0, "minutos_semestre": 0})
        r["modulos_semana"] += 1
        r["modulos_semestre"] += n_sem
        r["minutos_semestre"] += minutos * n_sem
    for r in res.values():
        r["horas_semestre"] = round(r.pop("minutos_semestre") / 60, 1)
    return res

@app.get("/api/profesores/{profesor_id}/disponibilidad")
def disponibilidad_profesor(
    profesor_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    """
    Bloques en los que el profesor está disponible y bloques en los que ya
    tiene una clase asignada en algún sinóptico (para ver cuáles están realmente libres).
    """
    profesor = db.query(models.Profesor).filter(models.Profesor.id == profesor_id).first()
    if not profesor:
        raise HTTPException(status_code=404, detail="El profesor indicado no existe.")

    disponibles = db.query(models.DisponibilidadDocente.bloque_horario_id).filter(
        models.DisponibilidadDocente.profesor_id == profesor_id,
        models.DisponibilidadDocente.disponible.is_(True),
    ).all()
    ocupados = db.query(models.SinopticoItem.bloque_horario_id).filter(
        models.SinopticoItem.profesor_id == profesor_id
    ).all()

    return {
        "profesor_id": profesor_id,
        "bloques_disponibles": sorted({r[0] for r in disponibles}),
        "bloques_ocupados": sorted({r[0] for r in ocupados}),
    }


MEDIOS_ACUERDO = {
    "llamada": "Llamada telefónica",
    "correo": "Correo electrónico",
    "presencial": "Reunión presencial",
    "mensaje": "Mensaje (WhatsApp / chat)",
    "solicitud_docente": "Solicitud del docente (portal)",
    "otro": "Otro",
}
NOMBRES_DIA = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}


def registrar_cambio(
    db: Session, usuario: models.Usuario, accion: str, entidad: str, detalle: str,
    sinoptico_id: Optional[int] = None, profesor_id: Optional[int] = None,
    medio: Optional[str] = None, motivo: Optional[str] = None,
):
    """Agrega una línea a la bitácora. NO hace commit: se confirma con el del endpoint."""
    db.add(models.RegistroCambio(
        usuario_id=usuario.id,
        usuario_nombre=f"{usuario.nombre} ({usuario.email})",
        accion=accion, entidad=entidad, detalle=detalle[:500],
        sinoptico_id=sinoptico_id, profesor_id=profesor_id,
        medio=medio, motivo=(motivo or None),
    ))


def describir_bloque(db: Session, bloque_id: int) -> str:
    b = db.query(models.BloqueHorario).filter(models.BloqueHorario.id == bloque_id).first()
    if not b:
        return f"bloque {bloque_id}"
    return f"{NOMBRES_DIA.get(b.dia_semana, b.dia_semana)} {str(b.hora_inicio)[:5]}"


def nombre_asignatura(db: Session, asignatura_id: int) -> str:
    a = db.query(models.Asignatura).filter(models.Asignatura.id == asignatura_id).first()
    return a.nombre if a else f"asignatura {asignatura_id}"


class DisponibilidadManualRequest(BaseModel):
    bloque_horario_ids: List[int]
    disponible: bool
    medio: str                 # llamada | correo | presencial | mensaje | solicitud_docente | otro
    motivo: str                # por qué se hace el cambio / cómo se llegó al acuerdo
    # Compatibilidad: sin medio/motivo la petición se rechaza con 422


@app.put("/api/profesores/{profesor_id}/disponibilidad")
def fijar_disponibilidad_manual(
    profesor_id: int,
    datos: DisponibilidadManualRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
):
    """
    Marca (disponible=true) o desmarca (disponible=false) uno o varios bloques
    para un profesor, a mano. Sirve para sumar días/horas extra a lo que vino
    en el Excel. Lo marcado aquí queda como origen='manual' y NO se pierde al
    volver a cargar el Excel de disponibilidad.
    """
    profesor = db.query(models.Profesor).filter(models.Profesor.id == profesor_id).first()
    if not profesor:
        raise HTTPException(status_code=404, detail="El profesor indicado no existe.")

    if datos.medio not in MEDIOS_ACUERDO:
        raise HTTPException(status_code=400, detail="Debes elegir cómo se acordó el cambio (llamada, correo, etc.).")
    motivo = (datos.motivo or "").strip()
    if len(motivo) < 3:
        raise HTTPException(status_code=400, detail="Debes indicar el motivo del cambio.")

    ids = set(datos.bloque_horario_ids)
    if not ids:
        return {"ok": True, "cambiados": 0}

    existentes_bloques = {
        r[0] for r in db.query(models.BloqueHorario.id).filter(models.BloqueHorario.id.in_(ids)).all()
    }
    if existentes_bloques != ids:
        raise HTTPException(status_code=404, detail="Alguno de los bloques horarios indicados no existe.")

    if datos.disponible:
        ya = {
            r[0] for r in db.query(models.DisponibilidadDocente.bloque_horario_id).filter(
                models.DisponibilidadDocente.profesor_id == profesor_id,
                models.DisponibilidadDocente.bloque_horario_id.in_(ids),
            ).all()
        }
        for bloque_id in ids - ya:
            db.add(models.DisponibilidadDocente(
                profesor_id=profesor_id,
                bloque_horario_id=bloque_id,
                disponible=True,
                origen="manual",
            ))
        # Si existía la fila (p. ej. del Excel) solo se asegura que esté disponible
        db.query(models.DisponibilidadDocente).filter(
            models.DisponibilidadDocente.profesor_id == profesor_id,
            models.DisponibilidadDocente.bloque_horario_id.in_(ids),
        ).update({"disponible": True}, synchronize_session=False)
    else:
        db.query(models.DisponibilidadDocente).filter(
            models.DisponibilidadDocente.profesor_id == profesor_id,
            models.DisponibilidadDocente.bloque_horario_id.in_(ids),
        ).delete(synchronize_session=False)

    nombres_bloques = ", ".join(describir_bloque(db, i) for i in sorted(ids)[:8])
    if len(ids) > 8:
        nombres_bloques += f" y {len(ids) - 8} más"
    registrar_cambio(
        db, usuario,
        accion="disponibilidad_agregada" if datos.disponible else "disponibilidad_quitada",
        entidad="disponibilidad",
        detalle=f"{'Agregó' if datos.disponible else 'Quitó'} disponibilidad de {profesor.nombre} {profesor.apellido}: {nombres_bloques}",
        profesor_id=profesor_id, medio=datos.medio, motivo=motivo,
    )
    db.commit()
    return {"ok": True, "cambiados": len(ids)}


# ---------------------------------------------------------------------------
# PORTAL DOCENTE: "mi horario" y "subir mi horario"
# El usuario se vincula con su ficha de profesor por nombre (mismo criterio
# que la carga del Excel: al menos 2 palabras en común entre el nombre del
# usuario y "nombre apellido" del profesor).
# ---------------------------------------------------------------------------

def _profesor_del_usuario(db: Session, usuario: models.Usuario):
    palabras_usuario = set(limpiar_texto(usuario.nombre or "").split())
    mejor, mejor_score = None, 0
    for p in db.query(models.Profesor).filter(models.Profesor.activo == True).all():
        palabras_prof = set(limpiar_texto(f"{p.nombre} {p.apellido}").split())
        score = len(palabras_usuario & palabras_prof)
        if score >= 2 and score > mejor_score:
            mejor, mejor_score = p, score
    return mejor


@app.get("/api/docente/mis-cambios")
def mis_cambios_docente(
    limite: int = 100,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_docente),
):
    """Cambios hechos por coordinación sobre la disponibilidad y las clases del profesor logeado."""
    profesor = _profesor_del_usuario(db, usuario)
    if not profesor:
        return []
    filas = db.query(models.RegistroCambio).filter(
        models.RegistroCambio.profesor_id == profesor.id
    ).order_by(models.RegistroCambio.creado_en.desc(), models.RegistroCambio.id.desc()).limit(limite).all()
    return [_registro_a_dict(r) for r in filas]


@app.get("/api/docente/mi-horario")
def mi_horario_docente(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_docente),
):
    """Clases asignadas al profesor logeado (en cualquier sinóptico), en formato calendario."""
    profesor = _profesor_del_usuario(db, usuario)
    if not profesor:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una ficha de profesor que coincida con tu nombre de usuario. Pide al administrador que lo revise.",
        )

    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Sala, models.BloqueHorario, models.Jornada, models.Sinoptico)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .outerjoin(models.Jornada, models.SinopticoItem.jornada_id == models.Jornada.id)
        .join(models.Sinoptico, models.SinopticoItem.sinoptico_id == models.Sinoptico.id)
        .filter(models.SinopticoItem.profesor_id == profesor.id)
        .all()
    )

    eventos = []
    for item, asignatura, sala, bloque, jornada, sinoptico in filas:
        eventos.append({
            "id": item.id,
            "title": asignatura.nombre,
            "daysOfWeek": [bloque.dia_semana],
            "startTime": bloque.hora_inicio.strftime("%H:%M:%S"),
            "endTime": bloque.hora_fin.strftime("%H:%M:%S"),
            "extendedProps": {
                "codigo": asignatura.codigo,
                "profesor": f"{profesor.nombre} {profesor.apellido}",
                "sala": sala.nombre if sala else "Sin asignar",
                "jornada": jornada.nombre if jornada else bloque.jornada.value,
                "seccion": item.seccion,
                "tipo": item.tipo,
                "sinoptico_id": item.sinoptico_id,
                "color": item.color,
                "semanas": parse_semanas(item.semanas),
            },
        })

    return {
        "profesor": f"{profesor.nombre} {profesor.apellido}",
        "eventos": eventos,
    }


@app.post("/api/docente/disponibilidad/upload")
async def subir_mi_disponibilidad(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_docente),
):
    """
    El profesor logeado sube su propio Excel de disponibilidad (mismas columnas
    que la plantilla: hora_inicio, lunes..sabado con 1/0; la columna
    nombre_docente se ignora porque todo se asigna a quien sube el archivo).
    Reemplaza solo SU disponibilidad de origen 'excel'; lo agregado a mano
    por el administrador se conserva.
    """
    profesor = _profesor_del_usuario(db, usuario)
    if not profesor:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una ficha de profesor que coincida con tu nombre de usuario. Pide al administrador que lo revise.",
        )

    try:
        df = pd.read_excel(io.BytesIO(await archivo.read()))
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "hora_inicio" not in df.columns:
            raise HTTPException(status_code=400, detail="El archivo debe tener la columna 'hora_inicio'.")

        dias_map = {'lunes': 1, 'martes': 2, 'miercoles': 3, 'jueves': 4, 'viernes': 5, 'sabado': 6}
        bloques_bd = db.query(models.BloqueHorario).all()
        bloque_por_clave = {
            (b.dia_semana, formatear_hora_hhmm(b.hora_inicio)): b for b in bloques_bd
        }

        db.query(models.DisponibilidadDocente).filter(
            models.DisponibilidadDocente.profesor_id == profesor.id,
            models.DisponibilidadDocente.origen == "excel",
        ).delete(synchronize_session=False)
        db.commit()

        ya = {
            d.bloque_horario_id
            for d in db.query(models.DisponibilidadDocente).filter(
                models.DisponibilidadDocente.profesor_id == profesor.id
            ).all()
        }

        creados = 0
        for _, row in df.iterrows():
            if pd.isnull(row["hora_inicio"]):
                continue
            hhmm = formatear_hora_hhmm(row["hora_inicio"])
            for col_dia, dia_num in dias_map.items():
                if col_dia in row and pd.notnull(row[col_dia]) and int(row[col_dia]) == 1:
                    bloque = bloque_por_clave.get((dia_num, hhmm))
                    if bloque and bloque.id not in ya:
                        db.add(models.DisponibilidadDocente(
                            profesor_id=profesor.id,
                            bloque_horario_id=bloque.id,
                            disponible=True,
                            origen="excel",
                        ))
                        ya.add(bloque.id)
                        creados += 1

        db.commit()
        return {"ok": True, "mensaje": f"Tu disponibilidad quedó cargada: {creados} bloques disponibles."}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar tu archivo: {str(e)}")


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
    usuario: models.Usuario = Depends(require_coordinador),
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
    registrar_cambio(db, usuario, "sinoptico_creado", "sinoptico", "Creó el sinóptico vacío", sinoptico_id=nuevo.id)
    db.commit()
    return {"sinoptico_id": nuevo.id, "asignaturas_sin_asignar": []}


class GenerarSinopticoConId(schemas.GenerarSinopticoRequest):
    # Si viene, se rellena ese sinóptico (sin crear uno nuevo) con las asignaturas que aún no tiene
    sinoptico_id: Optional[int] = None


@app.post("/api/sinopticos/generar")
def generar_sinoptico(
    datos: GenerarSinopticoConId,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador)
):
    """Generación automática asignando bloques respetando la disponibilidad docente sin choques horarios."""

    # 0. ¿Se pidió generar DENTRO de un sinóptico existente?
    sinoptico_existente = None
    if datos.sinoptico_id:
        sinoptico_existente = db.query(models.Sinoptico).filter(models.Sinoptico.id == datos.sinoptico_id).first()
        if not sinoptico_existente:
            raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")
        # Carrera y jornada son las del sinóptico, no las del filtro
        datos.carrera_id = sinoptico_existente.carrera_id
        datos.jornada = sinoptico_existente.jornada

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
    if sinoptico_existente:
        nuevo_sinoptico = sinoptico_existente
    else:
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
    ya_presentes = set()    # asignaturas que ese sinóptico ya tiene (solo al rellenar uno existente)
    if sinoptico_existente:
        for a_id, b_id in db.query(models.SinopticoItem.asignatura_id, models.SinopticoItem.bloque_horario_id).filter(
            models.SinopticoItem.sinoptico_id == sinoptico_existente.id
        ).all():
            ya_presentes.add(a_id)
            bloques_usados.add(b_id)

    ranuras = ranuras_con_ventanas(bloques)
    todas_las_sesiones = pares_consecutivos(bloques)
    todos_los_simples = [(b,) for b in sorted(bloques, key=lambda b: (b.dia_semana, b.hora_inicio))]

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
                        seccion=f"{asignatura.codigo}",
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
        if asignatura.id in ya_presentes:
            continue
        area_requerida = area_para_asignatura(asignatura.nombre)

        candidatos_prof = sorted(profesores, key=lambda p: (
            0 if (area_requerida and p.area_docente and hasattr(p.area_docente, 'value') and p.area_docente.value == area_requerida) else 1,
            profesor_carga[p.id]
        ))
        candidatos_sala = sorted(salas, key=lambda s: sala_carga[s.id])
        dias_del_ramo = set()
        colocadas = 0

        for tam in tamanos_sesiones(asignatura):
            if tam == 1:
                # sesión de 1 módulo (cuando las horas son impares): cualquier bloque libre
                libres = [x for x in todos_los_simples if x[0].dia_semana in DIAS_CLASES and x[0].id not in bloques_usados]
                libres.sort(key=lambda x: (x[0].dia_semana in dias_del_ramo, carga_dia[x[0].dia_semana]))
                respaldo = [x for x in todos_los_simples if x[0].id not in bloques_usados]
                respaldo.sort(key=lambda x: (x[0].dia_semana > 5, carga_dia[x[0].dia_semana]))
            else:
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
        registrar_cambio(db, usuario, "sinoptico_generado", "sinoptico",
                         "Generó automáticamente las asignaturas faltantes" if sinoptico_existente else "Generó el sinóptico automáticamente",
                         sinoptico_id=nuevo_sinoptico.id)
        db.commit()
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

    # Plan de estudio y nivel de cada sinóptico, deducidos de las asignaturas que contiene
    # (el sinóptico no los guarda directamente). Una sola consulta para todos.
    combos = (
        db.query(
            models.SinopticoItem.sinoptico_id,
            models.Asignatura.plan_estudio_id,
            models.Asignatura.nivel_semestral,
            func.count(models.SinopticoItem.id),
        )
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .group_by(
            models.SinopticoItem.sinoptico_id,
            models.Asignatura.plan_estudio_id,
            models.Asignatura.nivel_semestral,
        )
        .all()
    )
    planes_por_sin = defaultdict(lambda: defaultdict(int))
    niveles_por_sin = defaultdict(set)
    for sin_id, plan_id, nivel, cantidad in combos:
        if plan_id is not None:
            planes_por_sin[sin_id][plan_id] += cantidad
        if nivel is not None:
            niveles_por_sin[sin_id].add(nivel)

    # Planes activos por carrera: sirve para sinópticos vacíos de una carrera con un único plan
    planes_carrera = defaultdict(list)
    for p in db.query(models.PlanEstudio).filter(models.PlanEstudio.activo == True).all():
        planes_carrera[p.carrera_id].append(p.id)

    resultado = []
    for sinoptico, carrera, semestre in filas:
        planes = planes_por_sin.get(sinoptico.id)
        if planes:
            plan_id = max(planes, key=planes.get)
        elif len(planes_carrera.get(carrera.id, [])) == 1:
            plan_id = planes_carrera[carrera.id][0]
        else:
            plan_id = None

        niveles = niveles_por_sin.get(sinoptico.id, set())
        if len(niveles) == 1:
            nivel = next(iter(niveles))
        elif len(niveles) > 1:
            nivel = 0   # 0 = varios niveles (el filtro queda en "Todos los niveles")
        else:
            nivel = None  # sinóptico vacío: no se sabe, el frontend no toca el filtro

        resultado.append({
            "id": sinoptico.id,
            "carrera_id": carrera.id,
            "carrera": carrera.nombre,
            "codigo_carrera": carrera.codigo,
            "semestre_id": semestre.id,
            "semestre": f"{semestre.anio}-{semestre.numero}",
            "plan_estudio_id": plan_id,
            "nivel_semestral": nivel,
            "jornada": sinoptico.jornada.value if hasattr(sinoptico.jornada, 'value') else str(sinoptico.jornada),
            "finalizado": sinoptico.finalizado,
            "creado_en": sinoptico.creado_en,
        })
    return resultado


@app.get("/api/sinopticos/{sinoptico_id}/filtros")
def filtros_de_sinoptico(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    """
    Datos para rellenar los filtros de la izquierda al abrir un sinóptico:
    carrera, plan de estudio, semestre, nivel y jornada.
    """
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado.")

    combos = (
        db.query(
            models.Asignatura.plan_estudio_id,
            models.Asignatura.nivel_semestral,
            func.count(models.SinopticoItem.id),
        )
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .group_by(models.Asignatura.plan_estudio_id, models.Asignatura.nivel_semestral)
        .all()
    )
    planes = defaultdict(int)
    niveles = set()
    for plan_id, nivel, cantidad in combos:
        if plan_id is not None:
            planes[plan_id] += cantidad
        if nivel is not None:
            niveles.add(nivel)

    if planes:
        plan_id = max(planes, key=planes.get)
    else:
        # sinóptico vacío: si la carrera tiene un único plan activo, es ese
        planes_carrera = db.query(models.PlanEstudio.id).filter(
            models.PlanEstudio.carrera_id == sinoptico.carrera_id,
            models.PlanEstudio.activo == True,
        ).all()
        plan_id = planes_carrera[0][0] if len(planes_carrera) == 1 else None

    if len(niveles) == 1:
        nivel = next(iter(niveles))
    elif len(niveles) > 1:
        nivel = 0      # varios niveles -> "Todos los niveles"
    else:
        nivel = None   # vacío: no se toca el filtro

    return {
        "carrera_id": sinoptico.carrera_id,
        "plan_estudio_id": plan_id,
        "semestre_id": sinoptico.semestre_id,
        "nivel_semestral": nivel,
        "jornada": sinoptico.jornada.value if hasattr(sinoptico.jornada, "value") else str(sinoptico.jornada),
        "finalizado": sinoptico.finalizado,
    }


def calcular_cumplimiento_horas(db: Session, sinoptico_id: int):
    """
    Horas requeridas de cada asignatura = columna 'horas' de la tabla
    asignatura TAL CUAL (ya es el total de horas que exige el ramo; no se
    multiplica por nada).
    Horas programadas = lo que arma el SINÓPTICO: por cada bloque horario de
    esa asignatura, 1 hora x la cantidad de semanas en que se dicta ese
    bloque (todas las semanas -18, SEMANAS_DEFAULT- si no se marcaron
    semanas específicas). Es este lado el que se multiplica por las semanas,
    no las horas de la asignatura.
    """
    items = (
        db.query(models.SinopticoItem.asignatura_id, models.SinopticoItem.semanas)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )

    horas_programadas = defaultdict(int)
    for asignatura_id, semanas_txt in items:
        lista = parse_semanas(semanas_txt)
        n_semanas = len(lista) if lista else SEMANAS_DEFAULT
        horas_programadas[asignatura_id] += n_semanas  # 1 hora por bloque por semana

    if not horas_programadas:
        return []

    asignaturas = db.query(models.Asignatura).filter(
        models.Asignatura.id.in_(horas_programadas.keys())
    ).all()

    resultado = []
    for asig in asignaturas:
        requeridas = asig.horas or 0
        programadas = horas_programadas.get(asig.id, 0)
        resultado.append({
            "asignatura_id": asig.id,
            "codigo": asig.codigo,
            "nombre": asig.nombre,
            "horas_requeridas": requeridas,
            "horas_programadas": programadas,
            "cumple": programadas == requeridas,
            "diferencia": requeridas - programadas,  # > 0 = faltan horas, < 0 = sobran horas
        })
    return sorted(resultado, key=lambda r: r["nombre"])


@app.get("/api/sinopticos/{sinoptico_id}/horas")
def horas_por_asignatura(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_docente),
):
    """
    Horas requeridas vs. programadas de cada asignatura del sinóptico (18
    semanas, 1 hora por bloque horario). Se usa para mostrar el avance al
    seleccionar una asignatura y para validar el botón 'Finalizar sinóptico'.
    """
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")
    return calcular_cumplimiento_horas(db, sinoptico_id)


class FinalizadoUpdateRequest(BaseModel):
    finalizado: bool


@app.patch("/api/sinopticos/{sinoptico_id}/finalizado")
def actualizar_finalizado_sinoptico(
    sinoptico_id: int,
    datos: FinalizadoUpdateRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
):
    """
    Marca o desmarca un sinóptico como finalizado. Para poder marcarlo como
    finalizado, TODAS las asignaturas que tiene programadas deben cumplir
    exactamente las horas que exige la columna 'horas' de su asignatura
    (18 semanas x 1 hora por bloque horario).
    """
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")

    if datos.finalizado and not sinoptico.finalizado:
        resumen = calcular_cumplimiento_horas(db, sinoptico_id)
        if not resumen:
            raise HTTPException(
                status_code=400,
                detail="No se puede finalizar: el sinóptico todavía no tiene asignaturas programadas.",
            )
        incumplidas = [r for r in resumen if not r["cumple"]]
        if incumplidas:
            detalle = "; ".join(
                f"{r['nombre']} ({r['horas_programadas']} de {r['horas_requeridas']} hrs)"
                for r in incumplidas
            )
            raise HTTPException(
                status_code=400,
                detail=f"No se puede finalizar: hay asignaturas que no cumplen sus horas -> {detalle}",
            )

    sinoptico.finalizado = datos.finalizado
    registrar_cambio(
        db, usuario,
        "sinoptico_finalizado" if datos.finalizado else "sinoptico_reabierto",
        "sinoptico",
        "Finalizó el sinóptico" if datos.finalizado else "Reabrió el sinóptico (quitó finalizado)",
        sinoptico_id=sinoptico_id,
    )
    db.commit()
    db.refresh(sinoptico)
    return {"ok": True, "finalizado": sinoptico.finalizado}


@app.get("/api/sinopticos/eventos")
def eventos_todos_los_sinopticos(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    """
    Trae en UNA sola consulta los eventos de TODOS los sinópticos, agrupados
    por sinoptico_id. Reemplaza el patrón N+1 de pedir
    /sinopticos/{id}/eventos una vez por cada sinóptico (lento con muchos
    sinópticos generados, como en la galería).
    """
    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario, models.Jornada)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .outerjoin(models.Jornada, models.SinopticoItem.jornada_id == models.Jornada.id)
        .all()
    )

    por_sinoptico = defaultdict(list)
    for item, asignatura, profesor, sala, bloque, jornada in filas:
        por_sinoptico[item.sinoptico_id].append({
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
                "tipo": item.tipo,
                "color": item.color,
                "semanas": parse_semanas(item.semanas),
            }
        })

    return {str(sinoptico_id): eventos for sinoptico_id, eventos in por_sinoptico.items()}


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
                "tipo": item.tipo,
                "color": item.color,
                "semanas": parse_semanas(item.semanas),
            }
        })
    return eventos


@app.get("/api/sinopticos/{sinoptico_id}/pdf")
def exportar_sinoptico_pdf(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Exporta el sinóptico a PDF con el formato del boletín de carga académica de Duoc UC."""
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado.")
    carrera = db.query(models.Carrera).filter(models.Carrera.id == sinoptico.carrera_id).first()
    semestre = db.query(models.Semestre).filter(models.Semestre.id == sinoptico.semestre_id).first()

    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )
    items = []
    for item, asignatura, profesor, sala, bloque in filas:
        items.append({
            "asignatura_id": asignatura.id,
            "nombre": asignatura.nombre,
            "codigo": asignatura.codigo,
            "seccion": item.seccion,
            "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else None,
            "sala": sala.nombre if sala else None,
            "dia_semana": bloque.dia_semana,
            "hora_inicio": bloque.hora_inicio,
            "hora_fin": bloque.hora_fin,
            "semanas": parse_semanas(item.semanas),
        })

    # Filas de la grilla: los módulos de la jornada del sinóptico (todos si es mixta)
    consulta_bloques = db.query(models.BloqueHorario.hora_inicio, models.BloqueHorario.hora_fin)
    jornada_val = sinoptico.jornada.value if hasattr(sinoptico.jornada, "value") else str(sinoptico.jornada)
    if jornada_val != "mixta":
        consulta_bloques = consulta_bloques.filter(models.BloqueHorario.jornada == sinoptico.jornada)
    bloques_horas = [(a, b) for a, b in consulta_bloques.distinct().all()]

    pdf = construir_pdf_sinoptico(
        sinoptico_id=sinoptico.id,
        carrera_nombre=carrera.nombre if carrera else "",
        carrera_codigo=carrera.codigo if carrera else "",
        jornada_nombre=jornada_val.capitalize(),
        semestre_numero=semestre.numero if semestre else 1,
        anio=semestre.anio if semestre else LUNES_INICIO_SEMESTRE.year,
        items=items,
        bloques_horas=bloques_horas,
        lunes_inicio=LUNES_INICIO_SEMESTRE,
        fecha_emision=datetime.now(ZoneInfo("America/Santiago")).date(),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sinoptico_{sinoptico.id}.pdf"'},
    )


@app.get("/api/sinopticos/{sinoptico_id}/excel")
def exportar_sinoptico_excel(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Exporta el sinóptico a Excel: hoja 'Horario' (grilla) y hoja 'Detalle' (una fila por bloque)."""
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado.")
    carrera = db.query(models.Carrera).filter(models.Carrera.id == sinoptico.carrera_id).first()
    semestre = db.query(models.Semestre).filter(models.Semestre.id == sinoptico.semestre_id).first()

    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )
    items = []
    for item, asignatura, profesor, sala, bloque in filas:
        items.append({
            "codigo": asignatura.codigo,
            "nombre": asignatura.nombre,
            "seccion": item.seccion,
            "tipo": TIPOS_CLASE.get(item.tipo) if item.tipo else None,
            "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else None,
            "sala": sala.nombre if sala else None,
            "capacidad": item.capacidad_inicial,
            "dia_semana": bloque.dia_semana,
            "hora_inicio": bloque.hora_inicio,
            "hora_fin": bloque.hora_fin,
            "semanas": parse_semanas(item.semanas) or list(range(1, SEMANAS_DEFAULT + 1)),
            "color": item.color,
        })

    consulta_bloques = db.query(models.BloqueHorario.hora_inicio, models.BloqueHorario.hora_fin)
    jornada_val = sinoptico.jornada.value if hasattr(sinoptico.jornada, "value") else str(sinoptico.jornada)
    if jornada_val != "mixta":
        consulta_bloques = consulta_bloques.filter(models.BloqueHorario.jornada == sinoptico.jornada)
    bloques_horas = [(a, b) for a, b in consulta_bloques.distinct().all()]

    contenido = construir_excel_sinoptico(
        sinoptico_id=sinoptico.id,
        carrera_nombre=carrera.nombre if carrera else "",
        jornada_nombre=jornada_val.capitalize(),
        semestre_numero=semestre.numero if semestre else 1,
        anio=semestre.anio if semestre else LUNES_INICIO_SEMESTRE.year,
        items=items,
        bloques_horas=bloques_horas,
    )
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="sinoptico_{sinoptico.id}.xlsx"'},
    )

@app.get("/api/reportes/sabana")
def reporte_sabana(
    semestre_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Sábana de programación global (todos los sinópticos, una hoja por semestre). Solo coordinador y admin."""
    consulta = (
        db.query(
            models.SinopticoItem, models.Sinoptico, models.Carrera, models.Semestre,
            models.Asignatura, models.PlanEstudio, models.Profesor, models.Sala,
            models.BloqueHorario, models.Jornada,
        )
        .join(models.Sinoptico, models.SinopticoItem.sinoptico_id == models.Sinoptico.id)
        .join(models.Carrera, models.Sinoptico.carrera_id == models.Carrera.id)
        .join(models.Semestre, models.Sinoptico.semestre_id == models.Semestre.id)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .outerjoin(models.Jornada, models.SinopticoItem.jornada_id == models.Jornada.id)
    )
    if semestre_id is not None:
        consulta = consulta.filter(models.Sinoptico.semestre_id == semestre_id)

    formacion = {"teorica": "TEO", "practica": "PRA"}
    items = []
    for item, sin, carrera, semestre, asig, plan, prof, sala, bloque, jornada in consulta.all():
        nom_jornada = jornada.nombre if jornada else bloque.jornada.value.capitalize()
        items.append({
            "sinoptico_id": sin.id,
            "asignatura_id": asig.id,
            "profesor_id": item.profesor_id,
            "sala_id": item.sala_id,
            "dia_semana": bloque.dia_semana,
            "hora_inicio": bloque.hora_inicio,
            "hora_fin": bloque.hora_fin,
            "anio": semestre.anio,
            "periodo": semestre.numero,
            "cod_carrera": carrera.codigo,
            "plan": plan.codigo if plan else None,
            "escuela": carrera.nombre,
            "cod_jornada": nom_jornada[:1].upper(),
            "nom_jornada": nom_jornada,
            "nivel": asig.nivel_semestral,
            "id_seccion": item.id_seccion,
            "seccion": item.seccion,
            "nombre_seccion": f"{item.seccion or asig.codigo} {asig.nombre}",
            "cod_asignatura": asig.codigo,
            "nom_asignatura": asig.nombre,
            "formacion": formacion.get(item.tipo),
            "rut": getattr(prof, "rut", None) if prof else None,
            "profesor": f"{prof.nombre} {prof.apellido}" if prof else None,
            "sala": sala.nombre if sala else None,
            "capacidad_sala": getattr(sala, "capacidad", None) if sala else None,
            "duracion_horas": (asig.horas or 0) * SEMANAS_DEFAULT or None,
            "fecha_inicio": item.fecha_inicio,
            "fecha_final": item.fecha_final,
            "capacidad_inicial": item.capacidad_inicial,
        })

    contenido = construir_excel_sabana(items)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sabana_programacion.xlsx"'},
    )

@app.get("/api/salas/eventos")
def eventos_todas_las_salas(db: Session = Depends(get_db), _: models.Usuario = Depends(require_docente)):
    """
    Trae en UNA sola consulta los eventos de TODAS las salas, agrupados por
    sala_id. Reemplaza el patrón N+1 de pedir /salas/{id}/eventos una vez por
    cada sala (que con 15-20 salas dispara 15-20 queries secuenciales).
    """
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
        .filter(models.SinopticoItem.sala_id.isnot(None))
        .all()
    )

    por_sala = defaultdict(list)
    for item, asignatura, profesor, bloque, jornada, sinoptico, carrera, semestre in filas:
        por_sala[item.sala_id].append({
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
                "semanas": parse_semanas(item.semanas),
            }
        })

    # Claves como string para que lleguen limpias en JSON y sean fáciles de indexar en el frontend
    return {str(sala_id): eventos for sala_id, eventos in por_sala.items()}


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
                "semanas": parse_semanas(item.semanas),
            }
        })
    return eventos


TIPOS_CLASE = {"teorica": "Teórica", "practica": "Práctica"}


class SinopticoItemCreateConTipo(schemas.SinopticoItemCreate):
    tipo: Optional[str] = None   # teorica | practica | None


class SinopticoItemUpdateConTipo(schemas.SinopticoItemUpdate):
    tipo: Optional[str] = None


def normalizar_tipo(valor: Optional[str]) -> Optional[str]:
    if valor in (None, ""):
        return None
    if valor not in TIPOS_CLASE:
        raise HTTPException(status_code=400, detail="El tipo de clase debe ser teórica o práctica.")
    return valor


@app.post("/api/sinopticos/items", response_model=schemas.SinopticoItemOut, status_code=201)
def agregar_item_sinoptico(
    datos: SinopticoItemCreateConTipo,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
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
    # Si la asignatura ya tiene semanas elegidas en este sinóptico, el bloque nuevo las hereda
    hermano = db.query(models.SinopticoItem).filter(
        models.SinopticoItem.sinoptico_id == datos.sinoptico_id,
        models.SinopticoItem.asignatura_id == datos.asignatura_id,
    ).first()
    semanas_heredadas = hermano.semanas if hermano else None
    inicio, fin = fechas_para_item(bloque.dia_semana, semanas_heredadas)

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
        tipo=normalizar_tipo(datos.tipo),
        fecha_inicio=inicio,
        fecha_final=fin,
        jornada_id=obtener_jornada_id(db, jornada_para_item),
        color=datos.color or COLOR_DEFAULT,
        semanas=semanas_heredadas,
    )
    db.add(nuevo_item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Error de restricción al guardar el ramo.")

    db.refresh(nuevo_item)
    registrar_cambio(
        db, usuario, "bloque_agregado", "sinoptico",
        f"Agregó {nombre_asignatura(db, nuevo_item.asignatura_id)} en {describir_bloque(db, nuevo_item.bloque_horario_id)}",
        sinoptico_id=nuevo_item.sinoptico_id, profesor_id=nuevo_item.profesor_id,
    )
    db.commit()
    return nuevo_item


@app.put("/api/sinopticos/items/{item_id}", response_model=schemas.SinopticoItemOut)
def editar_item_sinoptico(
    item_id: int,
    datos: SinopticoItemUpdateConTipo,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
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
    item.tipo = normalizar_tipo(datos.tipo)
    if datos.color:
        item.color = datos.color
    item.fecha_inicio, item.fecha_final = fechas_para_item(bloque.dia_semana, item.semanas)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Error al guardar el evento por choque de restricciones."
        )
    db.refresh(item)
    registrar_cambio(
        db, usuario, "bloque_editado", "sinoptico",
        f"Editó {nombre_asignatura(db, item.asignatura_id)} en {describir_bloque(db, item.bloque_horario_id)}",
        sinoptico_id=item.sinoptico_id, profesor_id=item.profesor_id,
    )
    db.commit()
    return item


@app.patch("/api/sinopticos/items/{item_id}/mover")
def mover_item_sinoptico(
    item_id: int,
    datos: schemas.MoverItemRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
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

    bloque_anterior = describir_bloque(db, item.bloque_horario_id)
    item.fecha_inicio, item.fecha_final = fechas_para_item(nuevo_bloque.dia_semana, item.semanas)
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
    registrar_cambio(
        db, usuario, "bloque_movido", "sinoptico",
        f"Movió {nombre_asignatura(db, item.asignatura_id)} de {bloque_anterior} a {describir_bloque(db, nuevo_bloque.id)}",
        sinoptico_id=item.sinoptico_id, profesor_id=item.profesor_id,
    )
    db.commit()
    return {"ok": True, "item_id": item.id, "bloque_horario_id": nuevo_bloque.id}


@app.patch("/api/sinopticos/{sinoptico_id}/asignaturas/{asignatura_id}/color")
def actualizar_color_asignatura(
    sinoptico_id: int,
    asignatura_id: int,
    datos: ColorUpdateRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
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

    registrar_cambio(db, usuario, "color_cambiado", "sinoptico",
                     f"Cambió el color de {nombre_asignatura(db, asignatura_id)}", sinoptico_id=sinoptico_id)
    db.commit()
    return {"ok": True, "actualizados": len(items)}


@app.patch("/api/sinopticos/{sinoptico_id}/asignaturas/{asignatura_id}/semanas")
def actualizar_semanas_asignatura(
    sinoptico_id: int,
    asignatura_id: int,
    datos: SemanasUpdateRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
):
    """
    Define en qué semanas (1..17) se dicta una asignatura dentro de un sinóptico
    (semanal, semana por medio, mensual, o las que se marquen a mano). Se aplica
    a TODOS los bloques de la asignatura en ese sinóptico.
    """
    validas = sorted({w for w in datos.semanas if 1 <= w <= SEMANAS_DEFAULT})
    if not validas:
        raise HTTPException(status_code=400, detail="Debes marcar al menos una semana.")

    items = db.query(models.SinopticoItem).filter(
        models.SinopticoItem.sinoptico_id == sinoptico_id,
        models.SinopticoItem.asignatura_id == asignatura_id,
    ).all()
    if not items:
        raise HTTPException(status_code=404, detail="No hay bloques de esa asignatura en este sinóptico.")

    texto = serializar_semanas(validas)
    for item in items:
        item.semanas = texto
        bloque = db.query(models.BloqueHorario).filter(models.BloqueHorario.id == item.bloque_horario_id).first()
        if bloque:
            item.fecha_inicio, item.fecha_final = fechas_para_item(bloque.dia_semana, texto)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudieron actualizar las semanas.")

    registrar_cambio(db, usuario, "semanas_cambiadas", "sinoptico",
                     f"Cambió las semanas de {nombre_asignatura(db, asignatura_id)}: {texto}", sinoptico_id=sinoptico_id)
    db.commit()
    return {"ok": True, "actualizados": len(items), "semanas": parse_semanas(texto) or list(range(1, SEMANAS_DEFAULT + 1))}


@app.delete("/api/sinopticos/items/{item_id}", status_code=204)
def eliminar_item_sinoptico(
    item_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
):
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El bloque de horario indicado no existe.")
    registrar_cambio(
        db, usuario, "bloque_eliminado", "sinoptico",
        f"Eliminó {nombre_asignatura(db, item.asignatura_id)} de {describir_bloque(db, item.bloque_horario_id)}",
        sinoptico_id=item.sinoptico_id, profesor_id=item.profesor_id,
    )
    db.delete(item)
    db.commit()
    return None


@app.delete("/api/sinopticos/{sinoptico_id}", status_code=204)
def eliminar_sinoptico(
    sinoptico_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(require_coordinador),
):
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")
    registrar_cambio(db, usuario, "sinoptico_eliminado", "sinoptico",
                     "Eliminó el sinóptico completo", sinoptico_id=sinoptico_id)
    db.delete(sinoptico)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# BITÁCORA DE CAMBIOS (quién modificó qué, cuándo y por qué)
# ---------------------------------------------------------------------------
def _registro_a_dict(r: "models.RegistroCambio") -> dict:
    return {
        "id": r.id,
        "fecha": r.creado_en.isoformat() if r.creado_en else None,
        "usuario": r.usuario_nombre,
        "accion": r.accion,
        "entidad": r.entidad,
        "detalle": r.detalle,
        "sinoptico_id": r.sinoptico_id,
        "profesor_id": r.profesor_id,
        "medio": r.medio,
        "medio_texto": MEDIOS_ACUERDO.get(r.medio) if r.medio else None,
        "motivo": r.motivo,
    }


@app.get("/api/sinopticos/{sinoptico_id}/historial")
def historial_sinoptico(
    sinoptico_id: int,
    limite: int = 200,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Quién modificó este sinóptico, qué hizo y cuándo (más reciente primero)."""
    filas = db.query(models.RegistroCambio).filter(
        models.RegistroCambio.sinoptico_id == sinoptico_id
    ).order_by(models.RegistroCambio.creado_en.desc(), models.RegistroCambio.id.desc()).limit(limite).all()
    return [_registro_a_dict(r) for r in filas]


@app.get("/api/profesores/{profesor_id}/historial")
def historial_disponibilidad_profesor(
    profesor_id: int,
    limite: int = 200,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_coordinador),
):
    """Cambios de disponibilidad de un profesor con su motivo y medio de acuerdo."""
    filas = db.query(models.RegistroCambio).filter(
        models.RegistroCambio.profesor_id == profesor_id,
        models.RegistroCambio.entidad == "disponibilidad",
    ).order_by(models.RegistroCambio.creado_en.desc(), models.RegistroCambio.id.desc()).limit(limite).all()
    return [_registro_a_dict(r) for r in filas]


@app.get("/api/admin/bitacora")
def bitacora_general(
    limite: int = 300,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_admin),
):
    filas = db.query(models.RegistroCambio).order_by(
        models.RegistroCambio.creado_en.desc(), models.RegistroCambio.id.desc()
    ).limit(limite).all()
    return [_registro_a_dict(r) for r in filas]


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