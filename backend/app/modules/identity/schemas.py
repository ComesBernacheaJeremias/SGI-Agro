from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.schemas import Schema

# --- Auth ---


class LoginRequest(Schema):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(Schema):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


# --- Roles ---


class RoleRef(Schema):
    id: UUID
    code: str
    name: str


class RoleOut(RoleRef):
    description: str
    is_system: bool
    permissions_editable: bool
    permissions: list[str]  # efectivos (en roles fijos, calculados)
    user_count: int


class RoleCreate(Schema):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=255)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None


class PermissionOut(Schema):
    code: str
    label: str
    support_only: bool


class PermissionGroupOut(Schema):
    group: str
    permissions: list[PermissionOut]


# --- Usuarios ---


class UserOut(Schema):
    id: UUID
    username: str
    full_name: str
    role: RoleRef
    is_active: bool
    last_login_at: datetime | None


class UserCreate(Schema):
    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=120)
    role_id: UUID
    password: str = Field(min_length=1, max_length=200)


class UserUpdate(Schema):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role_id: UUID | None = None


class ResetPasswordRequest(Schema):
    password: str = Field(min_length=1, max_length=200)


class MeOut(UserOut):
    """Usuario actual + sus permisos efectivos (el frontend oculta lo que no puede usar)."""

    permissions: list[str]


class TokenResponse(Schema):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo de token estándar, no es una contraseña)
    user: MeOut
