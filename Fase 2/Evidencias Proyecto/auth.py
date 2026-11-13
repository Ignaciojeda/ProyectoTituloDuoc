"""
Autenticación y autorización del lado del servidor.

- La sesión es un JWT guardado en una cookie HttpOnly (JavaScript no puede leerla, así que un XSS no la roba).
- Como el navegador envía la cookie solo, toda petición que modifica datos (POST/PUT/PATCH/DELETE) debe traer
  además la cabecera X-CSRF-Token. Ese valor va dentro del JWT (claim "csrf"), se entrega al frontend en la
  respuesta de /auth/login y /auth/me, y un sitio ajeno no puede leerlo (CORS).
- Las comprobaciones viven en las dependencias (get_current_user / require_role): ningún endpoint las
  puede olvidar sin quedar visiblemente desprotegido.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config
import models
from database import get_db

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_MINUTES

COOKIE_NAME = config.COOKIE_NAME
CSRF_HEADER = "X-CSRF-Token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash de una contraseña inexistente: el login tarda lo mismo exista o no el correo
_HASH_FALSO: Optional[str] = None


# --- Contraseñas ---------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def huella_password(password_hash: str) -> str:
    """Huella corta de la contraseña actual: si el usuario la cambia, los tokens anteriores dejan de valer."""
    return hmac.new(SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:16]


# --- Sesión (JWT en cookie HttpOnly) -------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    ahora = datetime.now(timezone.utc)
    expire = ahora + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": ahora})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def emitir_sesion(user: models.Usuario) -> tuple[str, str]:
    """Devuelve (jwt, csrf_token). El csrf_token viaja dentro del JWT y también se entrega al frontend."""
    csrf = secrets.token_urlsafe(32)
    token = create_access_token({
        "sub": str(user.id),
        "pv": huella_password(user.password_hash),
        "csrf": csrf,
        "jti": secrets.token_hex(8),
    })
    return token, csrf


def poner_cookie_sesion(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",                       # requisito del prefijo __Host-
        domain=config.COOKIE_DOMAIN,
        secure=config.COOKIE_SECURE,
        httponly=True,                  # inaccesible desde JavaScript
        samesite=config.COOKIE_SAMESITE,
    )


def borrar_cookie_sesion(response: Response) -> None:
    # Los atributos deben coincidir con los de set_cookie, o el navegador no la elimina
    response.delete_cookie(
        key=COOKIE_NAME, path="/", domain=config.COOKIE_DOMAIN,
        secure=config.COOKIE_SECURE, httponly=True, samesite=config.COOKIE_SAMESITE,
    )


def _extraer_token(request: Request) -> tuple[Optional[str], bool]:
    """(token, vino_por_cookie). La cookie manda; la cabecera Bearer solo si se habilitó expresamente."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token, True
    if config.PERMITIR_BEARER:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer ") and len(auth) > 7:
            return auth[7:].strip(), False
    return None, False


# --- Autenticación y dependencias ----------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Usuario]:
    global _HASH_FALSO
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email.strip().lower(), models.Usuario.activo == True)
        .first()
    )
    if not user:
        if _HASH_FALSO is None:
            _HASH_FALSO = pwd_context.hash("contrasena-inexistente")
        verify_password(password, _HASH_FALSO)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.Usuario:
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
    )
    token, por_cookie = _extraer_token(request)
    if not token:
        raise credenciales_invalidas

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require_exp": True})
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credenciales_invalidas

    user = db.query(models.Usuario).filter(
        models.Usuario.id == user_id, models.Usuario.activo == True
    ).first()
    if user is None:
        raise credenciales_invalidas

    # El token solo vale mientras la contraseña no haya cambiado desde que se emitió
    if not hmac.compare_digest(str(payload.get("pv", "")), huella_password(user.password_hash)):
        raise credenciales_invalidas

    csrf_sesion = str(payload.get("csrf", ""))
    # CSRF: solo aplica a la cookie (el navegador la adjunta solo); una cabecera Bearer no se adjunta sola
    if por_cookie and request.method.upper() not in METODOS_SEGUROS:
        enviado = request.headers.get(CSRF_HEADER, "")
        if not csrf_sesion or not hmac.compare_digest(enviado, csrf_sesion):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF ausente o inválido")

    request.state.csrf_token = csrf_sesion
    return user


def rol_de(user: models.Usuario) -> str:
    rol = user.rol
    return str(rol.value if hasattr(rol, "value") else rol).split(".")[-1].lower()


def require_role(*roles: str):
    permitidos = {r.lower() for r in roles}

    def _dep(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if rol_de(current_user) not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para acceder a este recurso",
            )
        return current_user

    return _dep


# Atajos por rol. require_docente = cualquier usuario autenticado (docente o superior).
require_admin = require_role("administrador")
require_coordinador = require_role("coordinador", "administrador")
require_docente = require_role("docente", "coordinador", "administrador")
