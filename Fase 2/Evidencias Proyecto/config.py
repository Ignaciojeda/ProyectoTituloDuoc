"""
Configuración central. TODOS los secretos salen de variables de entorno (.env); nunca del código.
Mantiene los nombres que ya usan ustedes (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME).
"""
import os

from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env si existe (en Docker/servidor las variables ya vienen definidas)


def _requerida(nombre: str, largo_minimo: int = 1) -> str:
    valor = os.environ.get(nombre, "").strip()
    if len(valor) < largo_minimo:
        raise RuntimeError(
            f"Falta la variable de entorno {nombre}"
            + (f" (mínimo {largo_minimo} caracteres)" if largo_minimo > 1 else "")
            + ". Copia .env.example como .env y complétala."
        )
    return valor


# --- Base de datos ---
DB_USER = _requerida("DB_USER")
DB_PASSWORD = _requerida("DB_PASSWORD")
DB_HOST = _requerida("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = _requerida("DB_NAME")

# --- Sesiones (JWT) ---
SECRET_KEY = _requerida("SECRET_KEY", largo_minimo=32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "60"))

# --- Cifrado de datos sensibles (opcionales hasta que se active el cifrado del RUT) ---
DATA_ENCRYPTION_KEY = os.environ.get("DATA_ENCRYPTION_KEY", "").strip()
DATA_HASH_KEY = os.environ.get("DATA_HASH_KEY", "").strip()