"""Piezas genéricas para entidades con alta/edición/activación (maestros, usuarios…).

- `CrudRepository`: listado con búsqueda (sin distinguir tildes ni mayúsculas), filtro de
  activos, orden y paginación.
- `CrudService`: obtener / crear / editar / activar / desactivar, con validación de únicos.

Cada módulo hereda y solo declara lo propio (modelo, campos de búsqueda, únicos, reglas).
"""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, Query
from pydantic import BaseModel as PydanticModel
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.models import BaseModel
from app.core.pagination import PageParams, paginate
from app.core.repository import BaseRepository


class ListParams(PydanticModel):
    q: str | None = None
    active: bool | None = True  # None = todos
    sort: str | None = None


def _list_params(
    q: Annotated[str | None, Query(description="Texto a buscar")] = None,
    active: Annotated[Literal["true", "false", "all"], Query()] = "true",
    sort: Annotated[str | None, Query(description="Campo; con '-' adelante: descendente")] = None,
) -> ListParams:
    return ListParams(q=q, active=None if active == "all" else active == "true", sort=sort)


ListQuery = Annotated[ListParams, Depends(_list_params)]


def _normalized(column: Any) -> Any:
    """Texto sin tildes y en minúsculas (requiere la extensión `unaccent`)."""
    return func.lower(func.unaccent(column))


class CrudRepository[M: BaseModel](BaseRepository[M]):
    search_fields: tuple[str, ...] = ()
    default_sort: str = "name"

    def search(
        self, params: ListParams, page: PageParams, filters: dict[str, Any] | None = None
    ) -> tuple[list[M], int]:
        return paginate(self.session, self.list_query(params, filters or {}), page)

    def list_query(self, params: ListParams, filters: dict[str, Any]) -> Select[M]:
        """Consulta del listado: activos, búsqueda, filtros propios y orden."""
        model = self.model
        query = self.apply_filters(select(model), filters)
        if params.active is not None and hasattr(model, "is_active"):
            query = query.where(model.is_active.is_(params.active))  # type: ignore[attr-defined]
        if params.q and self.search_fields:
            pattern = f"%{params.q.strip()}%"
            query = query.where(
                or_(
                    *(
                        _normalized(getattr(model, f)).like(_normalized(pattern))
                        for f in self.search_fields
                    )
                )
            )
        return query.order_by(*self._order_by(params.sort))

    def apply_filters(self, query: Select[M], filters: dict[str, Any]) -> Select[M]:
        """Filtros propios del listado. Por defecto: igualdad campo = valor (ignora None)."""
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        return query

    def _order_by(self, sort: str | None) -> list[Any]:
        field = (sort or self.default_sort).lstrip("-")
        column = getattr(self.model, field, None)
        if column is None or field not in self.model.__table__.columns:
            column = getattr(self.model, self.default_sort)
        ordered = column.desc() if (sort or "").startswith("-") else column.asc()
        return [ordered, self.model.id.asc()]  # desempate estable para la paginación

    def exists_with(self, field: str, value: Any, exclude_id: UUID | None) -> bool:
        column = getattr(self.model, field)
        condition = (
            _normalized(column) == _normalized(value) if isinstance(value, str) else column == value
        )
        query = select(self.model.id).where(condition)
        if exclude_id is not None:
            query = query.where(self.model.id != exclude_id)
        return self.session.scalar(query.limit(1)) is not None


class CrudService[M: BaseModel, C: PydanticModel, U: PydanticModel]:
    repository_class: type[CrudRepository[M]]
    # campo → mensaje (con {value}); se valida sin distinguir tildes ni mayúsculas
    unique_fields: dict[str, str] = {}  # noqa: RUF012 (se redefine por subclase, no se muta)
    not_found_message = "No se encontró el registro."

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = self.repository_class(session)

    def get(self, id_: UUID) -> M:
        obj = self.repo.get(id_)
        if obj is None:
            raise NotFoundError(self.not_found_message)
        return obj

    def search(
        self, params: ListParams, page: PageParams, filters: dict[str, Any] | None = None
    ) -> tuple[list[M], int]:
        return self.repo.search(params, page, filters)

    def create(self, data: C) -> M:
        obj = self.repo.model(**self.values_for_create(data))
        self.validate(obj)
        return self.repo.add(obj)

    def update(self, id_: UUID, data: U) -> M:
        obj = self.get(id_)
        for field, value in self.values_for_update(data).items():
            setattr(obj, field, value)
        self.validate(obj)
        self.session.flush()
        return obj

    def set_active(self, id_: UUID, active: bool) -> M:
        obj = self.get(id_)
        obj.is_active = active  # type: ignore[attr-defined]
        self.session.flush()
        return obj

    # --- Puntos de extensión ---

    def values_for_create(self, data: C) -> dict[str, Any]:
        return data.model_dump()

    def values_for_update(self, data: U) -> dict[str, Any]:
        """Solo los campos enviados (PATCH)."""
        return data.model_dump(exclude_unset=True)

    def validate(self, obj: M) -> None:
        """Reglas antes de guardar. Por defecto: campos únicos. Extender con `super().validate`."""
        for field, message in self.unique_fields.items():
            value = getattr(obj, field)
            if value not in (None, "") and self.repo.exists_with(field, value, obj.id):
                raise BusinessRuleError(message.format(value=value), code="DUPLICATE")
