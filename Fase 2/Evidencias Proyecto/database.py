import logging

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

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=1800,    # renueva conexiones inactivas cada 30 min
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()