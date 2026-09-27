"""Lectura del historial: traduce nombres técnicos a etiquetas y referencias (IDs) a nombres."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.models import Base
from app.core.pagination import PageParams, paginate
from app.modules.audit.schemas import AuditChangeOut, AuditEntryOut
from app.modules.identity.models import User


@dataclass(frozen=True)
class AuditFilters:
    table: str | None = None
    record_id: UUID | None = None
    user_id: UUID | None = None
    action: str | None = None
    date_from: date | None = None
    date_to: date | None = None


def _models_by_table() -> dict[str, type[Any]]:
    return {mapper.class_.__tablename__: mapper.class_ for mapper in Base.registry.mappers}


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.models = _models_by_table()

    def search(self, filters: AuditFilters, params: PageParams) -> tuple[list[AuditEntryOut], int]:
        rows, total = paginate(self.session, self._query(filters), params)
        return self._to_out(rows), total

    # --- Consulta ---

    def _query(self, f: AuditFilters) -> Select[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.at.desc(), AuditLog.id.desc())
        if f.table:
            query = query.where(AuditLog.table_name == f.table)
        if f.record_id:
            query = query.where(AuditLog.record_id == f.record_id)
        if f.user_id:
            query = query.where(AuditLog.user_id == f.user_id)
        if f.action:
            query = query.where(AuditLog.action == f.action)
        tz = get_settings().tzinfo
        if f.date_from:
            query = query.where(AuditLog.at >= datetime.combine(f.date_from, time.min, tz))
        if f.date_to:
            next_day = datetime.combine(f.date_to + timedelta(days=1), time.min, tz)
            query = query.where(AuditLog.at < next_day)
        return query

    # --- Presentación ---

    def _to_out(self, rows: list[AuditLog]) -> list[AuditEntryOut]:
        user_names = self._display_names(User, {r.user_id for r in rows if r.user_id})
        references = self._resolve_references(rows)
        return [
            AuditEntryOut(
                id=row.id,
                at=row.at,
                action=row.action,
                table_name=row.table_name,
                table_label=self._table_label(row.table_name),
                record_id=row.record_id,
                user_name=user_names.get(row.user_id) if row.user_id else None,
                changes=[self._change_out(row.table_name, c, references) for c in row.changes],
            )
            for row in rows
        ]

    def _table_label(self, table: str) -> str:
        model = self.models.get(table)
        return getattr(model, "__label__", table) if model else table

    def _field_meta(self, table: str, field: str) -> tuple[str, str | None, dict[str, str]]:
        """(etiqueta, tabla referenciada si es FK, etiquetas de valores si es una opción)."""
        model = self.models.get(table)
        if model is None:
            return field, None, {}
        table_obj = model.__table__
        if field in table_obj.columns:
            column = table_obj.columns[field]
            foreign = next(iter(column.foreign_keys), None)
            choices = {str(k): v for k, v in column.info.get("choices", {}).items()}
            label = column.info.get("label", field)
            return label, foreign.column.table.name if foreign else None, choices
        relationship = model.__mapper__.relationships.get(field)
        if relationship is not None:
            return relationship.info.get("label", field), None, {}
        return field, None, {}

    def _resolve_references(self, rows: list[AuditLog]) -> dict[str, dict[UUID, str]]:
        """Nombres actuales de los registros referenciados por FKs en los cambios."""
        wanted: dict[str, set[UUID]] = {}
        for row in rows:
            for change in row.changes:
                _, target, _ = self._field_meta(row.table_name, change["field"])
                if target:
                    values = (change.get("before"), change.get("after"))
                    wanted.setdefault(target, set()).update(UUID(v) for v in values if v)
        resolved = {}
        for table, table_ids in wanted.items():
            model = self.models.get(table)
            if model is not None:
                resolved[table] = self._display_names(model, table_ids)
        return resolved

    def _display_names(self, model: type[Any], ids: set[UUID]) -> dict[UUID, str]:
        display = getattr(model, "__display__", None)
        if not ids or display is None:
            return {}
        rows = self.session.execute(
            select(model.id, getattr(model, display)).where(model.id.in_(ids))
        )
        return {row[0]: str(row[1]) for row in rows}

    def _change_out(
        self, table: str, change: dict[str, Any], references: dict[str, dict[UUID, str]]
    ) -> AuditChangeOut:
        label, target, choices = self._field_meta(table, change["field"])
        before, after = change.get("before"), change.get("after")
        if choices:
            before, after = choices.get(str(before), before), choices.get(str(after), after)
        if target:
            names = references.get(target, {})
            before = names.get(UUID(before), before) if before else before
            after = names.get(UUID(after), after) if after else after
        return AuditChangeOut(field=change["field"], label=label, before=before, after=after)
