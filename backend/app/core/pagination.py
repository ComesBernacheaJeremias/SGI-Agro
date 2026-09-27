"""Paginación común de listados.

?page=1&page_size=50 → { items, total, page, page_size }
"""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class PageParams(BaseModel):
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def _page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(_page_params)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


def paginate[M](session: Session, query: Select[M], params: PageParams) -> tuple[list[M], int]:
    """Ejecuta `query` paginada y devuelve (filas, total)."""
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(session.scalars(query.offset(params.offset).limit(params.page_size)))
    return rows, total
