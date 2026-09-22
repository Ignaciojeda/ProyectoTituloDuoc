"""
Script para crear usuarios iniciales de prueba (uno por rol).
Útil para desarrollo y para la entrega del proyecto.

Uso:
    python seed_users.py

Crea (si no existen):
    admin@duoc.cl      / Admin123!    -> administrador
    coord@duoc.cl      / Coord123!    -> coordinador
    docente@duoc.cl    / Docente123!  -> docente
"""

from database import SessionLocal, Base, engine
import models
from auth import hash_password


USUARIOS_INICIALES = [
    {
        "nombre": "Administrador del Sistema",
        "email": "admin@duoc.cl",
        "password": "Admin123!",
        "rol": models.RolUsuario.administrador,
    },
    {
        "nombre": "Coordinador Académico",
        "email": "coord@duoc.cl",
        "password": "Coord123!",
        "rol": models.RolUsuario.coordinador,
    },
    {
        "nombre": "Docente de Prueba",
        "email": "docente@duoc.cl",
        "password": "Docente123!",
        "rol": models.RolUsuario.docente,
    },
]


def main() -> None:
    # Asegura que las tablas existan
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for u in USUARIOS_INICIALES:
            existente = (
                db.query(models.Usuario)
                .filter(models.Usuario.email == u["email"])
                .first()
            )
            if existente:
                print(f"  ✓ Ya existe: {u['email']} ({existente.rol.value})")
                continue

            nuevo = models.Usuario(
                nombre=u["nombre"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                rol=u["rol"],
                activo=True,
            )
            db.add(nuevo)
            db.commit()
            db.refresh(nuevo)
            print(f"  + Creado: {nuevo.email} → {nuevo.rol.value}")
    finally:
        db.close()

    print("\nCredenciales de prueba:")
    print("-" * 50)
    for u in USUARIOS_INICIALES:
        print(f"  {u['rol'].value:14s}  {u['email']:25s}  {u['password']}")
    print("-" * 50)


if __name__ == "__main__":
    main()
