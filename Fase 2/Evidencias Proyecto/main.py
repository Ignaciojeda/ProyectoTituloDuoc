from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import defaultdict # nuevo

from database import engine, get_db, Base
import models
import schemas # nuevo: importamos schemas para usarlo en la ruta de asignaturas

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Crea las tablas en Postgres (si no existen) al levantar el servidor
Base.metadata.create_all(bind=engine)

# diccionario de palabras clave
PALABRA_CLAVE_AREA = {
    "informatica": ["programacion", "base de datos", "software", "sistemas"],
    "redes": ["redes"],
    "matematica": ["matematica", "algebra", "calculo"],
    # aca se pueden agregar mas basado en las asignaturas reales
}

def area_para_asignatura(nombre_asignatura: str):
    nombre = nombre_asignatura.lower()
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre for p in palabras):
            return area
    return None


@app.get("/")
def inicio(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/pag2")
def segunda(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pag2.html",
        context={}
    )

# --- conexión---
@app.get("/asignaturas")
def listar_asignaturas(db: Session = Depends(get_db)):
    return db.query(models.Asignatura).all()

# NUEVCO: ruta para crear asignaturas usando el esquema AsignaturaCreate y devolviendo AsignaturaOut
@app.post("/asignaturas", response_model=schemas.AsignaturaOut)
def crear_asignatura(datos: schemas.AsignaturaCreate, db: Session = Depends(get_db)):
    nueva = models.Asignatura(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# NUEVO: ruta para generar sinoptico(s)
@app.post("/sinopticos/generar")
def generar_sinoptico(datos: schemas.GenerarSinopticoRequest, db: Session = Depends(get_db)):
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
    db.flush()  # Asegura que el ID del sinoptico esté disponible

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