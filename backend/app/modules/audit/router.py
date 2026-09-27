from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.db import DbSession
from app.core.pagination import Page, Pagination
from app.modules.audit.schemas import AuditEntryOut
from app.modules.audit.service import AuditFilters, AuditService
from app.modules.identity.authorization import require
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User
from app.modules.identity.permissions import AUDIT_READ

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/records/{table}/{record_id}")
def record_history(
    table: str, record_id: UUID, db: DbSession, _: CurrentUser, page: Pagination
) -> Page[AuditEntryOut]:
    """Historial de un registro (botón "Historial" de cada pantalla)."""
    items, total = AuditService(db).search(AuditFilters(table=table, record_id=record_id), page)
    return Page(items=items, total=total, page=page.page, page_size=page.page_size)


@router.get("")
def general_history(
    db: DbSession,
    _: Annotated[User, require(AUDIT_READ)],
    page: Pagination,
    table: str | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[AuditEntryOut]:
    """Historial general con filtros (dueño y soporte)."""
    filters = AuditFilters(
        table=table, user_id=user_id, action=action, date_from=date_from, date_to=date_to
    )
    items, total = AuditService(db).search(filters, page)
    return Page(items=items, total=total, page=page.page, page_size=page.page_size)
