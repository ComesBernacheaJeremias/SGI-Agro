from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, status

from app.core.db import DbSession
from app.core.permissions import all_permissions
from app.modules.identity.authorization import require
from app.modules.identity.models import User
from app.modules.identity.permissions import USERS_MANAGE, USERS_READ
from app.modules.identity.role_service import RoleService
from app.modules.identity.schemas import (
    PermissionGroupOut,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
permissions_router = APIRouter(prefix="/api/v1/permissions", tags=["roles"])

Reader = Annotated[User, require(USERS_READ)]
Manager = Annotated[User, require(USERS_MANAGE)]


@router.get("")
def list_roles(db: DbSession, _: Reader) -> list[RoleOut]:
    return RoleService(db).list_roles()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_role(body: RoleCreate, db: DbSession, _: Manager) -> RoleOut:
    service = RoleService(db)
    return service.to_out(service.create(body))


@router.patch("/{id_}")
def update_role(id_: UUID, body: RoleUpdate, db: DbSession, _: Manager) -> RoleOut:
    service = RoleService(db)
    return service.to_out(service.update(id_, body))


@router.delete("/{id_}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(id_: UUID, db: DbSession, _: Manager) -> None:
    RoleService(db).delete(id_)


@permissions_router.get("")
def list_permissions(_: Reader) -> list[PermissionGroupOut]:
    """Todos los permisos del sistema, agrupados por módulo (para armar roles)."""
    groups: dict[str, list[PermissionOut]] = {}
    for p in all_permissions():
        groups.setdefault(p.group, []).append(
            PermissionOut(code=p.code, label=p.label, support_only=p.support_only)
        )
    return [PermissionGroupOut(group=g, permissions=perms) for g, perms in groups.items()]
