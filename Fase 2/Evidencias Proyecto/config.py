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

# --- Entorno y sesión por cookie ---
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
PRODUCCION = APP_ENV == "production"


def _booleano(nombre: str, defecto: bool) -> bool:
    valor = os.environ.get(nombre)
    if valor is None or not valor.strip():
        return defecto
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes")


# Orígenes del frontend autorizados (CORS + verificación de Origin en peticiones que modifican datos)
CORS_ORIGINS = [
    o.strip().rstrip("/") for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    ).split(",") if o.strip()
]
if "*" in CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS no puede contener '*': la sesión viaja en una cookie y necesita orígenes explícitos.")

# Cookie de sesión: HttpOnly siempre; Secure por defecto en producción (obligatorio allí)
COOKIE_SECURE = _booleano("COOKIE_SECURE", PRODUCCION)
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()   # lax | strict | none
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "").strip() or None          # solo si API y web están en subdominios distintos
if COOKIE_SAMESITE not in ("lax", "strict", "none"):
    raise RuntimeError("COOKIE_SAMESITE debe ser lax, strict o none.")
if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError("COOKIE_SAMESITE=none exige COOKIE_SECURE=1.")
if PRODUCCION and not COOKIE_SECURE:
    raise RuntimeError("En producción COOKIE_SECURE debe estar activo (HTTPS).")
if PRODUCCION and any(not o.startswith("https://") for o in CORS_ORIGINS):
    raise RuntimeError("En producción todos los CORS_ORIGINS deben ser https://")
# Con el prefijo __Host- el navegador rechaza cookies sin Secure, sin Path=/ o con Domain
COOKIE_NAME = "__Host-sesion" if (COOKIE_SECURE and not COOKIE_DOMAIN) else "sesion"

# Autenticación por cabecera Bearer (solo herramientas externas); la web usa SIEMPRE la cookie
PERMITIR_BEARER = _booleano("PERMITIR_BEARER", False)

# True: un coordinador solo modifica los sinópticos que creó él (el administrador modifica todos)
COORDINADOR_EDITA_SOLO_LO_SUYO = _booleano("COORDINADOR_EDITA_SOLO_LO_SUYO", True)

# --- Cifrado de datos sensibles (opcionales hasta que se active el cifrado del RUT) ---
DATA_ENCRYPTION_KEY = os.environ.get("DATA_ENCRYPTION_KEY", "").strip()
DATA_HASH_KEY = os.environ.get("DATA_HASH_KEY", "").strip()
