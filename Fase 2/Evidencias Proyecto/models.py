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


# --- Tabla Independiente Jornada ---
class Jornada(Base):
    __tablename__ = "jornada"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(10), unique=True, nullable=False)  # 'D', 'V', 'M'
    nombre = Column(String(50), nullable=False)              # 'Diurno', 'Vespertino', 'Mixta'


class Carrera(Base):
    """Corresponde a 'Escuela / Clase' en la sábana real (ej. codigo='A163')."""
    __tablename__ = "carrera"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())

    planes_estudio = relationship("PlanEstudio", back_populates="carrera")


class PlanEstudio(Base):
    """Corresponde a 'Plan Estudio' real (ej. codigo='1116316')."""
    __tablename__ = "plan_estudio"

    id = Column(Integer, primary_key=True)
    carrera_id = Column(Integer, ForeignKey("carrera.id", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(50), unique=True, nullable=False)
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

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    edificio = Column(Enum(EdificioTipo), nullable=False)
    cantidad_sillas = Column(Integer, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Asignatura(Base):
    """Corresponde a 'Cod Asignatura' real (ej. codigo='ABA1101')."""
    __tablename__ = "asignatura"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    plan_estudio_id = Column(Integer, ForeignKey("plan_estudio.id", ondelete="SET NULL"), nullable=True)
    horas = Column(SmallInteger)
    nivel_semestral = Column(SmallInteger, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    plan_estudio = relationship("PlanEstudio", back_populates="asignaturas")


class BloqueHorario(Base):
    __tablename__ = "bloque_horario"
    __table_args__ = (UniqueConstraint("dia_semana", "hora_inicio", "hora_fin", "jornada"),)

    id = Column(Integer, primary_key=True)
    dia_semana = Column(SmallInteger, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False)


class Sinoptico(Base):
    __tablename__ = "sinoptico"

    id = Column(Integer, primary_key=True)
    carrera_id = Column(Integer, ForeignKey("carrera.id"), nullable=False)
    semestre_id = Column(Integer, ForeignKey("semestre.id"), nullable=False)
    jornada = Column(Enum(JornadaTipo), nullable=False, default=JornadaTipo.diurno) # <--- Asegurar este campo
    creado_en = Column(DateTime, server_default=func.now())


class SinopticoItem(Base):
    """Eventos individuales dentro de un sinóptico."""
    __tablename__ = "sinoptico_item"
    __table_args__ = (
        UniqueConstraint("profesor_id", "bloque_horario_id", name="uq_item_profesor_bloque"),
        UniqueConstraint("sala_id", "bloque_horario_id", name="uq_item_sala_bloque"),
    )

    id = Column(Integer, primary_key=True)
    sinoptico_id = Column(Integer, ForeignKey("sinoptico.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignatura.id"), nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesor.id", ondelete="SET NULL"), nullable=True)
    sala_id = Column(Integer, ForeignKey("sala.id", ondelete="SET NULL"), nullable=True)
    bloque_horario_id = Column(Integer, ForeignKey("bloque_horario.id"), nullable=False)
    jornada_id = Column(Integer, ForeignKey("jornada.id", ondelete="SET NULL"), nullable=True)

    # Reemplazo oficial: ID Seccion (ej: '24478875') y Seccion (ej: 'ABA1101-001V')
    id_seccion = Column(String(30), nullable=True)
    seccion = Column(String(50), nullable=True)

    capacidad_inicial = Column(SmallInteger, nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_final = Column(Date, nullable=True)

    jornada = relationship("Jornada")


class LoginLog(Base):
    __tablename__ = "login_log"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    email_intentado = Column(String(150), nullable=False)
    exito = Column(Boolean, nullable=False)
    motivo_fallo = Column(String(100), nullable=True)
    ip_origen = Column(String(45), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.coordinador)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())