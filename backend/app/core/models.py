"""Base de todos los modelos: id UUIDv7, fechas y autoría se completan solos."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, MetaData, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from uuid6 import uuid7

from app.core import context

# Nombres de constraints predecibles (necesario para migraciones limpias con Alembic)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BaseModel(Base):
    """Toda tabla del sistema hereda de acá.

    - `id`: UUIDv7 (ordenable por fecha; el frontend puede generarlo para la carga offline).
    - `created_*` / `updated_*`: se completan automáticamente con el usuario del request.
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[UUID | None]
    updated_by: Mapped[UUID | None]


@event.listens_for(Session, "before_flush")
def _set_authorship(session: Session, _flush_context: object, _instances: object) -> None:
    user_id = context.current().user_id
    if user_id is None:
        return
    for obj in session.new:
        if isinstance(obj, BaseModel):
            obj.created_by = obj.created_by or user_id
            obj.updated_by = user_id
    for obj in session.dirty:
        if isinstance(obj, BaseModel) and session.is_modified(obj):
            obj.updated_by = user_id
