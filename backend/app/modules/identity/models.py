from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base, BaseModel

# Columnas técnicas que no aportan al historial de cambios
NOT_AUDITED = {"audit": False}


class Role(BaseModel):
    __tablename__ = "roles"
    __label__ = "Rol"
    __display__ = "name"

    code: Mapped[str] = mapped_column(String(30), unique=True, info={"label": "Código"})
    name: Mapped[str] = mapped_column(String(60), info={"label": "Nombre"})
    description: Mapped[str] = mapped_column(String(255), default="", info={"label": "Descripción"})
    # Rol del sistema: no se puede eliminar ni cambiar su código
    is_system: Mapped[bool] = mapped_column(default=False, info=NOT_AUDITED)

    permissions: Mapped[list["RolePermission"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Permisos", "audit_key": "permission"},
    )


class RolePermission(Base):
    """Permiso asignado a un rol editable (los roles fijos se calculan en código)."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(60), primary_key=True)


class User(BaseModel):
    __tablename__ = "users"
    __label__ = "Usuario"
    __display__ = "full_name"

    username: Mapped[str] = mapped_column(String(50), info={"label": "Usuario"})
    full_name: Mapped[str] = mapped_column(String(120), info={"label": "Nombre completo"})
    password_hash: Mapped[str] = mapped_column(String(255), info=NOT_AUDITED)
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), info={"label": "Rol"})

    failed_login_attempts: Mapped[int] = mapped_column(default=0, info=NOT_AUDITED)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), info=NOT_AUDITED)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), info=NOT_AUDITED
    )

    role: Mapped[Role] = relationship(lazy="joined")


# Usuario único sin distinguir mayúsculas ("Juan" y "juan" son el mismo usuario)
Index("uq_users_username_lower", func.lower(User.username), unique=True)


class SessionToken(BaseModel):
    """Sesión de 30 días (refresh token). Se rota en cada uso; se guarda solo el hash."""

    __tablename__ = "session_tokens"
    __audited__ = False

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
