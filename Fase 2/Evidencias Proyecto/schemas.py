from datetime import date, time, datetime
from pydantic import BaseModel, EmailStr, Field
from models import JornadaTipo, AreaDocenteTipo, RolUsuario, EdificioTipo
from typing import Optional


# --- Jornada ---
class JornadaOut(BaseModel):
    id: int
    codigo: str
    nombre: str

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
class SemestreOut(BaseModel):
    id: int
    anio: int
    numero: int
    fecha_inicio: date
    fecha_fin: date
    activo: bool

    class Config:
        from_attributes = True


# --- Profesor ---
class ProfesorOut(BaseModel):
    id: int
    rut: str
    nombre: str
    apellido: str
    email: str
    area_docente: AreaDocenteTipo
    activo: bool

    class Config:
        from_attributes = True


# --- Asignatura ---
class AsignaturaCreate(BaseModel):
    codigo: str
    nombre: str
    plan_estudio_id: Optional[int] = None
    horas: Optional[int] = None
    nivel_semestral: Optional[int] = None

class AsignaturaOut(AsignaturaCreate):
    id: int

    class Config:
        from_attributes = True


# --- Sala ---
class SalaOut(BaseModel):
    id: int
    nombre: str
    edificio: EdificioTipo
    cantidad_sillas: int
    activo: bool

    class Config:
        from_attributes = True


# --- Bloque horario ---
class BloqueHorarioOut(BaseModel):
    id: int
    dia_semana: int = Field(ge=1, le=6)
    hora_inicio: time
    hora_fin: time
    jornada: JornadaTipo

    class Config:
        from_attributes = True


# --- Generar sinóptico ---
class GenerarSinopticoRequest(BaseModel):
    carrera_id: int
    semestre_id: int
    jornada: JornadaTipo


# --- Mover ítem ---
class MoverItemRequest(BaseModel):
    dia_semana: int = Field(ge=1, le=6)
    hora_inicio: time
    hora_fin: time
    jornada: JornadaTipo


# --- Sinóptico Item ---
class SinopticoItemCreate(BaseModel):
    sinoptico_id: int
    asignatura_id: int
    profesor_id: Optional[int] = None
    sala_id: Optional[int] = None
    bloque_horario_id: int
    jornada_id: Optional[int] = None
    id_seccion: Optional[str] = None
    seccion: Optional[str] = None
    capacidad_inicial: Optional[int] = None

class SinopticoItemUpdate(BaseModel):
    asignatura_id: int
    profesor_id: Optional[int] = None
    sala_id: Optional[int] = None
    bloque_horario_id: int
    jornada_id: Optional[int] = None
    id_seccion: Optional[str] = None
    seccion: Optional[str] = None
    capacidad_inicial: Optional[int] = None

class SinopticoItemOut(SinopticoItemCreate):
    id: int
    capacidad_inicial: Optional[int] = None

    class Config:
        from_attributes = True


# --- Usuario ---
class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    rol: RolUsuario
    activo: bool

    class Config:
        from_attributes = True


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    rol: RolUsuario = RolUsuario.coordinador


# --- Auditoría ---
class LoginLogOut(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    email_intentado: str
    exito: bool
    motivo_fallo: Optional[str] = None
    ip_origen: Optional[str] = None
    creado_en: datetime

    class Config:
        from_attributes = True


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut