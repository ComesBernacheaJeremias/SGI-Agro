"""Gestión de usuarios: alta, edición, activación y contraseñas."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.crud import CrudService
from app.core.errors import BusinessRuleError, ForbiddenError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.modules.identity.authorization import SUPPORT
from app.modules.identity.models import Role, User
from app.modules.identity.repository import SessionTokenRepository, UserRepository
from app.modules.identity.schemas import UserCreate, UserUpdate

MIN_PASSWORD_LENGTH = 10


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BusinessRuleError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
            code="WEAK_PASSWORD",
        )


class UserService(CrudService[User, UserCreate, UserUpdate]):
    repository_class = UserRepository
    unique_fields = {"username": "Ya existe el usuario '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el usuario."

    def __init__(self, session: Session, actor: User | None = None) -> None:
        """`actor`: quien hace la operación (None = sistema, ej. el comando create-user)."""
        super().__init__(session)
        self.actor = actor
        self.tokens = SessionTokenRepository(session)

    # --- Alta / edición ---

    def values_for_create(self, data: UserCreate) -> dict[str, Any]:
        validate_password(data.password)
        values = data.model_dump(exclude={"password"})
        values["username"] = values["username"].strip()
        values["full_name"] = values["full_name"].strip()
        values["password_hash"] = hash_password(data.password)
        return values

    def update(self, id_: UUID, data: UserUpdate) -> User:
        self._ensure_can_manage(self.get(id_))
        user = super().update(id_, data)
        self.session.expire(user, ["role"])  # recargar el rol si cambió role_id
        return user

    def validate(self, obj: User) -> None:
        super().validate(obj)
        role = self.session.get(Role, obj.role_id)
        if role is None:
            raise BusinessRuleError("El rol elegido no existe.", code="ROLE_NOT_FOUND")
        if role.code == SUPPORT and not self._actor_is_support():
            raise ForbiddenError("Solo el rol Soporte puede asignar el rol Soporte.")

    # --- Activación / contraseñas ---

    def set_active(self, id_: UUID, active: bool) -> User:
        user = self.get(id_)
        self._ensure_can_manage(user)
        if not active and self.actor is not None and user.id == self.actor.id:
            raise BusinessRuleError(
                "No podés desactivar tu propio usuario.", code="SELF_DEACTIVATE"
            )
        user = super().set_active(id_, active)
        if not active:
            self.tokens.revoke_all_for_user(user.id, datetime.now(UTC))
        return user

    def reset_password(self, id_: UUID, password: str) -> None:
        """Un administrador le asigna una contraseña nueva; se cierran sus sesiones."""
        user = self.get(id_)
        self._ensure_can_manage(user)
        validate_password(password)
        user.password_hash = hash_password(password)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.tokens.revoke_all_for_user(user.id, datetime.now(UTC))

    def change_own_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(user.password_hash, current):
            raise UnauthorizedError("La contraseña actual no es correcta.", code="WRONG_PASSWORD")
        validate_password(new)
        user.password_hash = hash_password(new)

    # --- Reglas de quién puede modificar a quién ---

    def _actor_is_support(self) -> bool:
        return self.actor is None or self.actor.role.code == SUPPORT

    def _ensure_can_manage(self, target: User) -> None:
        if target.role.code == SUPPORT and not self._actor_is_support():
            raise ForbiddenError("Solo el rol Soporte puede modificar usuarios de Soporte.")
