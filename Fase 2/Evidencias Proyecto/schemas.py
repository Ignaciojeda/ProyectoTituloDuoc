from pydantic import BaseModel
from models import JornadaTipo

class AsignaturaCreate(BaseModel):
    codigo: str
    nombre: str
    jornada: JornadaTipo
    carrera_id: int | None = None
    creditos: int | None = None
    horas_semanales: int | None = None

class AsignaturaOut(AsignaturaCreate):
    id: int

    class Config:
        from_attributes = True

class GenerarSinopticoRequest(BaseModel):
    carrera_id: int
    semestre_id: int