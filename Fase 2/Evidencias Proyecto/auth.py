"""
Módulo de autenticación y autorización con JWT para cliente React.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config
import models
import schemas
from database import get_db

# Configuración JWT (la clave viene SOLO del entorno; si falta, la app no arranca)
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Endpoint desde el cual Swagger UI o React obtienen el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Hash de una contraseña inexistente: se usa para que el login tarde lo mismo exista o no el correo
_HASH_FALSO: Optional[str] = None


# --- Hashing de contraseñas ----------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def huella_password(password_hash: str) -> str:
    """
    Huella corta de la contraseña actual. Va dentro del token: si el usuario cambia su contraseña,
    la huella cambia y todos los tokens anteriores dejan de ser válidos.
    """
    return hmac.new(SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:16]


# --- Tokens JWT ----------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    ahora = datetime.now(timezone.utc)
    expire = ahora + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": ahora})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- Autenticación y Dependencias ---------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Usuario]:
    global _HASH_FALSO
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email.strip().lower(), models.Usuario.activo == True)
        .first()
    )
    if not user:
        # Verifica contra un hash falso para no revelar (por el tiempo de respuesta) qué correos existen
        if _HASH_FALSO is None:
            _HASH_FALSO = pwd_context.hash("contrasena-inexistente")
        verify_password(password, _HASH_FALSO)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require_exp": True})
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(models.Usuario).filter(
        models.Usuario.id == user_id_int,
        models.Usuario.activo == True
    ).first()

    if user is None:
        raise credentials_exception

    # El token solo vale mientras la contraseña no haya cambiado desde que se emitió
    if not hmac.compare_digest(str(payload.get("pv", "")), huella_password(user.password_hash)):
        raise credentials_exception
    return user


def require_role(*roles: str):
    allowed: set[str] = {r.lower() for r in roles}

    def _dep(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        # Extrae de forma segura el valor en texto del rol
        if hasattr(current_user.rol, 'value'):
            user_role = str(current_user.rol.value).lower()
        else:
            raw_role = str(current_user.rol)
            user_role = raw_role.split('.')[-1].lower() if '.' in raw_role else raw_role.lower()

        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para acceder a este recurso",
            )
        return current_user

    return _dep


# Atajos por rol
require_admin = require_role("administrador")
require_coordinador = require_role("coordinador", "administrador")
require_docente = require_role("docente", "coordinador", "administrador")