"""Gestión de roles y sus permisos."""

import re
import unicodedata
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.permissions import all_permissions
from app.modules.identity.authorization import effective_permissions, has_computed_permissions
from app.modules.identity.models import Role, RolePermission
from app.modules.identity.repository import RoleRepository, UserRepository
from app.modules.identity.schemas import RoleCreate, RoleOut, RoleUpdate


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")[:30] or "rol"


class RoleService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.roles = RoleRepository(session)
        self.users = UserRepository(session)

    def list_roles(self) -> list[RoleOut]:
        return [self.to_out(role) for role in self.roles.list_all()]

    def get(self, id_: UUID) -> Role:
        role = self.roles.get(id_)
        if role is None:
            raise NotFoundError("No se encontró el rol.")
        return role

    def create(self, data: RoleCreate) -> Role:
        code = _slug(data.name)
        if self.roles.get_by_code(code) or self.roles.exists_with("name", data.name, None):
            raise BusinessRuleError(f"Ya existe un rol llamado '{data.name}'.", code="DUPLICATE")
        role = Role(code=code, name=data.name.strip(), description=data.description.strip())
        self._set_permissions(role, data.permissions)
        return self.roles.add(role)

    def update(self, id_: UUID, data: RoleUpdate) -> Role:
        role = self.get(id_)
        if has_computed_permissions(role):
            raise BusinessRuleError(
                f"El rol '{role.name}' es fijo del sistema y no se puede modificar.",
                code="SYSTEM_ROLE",
            )
        if data.name is not None and not role.is_system:
            if self.roles.exists_with("name", data.name, role.id):
                raise BusinessRuleError(
                    f"Ya existe un rol llamado '{data.name}'.", code="DUPLICATE"
                )
            role.name = data.name.strip()
        if data.description is not None:
            role.description = data.description.strip()
        if data.permissions is not None:
            self._set_permissions(role, data.permissions)
        self.session.flush()
        return role

    def delete(self, id_: UUID) -> None:
        role = self.get(id_)
        if role.is_system:
            raise BusinessRuleError(
                "Los roles del sistema no se pueden eliminar.", code="SYSTEM_ROLE"
            )
        if self.users.count_by_role(role.id):
            raise BusinessRuleError(
                "No se puede eliminar un rol que tiene usuarios asignados.", code="ROLE_IN_USE"
            )
        self.session.delete(role)
        self.session.flush()

    def to_out(self, role: Role) -> RoleOut:
        return RoleOut(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions_editable=not has_computed_permissions(role),
            permissions=sorted(effective_permissions(role)),
            user_count=self.users.count_by_role(role.id),
        )

    def _set_permissions(self, role: Role, codes: list[str]) -> None:
        assignable = {p.code for p in all_permissions() if not p.support_only}
        invalid = sorted(set(codes) - assignable)
        if invalid:
            raise BusinessRuleError(
                f"Permisos inválidos o no asignables: {', '.join(invalid)}.",
                code="INVALID_PERMISSION",
            )
        wanted = set(codes)
        current = {rp.permission for rp in role.permissions}
        role.permissions[:] = [rp for rp in role.permissions if rp.permission in wanted]
        role.permissions.extend(RolePermission(permission=c) for c in sorted(wanted - current))
