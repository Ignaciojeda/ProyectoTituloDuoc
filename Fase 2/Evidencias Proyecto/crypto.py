"""
Cifrado de datos sensibles a nivel de aplicación.

- CampoCifrado: tipo de columna de SQLAlchemy. Guarda el valor cifrado (Fernet = AES-128-CBC + HMAC)
  y lo devuelve descifrado al leerlo. El resto del código no cambia.
- hash_ciego(): huella HMAC-SHA256 del valor, para poder buscar o garantizar que sea único
  sin guardar el dato en claro (el texto cifrado cambia cada vez, así que no sirve para eso).
"""
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import String, TypeDecorator

import config

if not config.DATA_ENCRYPTION_KEY or not config.DATA_HASH_KEY:
    raise RuntimeError("Faltan DATA_ENCRYPTION_KEY y DATA_HASH_KEY en el .env (necesarias para el cifrado del RUT).")

_fernet = Fernet(config.DATA_ENCRYPTION_KEY.encode())


def cifrar(texto: str) -> str:
    return _fernet.encrypt(texto.encode("utf-8")).decode("ascii")


def descifrar(token: str) -> str:
    return _fernet.decrypt(token.encode("ascii")).decode("utf-8")


def normalizar_rut(rut: str) -> str:
    return "".join(c for c in str(rut) if c.isalnum()).upper()


def hash_ciego(valor: str) -> str:
    return hmac.new(
        config.DATA_HASH_KEY.encode(), normalizar_rut(valor).encode("utf-8"), hashlib.sha256
    ).hexdigest()


class CampoCifrado(TypeDecorator):
    """Columna de texto que se guarda cifrada."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return cifrar(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return descifrar(value)
        except InvalidToken:
            # Valor antiguo aún sin cifrar (durante la migración): se devuelve tal cual.
            return value