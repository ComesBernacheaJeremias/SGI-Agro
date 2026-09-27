"""Roles y verificación de permisos.

Roles fijos (permisos calculados en código, se actualizan solos al agregar módulos):
  - support:   todo.
  - owner:     todo excepto lo exclusivo de soporte.
  - read_only: todos los permisos de lectura.
Roles editables (permisos guardados en `role_permissions`): staff y los que se creen.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends

from app.core.errors import ForbiddenError
from app.core.permissions import Permission, all_permissions
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import Role, User

SUPPORT = "support"
OWNER = "owner"
STAFF = "staff"
READ_ONLY = "read_only"

COMPUTED_ROLES: dict[str, Callable[[Permission], bool]] = {
    SUPPORT: lambda _: True,
    OWNER: lambda p: not p.support_only,
    READ_ONLY: lambda p: p.is_read,
}


def has_computed_permissions(role: Role) -> bool:
    return role.code in COMPUTED_ROLES


def effective_permissions(role: Role) -> set[str]:
    rule = COMPUTED_ROLES.get(role.code)
    if rule is not None:
        return {p.code for p in all_permissions() if rule(p)}
    defined = {p.code for p in all_permissions()}
    return {rp.permission for rp in role.permissions if rp.permission in defined}


def require(permission: Permission) -> Any:
    """Dependencia que exige un permiso: `user: Annotated[User, require(MASTERDATA_CREATE)]`."""

    def check(user: CurrentUser) -> User:
        if permission.code not in effective_permissions(user.role):
            raise ForbiddenError(f"No tenés permiso para: {permission.group} → {permission.label}.")
        return user

    return Depends(check)
