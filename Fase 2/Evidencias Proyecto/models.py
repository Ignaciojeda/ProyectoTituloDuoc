from sqlalchemy import (
    Column, Integer, SmallInteger, String, Boolean,
    Date, DateTime, Time, ForeignKey, Enum, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class JornadaTipo(str, enum.Enum):
    diurno = "diurno"
    vespertino = "vespertino"
    mixta = "mixta"


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


class EdificioTipo(str, enum.Enum):
    W = "W"
    Y = "Y"
    Z = "Z"
    GYM = "GYM"
    BIBLIO = "BIBLIO"
    VIRTUAL = "VIRTUAL"
    CC = "CC"
    TERR = "TERR"


class Carrera(Base):
    """Corresponde a 'Escuela' en la sábana de programación real."""
    __tablename__ = "carrera"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())

    planes_estudio = relationship("PlanEstudio", back_populates="carrera")


class PlanEstudio(Base):
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
    """Salas reales de la sede Puerto Montt (edificios W, Y, Z,
    más ubicaciones especiales: gimnasio, biblioteca, salas
    virtuales, campos clínicos y terreno)."""
    __tablename__ = "sala"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)  # ej. 'W602', 'VIRTUAL01'
    edificio = Column(Enum(EdificioTipo), nullable=False)
    cantidad_sillas = Column(Integer, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Asignatura(Base):
    __tablename__ = "asignatura"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    plan_estudio_id = Column(Integer, ForeignKey("plan_estudio.id", ondelete="SET NULL"), nullable=True)
    horas = Column(SmallInteger)
    nivel_semestral = Column(SmallInteger, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    plan_estudio = relationship("PlanEstudio", back_populates="asignaturas")


class BloqueHorario(Base):
    """Catálogo compartido de módulos horarios reales de Duoc."""
    __tablename__ = "bloque_horario"
    __table_args__ = (UniqueConstraint("dia_semana", "hora_inicio", "hora_fin", "jornada"),)

    id = Column(Integer, primary_key=True)
    dia_semana = Column(SmallInteger, nullable=False)  # 1=Lunes ... 6=Sábado
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False)


class Sinoptico(Base):
    """Un 'lote' de asignaturas generado (o editado a mano) para
    una carrera y un semestre. No guarda jornada: eso se usa solo
    al generar, para filtrar qué bloques ofrecer."""
    __tablename__ = "sinoptico"

    id = Column(Integer, primary_key=True)
    carrera_id = Column(Integer, ForeignKey("carrera.id"), nullable=False)
    semestre_id = Column(Integer, ForeignKey("semestre.id"), nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())


class SinopticoItem(Base):
    """Una clase dentro de un sinóptico: asignatura + profesor +
    sala + bloque horario. profesor_id y sala_id son nullable
    (una clase puede quedar 'sin asignar' temporalmente)."""
    __tablename__ = "sinoptico_item"

    id = Column(Integer, primary_key=True)
    sinoptico_id = Column(Integer, ForeignKey("sinoptico.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignatura.id"), nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesor.id", ondelete="SET NULL"), nullable=True)
    sala_id = Column(Integer, ForeignKey("sala.id", ondelete="SET NULL"), nullable=True)
    bloque_horario_id = Column(Integer, ForeignKey("bloque_horario.id"), nullable=False)

    # Cupos de este bloque/sala específico -- permite dividir un
    # curso grande en más de una sala. No se usa todavía en main.py.
    capacidad_inicial = Column(SmallInteger, nullable=True)

    # Para exportar en el mismo formato de la sábana real más
    # adelante. No se usan todavía en main.py.
    codigo_seccion = Column(String(30), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_final = Column(Date, nullable=True)


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.coordinador)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())