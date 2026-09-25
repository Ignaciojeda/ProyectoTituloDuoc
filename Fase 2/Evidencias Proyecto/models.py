from sqlalchemy import (
    Column, Integer, SmallInteger, String, Boolean,
    Date, DateTime, Time, ForeignKey, Enum, CheckConstraint,
    UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class JornadaTipo(str, enum.Enum):
    diurno = "diurno"
    vespertino = "vespertino"


class RolUsuario(str, enum.Enum):
    administrador = "administrador"
    coordinador = "coordinador"
    docente = "docente"


class AreaDocenteTipo(str, enum.Enum):
    informatica = "informatica"
    redes = "redes"
    contabilidad = "contabilidad"
    administracion = "administracion"
    prevencion_riesgos = "prevencion_riesgos"
    trabajo_social = "trabajo_social"
    diseno_grafico = "diseno_grafico"
    turismo = "turismo"
    gastronomia = "gastronomia"
    enfermeria = "enfermeria"
    matematica = "matematica"
    lenguaje = "lenguaje"
    ingles = "ingles"


class Carrera(Base):
    __tablename__ = "carrera"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())

    planes_estudio = relationship("PlanEstudio", back_populates="carrera")


class PlanEstudio(Base):
    """
    Una carrera puede tener varios planes de estudio a lo largo
    del tiempo (cambios de malla curricular). 'vigente_hasta' en
    NULL significa que es el plan vigente actualmente.
    """
    __tablename__ = "plan_estudio"

    id = Column(Integer, primary_key=True)
    carrera_id = Column(Integer, ForeignKey("carrera.id", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(30), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    carrera = relationship("Carrera", back_populates="planes_estudio")
    asignaturas = relationship("Asignatura", back_populates="plan_estudio")


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
    area_docente = Column(Enum(AreaDocenteTipo), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())


class Sala(Base):
    __tablename__ = "sala"
    __table_args__ = (
        CheckConstraint("edificio IN ('W', 'Y', 'Z')", name="ck_sala_edificio"),
    )

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)  # ej. 'W-101'
    edificio = Column(String(1), nullable=False)
    cantidad_sillas = Column(Integer, nullable=False)
    piso = Column(SmallInteger)
    activo = Column(Boolean, nullable=False, default=True)


class Asignatura(Base):
    __tablename__ = "asignatura"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    plan_estudio_id = Column(Integer, ForeignKey("plan_estudio.id", ondelete="SET NULL"), nullable=True)
    horas = Column(SmallInteger)
    activo = Column(Boolean, nullable=False, default=True)

    plan_estudio = relationship("PlanEstudio", back_populates="asignaturas")


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.coordinador)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())

#NUEVO (creación de tabla bloque horario, sinoptico y sinoptico item), copiado de antes del git pull
class BloqueHorario(Base):
    __tablename__ = "bloque_horario"
    __table_args__ = (UniqueConstraint("dia_semana", "hora_inicio", "jornada"),)

    id = Column(Integer, primary_key=True)
    dia_semana = Column(SmallInteger, nullable=False)  # 1=Lunes ... 6=Sábado
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False)


class Sinoptico(Base):
    __tablename__ = "sinoptico"

    id = Column(Integer, primary_key=True)
    carrera_id = Column(Integer, ForeignKey("carrera.id"), nullable=False)
    semestre_id = Column(Integer, ForeignKey("semestre.id"), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())


class SinopticoItem(Base):
    __tablename__ = "sinoptico_item"

    id = Column(Integer, primary_key=True)
    sinoptico_id = Column(Integer, ForeignKey("sinoptico.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignatura.id"), nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesor.id"))
    sala_id = Column(Integer, ForeignKey("sala.id"))
    bloque_horario_id = Column(Integer, ForeignKey("bloque_horario.id"), nullable=False)