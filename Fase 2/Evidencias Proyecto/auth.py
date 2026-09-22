"""
Módulo de autenticación y autorización.

Estrategia:
- Contraseñas: se almacenan hasheadas con bcrypt (vía passlib).
- Sesión: cookie firmada con SessionMiddleware (itsdangerous).
- Autorización: dependencias de FastAPI que validan rol(es) permitido(s).
"""
from typing import Optional
from typing import Optional
from sqlalchemy.orm import Session
from typing import Iterable

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db


# --- Hashing de contraseñas ----------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Devuelve el hash bcrypt de la contraseña en texto plano."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compara una contraseña en texto plano con un hash almacenado."""
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        # Hash malformado o esquema desconocido
        return False


# --- Autenticación -------------------------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Usuario]:
    """
    Busca un usuario activo por email y verifica su contraseña.
    Devuelve el Usuario si las credenciales son válidas, o None en caso contrario.
    """
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email, models.Usuario.activo == True)
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.Usuario | None:
    """Lee el user_id desde la sesión y devuelve el Usuario, o None si no hay sesión."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return (
        db.query(models.Usuario)
        .filter(models.Usuario.id == user_id, models.Usuario.activo == True)
        .first()
    )


# --- Guards / dependencias por rol --------------------------------------------

def _wants_html(request: Request) -> bool:
    """Detecta si el cliente espera HTML (para redirigir a /login en vez de 401 JSON)."""
    accept = request.headers.get("accept", "")
    return "text/html" in accept


def require_login(
    request: Request, db: Session = Depends(get_db)
) -> models.Usuario:
    """Protege una ruta: exige sesión activa. Redirige a /login si es HTML."""
    user = get_current_user(request, db)
    if not user:
        if _wants_html(request):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                detail="Debe iniciar sesión",
                headers={"Location": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )
    return user


def require_role(*roles: str):
    """
    Fábrica de dependencias. Uso:
        @app.get("/admin", dependencies=[Depends(require_role("administrador"))])

    o como dependencia directa en endpoints que necesitan el usuario:
        def endpoint(user: models.Usuario = Depends(require_role("administrador"))):
            ...
    """
    allowed: set[str] = {r.lower() for r in roles}

    def _dep(request: Request, db: Session = Depends(get_db)) -> models.Usuario:
        user = get_current_user(request, db)
        if not user:
            if _wants_html(request):
                raise HTTPException(
                    status_code=status.HTTP_303_SEE_OTHER,
                    detail="Debe iniciar sesión",
                    headers={"Location": "/login"},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autenticado",
            )
        if user.rol.value.lower() not in allowed:
            if _wants_html(request):
                raise HTTPException(
                    status_code=status.HTTP_303_SEE_OTHER,
                    detail="No tiene permisos para esta sección",
                    headers={"Location": "/dashboard"},
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para acceder a este recurso",
            )
        return user

    return _dep


# Atajos por rol (más legibles en las rutas)
require_admin = require_role("administrador")
require_coordinador = require_role("coordinador", "administrador")  # admin también entra
require_docente = require_role("docente", "coordinador", "administrador")  # todos pueden ver
