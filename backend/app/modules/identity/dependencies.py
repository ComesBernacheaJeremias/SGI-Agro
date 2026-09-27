"""Dependencia de autenticación: `CurrentUser` en cualquier endpoint exige sesión válida."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import context
from app.core.db import DbSession
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    user_id = decode_access_token(credentials.credentials) if credentials else None
    user = UserRepository(db).get(user_id) if user_id else None
    if user is None or not user.is_active:
        raise UnauthorizedError("La sesión venció o no es válida. Volvé a ingresar.")
    context.current().user_id = user.id  # autoría (created_by/updated_by), historial y logs
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
