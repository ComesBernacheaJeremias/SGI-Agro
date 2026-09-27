"""Fábrica de endpoints estándar para una entidad con `CrudService`:

    GET    {prefix}                 listado (q, active, sort, page, page_size)
    GET    {prefix}/{id}            detalle
    POST   {prefix}                 alta
    PATCH  {prefix}/{id}            edición
    POST   {prefix}/{id}/deactivate desactivar
    POST   {prefix}/{id}/activate   reactivar

Uso: `router = crud_router(prefix=..., service=ProductService, out=ProductOut, ...)`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel as PydanticModel

from app.core.crud import CrudService, ListQuery
from app.core.db import DbSession
from app.core.pagination import Page, Pagination
from app.core.permissions import Permission
from app.modules.identity.authorization import require
from app.modules.identity.models import User


@dataclass(frozen=True)
class CrudPermissions:
    read: Permission
    write: Permission  # alta y edición
    deactivate: Permission


def _no_filters() -> dict[str, Any]:
    return {}


def crud_router(
    *,
    prefix: str,
    tag: str,
    service: type[CrudService[Any, Any, Any]],
    out: type[PydanticModel],
    create: type[PydanticModel],
    update: type[PydanticModel],
    permissions: CrudPermissions,
    filters: Callable[..., dict[str, Any]] | None = None,
) -> APIRouter:
    """`filters`: dependencia opcional que lee query params y devuelve {campo: valor}."""
    router = APIRouter(prefix=prefix, tags=[tag])
    read, write, deactivate = permissions.read, permissions.write, permissions.deactivate
    # Los schemas llegan como parámetros: FastAPI los usa para validar y documentar;
    # mypy no admite variables como tipos, de ahí los `type: ignore[valid-type]`.

    @router.get("")
    def list_items(
        db: DbSession,
        _: Annotated[User, require(read)],
        params: ListQuery,
        page: Pagination,
        extra: Annotated[dict[str, Any], Depends(filters or _no_filters)],
    ) -> Page[out]:  # type: ignore[valid-type]
        items, total = service(db).search(params, page, extra)
        return Page(
            items=[out.model_validate(i) for i in items],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    @router.get("/{id_}")
    def get_item(id_: UUID, db: DbSession, _: Annotated[User, require(read)]) -> out:  # type: ignore[valid-type]
        return out.model_validate(service(db).get(id_))

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_item(
        body: create,  # type: ignore[valid-type]
        db: DbSession,
        _: Annotated[User, require(write)],
    ) -> out:  # type: ignore[valid-type]
        return out.model_validate(service(db).create(body))

    @router.patch("/{id_}")
    def update_item(
        id_: UUID,
        body: update,  # type: ignore[valid-type]
        db: DbSession,
        _: Annotated[User, require(write)],
    ) -> out:  # type: ignore[valid-type]
        return out.model_validate(service(db).update(id_, body))

    @router.post("/{id_}/deactivate")
    def deactivate_item(id_: UUID, db: DbSession, _: Annotated[User, require(deactivate)]) -> out:  # type: ignore[valid-type]
        return out.model_validate(service(db).set_active(id_, active=False))

    @router.post("/{id_}/activate")
    def activate_item(id_: UUID, db: DbSession, _: Annotated[User, require(deactivate)]) -> out:  # type: ignore[valid-type]
        return out.model_validate(service(db).set_active(id_, active=True))

    return router
