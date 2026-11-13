import re
from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from models import JornadaTipo, AreaDocenteTipo, RolUsuario, EdificioTipo
from typing import Optional, List


class Estricto(BaseModel):
    """
    Base de TODO lo que el cliente envía: rechaza (422) cualquier campo no declarado, en vez de ignorarlo
    en silencio. Así no se pueden colar campos como rol, activo, creado_por_id, finalizado o password_hash.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Jornada ---
class JornadaOut(BaseModel):
    id: int
    codigo: str
    nombre: str

    class Config:
        from_attributes = True


# --- Carrera ---
class CarreraCreate(Estricto):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)

class CarreraOut(CarreraCreate):
    id: int

    class Config:
        from_attributes = True


# --- Plan de estudio ---
class PlanEstudioCreate(Estricto):
    carrera_id: int = Field(ge=1)
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=100)
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
    nombre: str
    apellido: str
    email: str
    area_docente: AreaDocenteTipo
    activo: bool

    class Config:
        from_attributes = True


# --- Asignatura ---
class AsignaturaCreate(Estricto):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    plan_estudio_id: Optional[int] = Field(default=None, ge=1)
    horas: Optional[int] = Field(default=None, ge=1, le=500)
    nivel_semestral: Optional[int] = Field(default=None, ge=1, le=12)

class AsignaturaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    plan_estudio_id: Optional[int] = None
    horas: Optional[int] = None
    nivel_semestral: Optional[int] = None

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
class GenerarSinopticoRequest(Estricto):
    carrera_id: int = Field(ge=1)
    semestre_id: int = Field(ge=1)
    jornada: JornadaTipo = JornadaTipo.diurno
    plan_estudio_id: Optional[int] = Field(default=None, ge=1)
    nivel_semestral: Optional[int] = Field(default=None, ge=0, le=12)


class SinopticoOut(BaseModel):
    id: int
    carrera_id: int
    semestre_id: int
    jornada: JornadaTipo
    finalizado: bool
    creado_en: datetime

    class Config:
        from_attributes = True


# --- Mover ítem ---
class MoverItemRequest(Estricto):
    dia_semana: int = Field(ge=1, le=6)
    hora_inicio: time
    hora_fin: time
    jornada: JornadaTipo


# --- Color (hexadecimal) ---
COLOR_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

def _normalizar_color(valor):
    """None o '' = sin color elegido (el backend usa el color por defecto).
    Si viene un valor, debe ser un hexadecimal #RRGGBB; se guarda en minúsculas."""
    if valor is None or valor == "":
        return None
    if not COLOR_HEX_RE.fullmatch(valor):
        raise ValueError("El color debe ser un código hexadecimal con formato #RRGGBB (ej. #2563eb).")
    return valor.lower()


# --- Sinóptico Item ---
class SinopticoItemCreate(Estricto):
    # La jornada del bloque NO la envía el cliente: el servidor la deduce del sinóptico y del bloque.
    sinoptico_id: int = Field(ge=1)
    asignatura_id: int = Field(ge=1)
    profesor_id: Optional[int] = Field(default=None, ge=1)
    sala_id: Optional[int] = Field(default=None, ge=1)
    bloque_horario_id: int = Field(ge=1)
    capacidad_inicial: Optional[int] = Field(default=None, ge=0, le=1000)
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validar_color(cls, v):
        return _normalizar_color(v)

class SinopticoItemUpdate(Estricto):
    asignatura_id: int = Field(ge=1)
    profesor_id: Optional[int] = Field(default=None, ge=1)
    sala_id: Optional[int] = Field(default=None, ge=1)
    bloque_horario_id: int = Field(ge=1)
    capacidad_inicial: Optional[int] = Field(default=None, ge=0, le=1000)
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validar_color(cls, v):
        return _normalizar_color(v)

class SinopticoItemOut(BaseModel):
    id: int
    sinoptico_id: int
    asignatura_id: int
    profesor_id: Optional[int] = None
    sala_id: Optional[int] = None
    bloque_horario_id: int
    jornada_id: Optional[int] = None
    capacidad_inicial: Optional[int] = None
    color: Optional[str] = None

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


class UsuarioCreate(Estricto):
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
class LoginRequest(Estricto):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)

class SesionResponse(BaseModel):
    """El JWT NO viaja aquí: va solo en la cookie HttpOnly. csrf_token se reenvía en la cabecera X-CSRF-Token."""
    user: UsuarioOut
    csrf_token: str
