from sqlalchemy import (
    Column, Integer, SmallInteger, String, Boolean,
    Date, DateTime, ForeignKey, Enum, UniqueConstraint, func
)
from database import Base
import enum


class JornadaTipo(str, enum.Enum):
    diurno = "diurno"
    vespertino = "vespertino"


class RolUsuario(str, enum.Enum):
    administrador = "administrador"
    coordinador = "coordinador"
    docente = "docente"


class Carrera(Base):
    __tablename__ = "carrera"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())


class Semestre(Base):
    __tablename__ = "semestre"
    __table_args__ = (UniqueConstraint("anio", "numero"),)

    id = Column(Integer, primary_key=True)
    anio = Column(Integer, nullable=False)
    numero = Column(SmallInteger, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Profesor(Base):
    __tablename__ = "profesor"

    id = Column(Integer, primary_key=True)
    rut = Column(String(12), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    especialidad = Column(String(150))
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())


class Sala(Base):
    __tablename__ = "sala"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    cantidad_sillas = Column(Integer, nullable=False)
    edificio = Column(String(100))
    piso = Column(SmallInteger)
    activo = Column(Boolean, nullable=False, default=True)


class Asignatura(Base):
    __tablename__ = "asignatura"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False)
    carrera_id = Column(Integer, ForeignKey("carrera.id"), nullable=True)
    creditos = Column(SmallInteger)
    horas_semanales = Column(SmallInteger)
    activo = Column(Boolean, nullable=False, default=True)


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.coordinador)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())