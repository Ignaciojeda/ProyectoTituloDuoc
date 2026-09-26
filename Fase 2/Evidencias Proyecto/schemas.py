from datetime import date, time
from pydantic import BaseModel, EmailStr, Field
from models import JornadaTipo, AreaDocenteTipo, RolUsuario
from typing import Optional


# --- Asignatura ---
class AsignaturaCreate(BaseModel):
    codigo: str
    nombre: str
    plan_estudio_id: Optional[int] = None
    horas: Optional[int] = None

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
    vigente_hasta: Optional[date] = None

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
    edificio: str
    cantidad_sillas: int
    piso: Optional[int] = None

class SalaOut(SalaCreate):
    id: int

    class Config:
        from_attributes = True


# --- Bloque horario ---
class BloqueHorarioCreate(BaseModel):
    dia_semana: int
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
    jornada: JornadaTipo


# --- Sinóptico ---
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
    profesor_id: Optional[int] = None
    sala_id: Optional[int] = None
    bloque_horario_id: int

class SinopticoItemOut(SinopticoItemCreate):
    id: int

    class Config:
        from_attributes = True


class MoverItemRequest(BaseModel):
    dia_semana: int
    hora_inicio: time
    hora_fin: time
    jornada: JornadaTipo


class SinopticoItemUpdate(BaseModel):
    asignatura_id: int
    profesor_id: Optional[int] = None
    sala_id: Optional[int] = None
    bloque_horario_id: int


# --- Usuario Out ---
class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    rol: RolUsuario
    activo: bool

    class Config:
        from_attributes = True


# --- Auth / Tokens ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut


# --- Usuario CRUD ---
class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    rol: RolUsuario = RolUsuario.coordinador


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    rol: Optional[RolUsuario] = None
    activo: Optional[bool] = None