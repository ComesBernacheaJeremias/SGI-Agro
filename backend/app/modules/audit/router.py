from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.db import DbSession
from app.core.pagination import Page, Pagination, paginate
from app.core.schemas import Schema
from app.modules.audit.schemas import AuditEntryOut
from app.modules.audit.service import AuditFilters, AuditService
from app.modules.identity.authorization import require
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import LOGIN_RESULT_LABELS, LoginEvent, LoginResult, User
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


class LoginEventOut(Schema):
    id: UUID
    created_at: datetime
    username: str
    ip: str
    user_agent: str
    result: LoginResult
    result_label: str


@router.get("/logins")
def login_events(
    db: DbSession,
    _: Annotated[User, require(AUDIT_READ)],
    page: Pagination,
    q: str | None = None,
    result: LoginResult | None = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[LoginEventOut]:
    """Intentos de ingreso (correctos y fallidos), los más nuevos primero."""
    query = select(LoginEvent).order_by(LoginEvent.created_at.desc())
    if q:
        query = query.where(
            LoginEvent.username.ilike(f"%{q.strip()}%") | LoginEvent.ip.ilike(f"%{q.strip()}%")
        )
    if result:
        query = query.where(LoginEvent.result == result)
    if date_from:
        query = query.where(func.date(LoginEvent.created_at) >= date_from)
    if date_to:
        query = query.where(func.date(LoginEvent.created_at) <= date_to)
    items, total = paginate(db, query, page)
    return Page(
        items=[
            LoginEventOut(
                id=e.id,
                created_at=e.created_at,
                username=e.username,
                ip=e.ip,
                user_agent=e.user_agent,
                result=e.result,
                result_label=LOGIN_RESULT_LABELS[e.result],
            )
            for e in items
        ],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )
