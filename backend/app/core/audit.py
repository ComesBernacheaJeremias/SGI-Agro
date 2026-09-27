"""Historial automático de cambios.

Cada alta, edición o baja de un modelo `BaseModel` genera una fila en `audit_log` con los
campos que cambiaron (antes → después), el usuario y el request. Ningún módulo tiene que
hacer nada: se registra al hacer flush, en la misma transacción.

Por modelo / columna:
  - `__label__ = "Producto"`                → nombre de la entidad para mostrar
  - `__display__ = "name"`                  → campo que la representa (para mostrar referencias)
  - `__audited__ = False`                   → la tabla no se registra
  - `mapped_column(..., info={"label": "Precio"})` → nombre del campo para mostrar
  - `mapped_column(..., info={"audit": False})`    → el campo no se registra
  - `relationship(..., info={"label": "Permisos", "audit_key": "permission"})`
        → colección registrada como lista de valores de `audit_key` (antes → después)
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, event, func, insert, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from uuid6 import uuid7

from app.core import context
from app.core.models import Base, BaseModel

# Columnas comunes que no aportan al historial
_ALWAYS_EXCLUDED = {"id", "created_at", "updated_at", "created_by", "updated_by"}


class AuditAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DEACTIVATE = "deactivate"
    ACTIVATE = "activate"
    CANCEL = "cancel"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    table_name: Mapped[str] = mapped_column(String(63), index=True)
    record_id: Mapped[UUID] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(20))
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    user_id: Mapped[UUID | None] = mapped_column(index=True)
    request_id: Mapped[str | None] = mapped_column(String(64))


def _json_value(value: Any) -> Any:
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _audited_columns(obj: BaseModel) -> list[Any]:
    return [
        attr
        for attr in inspect(obj).mapper.column_attrs
        if attr.key not in _ALWAYS_EXCLUDED
        and all(col.info.get("audit", True) for col in attr.columns)
    ]


def _changes(obj: BaseModel, action: AuditAction) -> list[dict[str, Any]]:
    state = inspect(obj)
    changes = []
    for attr in _audited_columns(obj):
        if action == AuditAction.CREATE:
            before, after = None, getattr(obj, attr.key)
            if after is None:
                continue
        elif action == AuditAction.DELETE:
            before, after = getattr(obj, attr.key), None
        else:
            history = state.attrs[attr.key].history
            if not history.has_changes():
                continue
            before = history.deleted[0] if history.deleted else None
            after = history.added[0] if history.added else None
            if before == after:
                continue
        changes.append(
            {"field": attr.key, "before": _json_value(before), "after": _json_value(after)}
        )
    changes.extend(_collection_changes(obj, action))
    return changes


def _collection_changes(obj: BaseModel, action: AuditAction) -> list[dict[str, Any]]:
    """Colecciones marcadas con `audit_key` (ej. permisos de un rol)."""
    state = inspect(obj)
    changes = []
    for rel in state.mapper.relationships:
        key = rel.info.get("audit_key")
        if key is None:
            continue
        history = state.attrs[rel.key].history
        if action == AuditAction.UPDATE and not history.has_changes():
            continue
        unchanged = [getattr(item, key) for item in history.unchanged or ()]
        before = sorted(unchanged + [getattr(item, key) for item in history.deleted or ()])
        after = sorted(unchanged + [getattr(item, key) for item in history.added or ()])
        if action == AuditAction.CREATE:
            before = []
        if before != after:
            changes.append({"field": rel.key, "before": before, "after": after})
    return changes


def _update_action(changes: list[dict[str, Any]]) -> AuditAction:
    by_field = {c["field"]: c for c in changes}
    if "status" in by_field and by_field["status"]["after"] == "cancelled":
        return AuditAction.CANCEL
    if "is_active" in by_field:
        return AuditAction.ACTIVATE if by_field["is_active"]["after"] else AuditAction.DEACTIVATE
    return AuditAction.UPDATE


def _is_audited(obj: object) -> bool:
    return isinstance(obj, BaseModel) and getattr(type(obj), "__audited__", True)


@event.listens_for(Session, "after_flush")
def _write_audit_log(session: Session, _flush_context: object) -> None:
    request = context.current()
    entries: list[dict[str, Any]] = []
    groups = (
        (session.new, AuditAction.CREATE),
        (session.dirty, AuditAction.UPDATE),
        (session.deleted, AuditAction.DELETE),
    )
    for objects, action in groups:
        for obj in objects:
            if not _is_audited(obj):
                continue
            changes = _changes(obj, action)
            if not changes:
                continue
            final_action = _update_action(changes) if action == AuditAction.UPDATE else action
            entries.append(
                {
                    "id": uuid7(),
                    "table_name": obj.__tablename__,
                    "record_id": obj.id,
                    "action": final_action.value,
                    "changes": changes,
                    "user_id": request.user_id,
                    "request_id": request.request_id,
                }
            )
    if entries:
        # Insert directo por la conexión: no modifica la sesión en medio del flush
        session.connection().execute(insert(AuditLog), entries)
