import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

import config

logger = logging.getLogger("sinoptico")

# URL.create escapa solos los caracteres especiales de la clave (@, :, /, #, etc.)
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=config.DB_USER,
    password=config.DB_PASSWORD,
    host=config.DB_HOST,
    port=config.DB_PORT,
    database=config.DB_NAME,
)

# Nunca imprimir la URL completa: incluye la contraseña. Solo host, puerto y base.
logger.info("Conectando a la base de datos en %s:%s/%s", config.DB_HOST, config.DB_PORT, config.DB_NAME)

connect_args = {"prepare_threshold": None}   # necesario con el pooler de Supabase (modo transacción)
if config.DB_HOST not in ("localhost", "127.0.0.1", "db"):
    connect_args["sslmode"] = "require"       # conexión cifrada obligatoria hacia servidores remotos


def _entero(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, defecto))
    except ValueError:
        return defecto


# Ajustes del pool de conexiones. Se pueden cambiar desde el .env sin tocar el código, para comparar en las pruebas de carga:
#   DB_PRE_PING=0     -> no hace un "SELECT 1" antes de cada uso (ahorra una ida y vuelta a la base por petición)
#   DB_POOL_SIZE / DB_MAX_OVERFLOW -> conexiones del backend (el pooler de Supabase tiene su propio límite)
#   DB_POOL_TIMEOUT   -> segundos de espera por una conexión antes de fallar (falla rápido en vez de colgarse)
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=os.environ.get("DB_PRE_PING", "1") != "0",
    pool_recycle=_entero("DB_POOL_RECYCLE", 300),    # renueva conexiones cada 5 min (antes 30)
    pool_size=_entero("DB_POOL_SIZE", 10),
    max_overflow=_entero("DB_MAX_OVERFLOW", 10),
    pool_timeout=_entero("DB_POOL_TIMEOUT", 10),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()