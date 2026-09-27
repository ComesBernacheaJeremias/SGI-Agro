"""Primitivas de seguridad: hash de contraseñas, tokens JWT y tokens de sesión."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()
_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Hash de una contraseña cualquiera: se verifica contra él cuando el usuario no existe,
# para que el tiempo de respuesta no revele qué usuarios existen.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def create_access_token(user_id: UUID, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    """Devuelve el id de usuario si el token es válido y vigente; si no, None."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        return None


def generate_session_token() -> str:
    """Token opaco de sesión (refresh). Al cliente va el token; a la base, solo su hash."""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
