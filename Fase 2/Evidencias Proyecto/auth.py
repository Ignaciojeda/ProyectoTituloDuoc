"""
Módulo de autenticación y autorización con JWT para cliente React.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY") or "super-secret-key-duoc-2026-sinopticos"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Endpoint desde el cual Swagger UI o React obtienen el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# --- Hashing de contraseñas ----------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


# --- Tokens JWT ----------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- Autenticación y Dependencias ---------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Usuario]:
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email.strip().lower(), models.Usuario.activo == True)
        .first()
    )
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # CONVERTIR user_id A INT
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise credentials_exception

    # Consulta con el valor en entero
    user = db.query(models.Usuario).filter(
        models.Usuario.id == user_id_int, 
        models.Usuario.activo == True
    ).first()

    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: str):
    allowed: set[str] = {r.lower() for r in roles}

    def _dep(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        user_role = current_user.rol.value.lower() if hasattr(current_user.rol, 'value') else str(current_user.rol).lower()
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