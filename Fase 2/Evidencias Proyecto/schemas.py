from datetime import date, time
from pydantic import BaseModel
from models import JornadaTipo, AreaDocenteTipo


# --- Asignatura ---
# OJO: estos campos deben calzar con los de models.Asignatura (antes tenía
# carrera_id/creditos/horas_semanales, que no existen en el modelo y hacían
# fallar la creación).
class AsignaturaCreate(BaseModel):
    codigo: str
    nombre: str
    jornada: JornadaTipo
    plan_estudio_id: int | None = None
    horas: int | None = None

class AsignaturaOut(AsignaturaCreate):
    id: int

    class Config:
        from_attributes = True


# --- Carrera ---
class CarreraCreate(BaseModel):
    codigo: str
    nombre: str

class CarreraOut(CarreraCreate):
    id: int

    class Config:
        from_attributes = True


# --- Plan de estudio ---
class PlanEstudioCreate(BaseModel):
    carrera_id: int
    codigo: str
    nombre: str
    vigente_desde: date
    vigente_hasta: date | None = None

class PlanEstudioOut(PlanEstudioCreate):
    id: int

    class Config:
        from_attributes = True


# --- Semestre ---
class SemestreCreate(BaseModel):
    anio: int
    numero: int
    fecha_inicio: date
    fecha_fin: date

class SemestreOut(SemestreCreate):
    id: int

    class Config:
        from_attributes = True


# --- Profesor ---
class ProfesorCreate(BaseModel):
    rut: str
    nombre: str
    apellido: str
    email: str
    area_docente: AreaDocenteTipo

class ProfesorOut(ProfesorCreate):
    id: int

    class Config:
        from_attributes = True


# --- Sala ---
class SalaCreate(BaseModel):
    nombre: str
    edificio: str          # 'W', 'Y' o 'Z'
    cantidad_sillas: int
    piso: int | None = None

class SalaOut(SalaCreate):
    id: int

    class Config:
        from_attributes = True


# --- Bloque horario (día + hora inicio/fin) ---
class BloqueHorarioCreate(BaseModel):
    dia_semana: int        # 1=Lunes ... 6=Sábado
    hora_inicio: time
    hora_fin: time
    jornada: JornadaTipo

class BloqueHorarioOut(BloqueHorarioCreate):
    id: int

    class Config:
        from_attributes = True


# --- Generar sinóptico ---
class GenerarSinopticoRequest(BaseModel):
    carrera_id: int
    semestre_id: int


# --- Construcción manual del sinóptico ---
class SinopticoCreate(BaseModel):
    carrera_id: int
    semestre_id: int

class SinopticoOut(SinopticoCreate):
    id: int

    class Config:
        from_attributes = True


class SinopticoItemCreate(BaseModel):
    sinoptico_id: int
    asignatura_id: int
    profesor_id: int | None = None
    sala_id: int | None = None
    bloque_horario_id: int

class SinopticoItemOut(SinopticoItemCreate):
    id: int

    class Config:
        from_attributes = True