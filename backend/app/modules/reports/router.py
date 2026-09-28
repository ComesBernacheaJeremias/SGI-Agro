"""Catálogo de reportes, ejecución (pantalla) y exportación (Excel/PDF). ADR-019."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Response

from app.core.db import DbSession
from app.core.errors import ForbiddenError
from app.core.export import to_pdf, to_xlsx
from app.core.reports import REPORTS, ReportDef, ReportFilter, ReportQuery, TableReport, get_report
from app.core.schemas import Schema
from app.modules.identity.authorization import effective_permissions
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

MEDIA = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


# Orden de los grupos en el catálogo: primero la rentabilidad (lo que más mira el dueño)
GROUP_ORDER = ["Costos y rentabilidad", "Comercial y caja", "Inventario", "Activos"]


def _group_position(report: ReportDef) -> int:
    return GROUP_ORDER.index(report.group) if report.group in GROUP_ORDER else len(GROUP_ORDER)


class ReportInfo(Schema):
    key: str
    title: str
    group: str
    description: str
    filters: list[ReportFilter]


def _allowed(user: User, key: str) -> ReportDef:
    report = get_report(key)
    if report.permission.code not in effective_permissions(user.role):
        raise ForbiddenError(f"No tenés permiso para ver: {report.title}.")
    return report


@router.get("")
def list_reports(user: CurrentUser) -> list[ReportInfo]:
    permissions = effective_permissions(user.role)
    return [
        ReportInfo(
            key=r.key, title=r.title, group=r.group, description=r.description, filters=r.filters
        )
        for r in sorted(REPORTS.values(), key=_group_position)
        if r.permission.code in permissions
    ]


@router.get("/{key}")
def run_report(key: str, db: DbSession, user: CurrentUser, params: ReportQuery) -> TableReport:
    return _allowed(user, key).build(db, params)


@router.get(
    "/{key}/export",
    response_class=Response,
    responses={200: {"content": {m: {} for m in MEDIA.values()}}},
)
def export_report(
    key: str,
    db: DbSession,
    user: CurrentUser,
    params: ReportQuery,
    format: Literal["xlsx", "pdf"] = "xlsx",
) -> Response:
    report = _allowed(user, key).build(db, params)
    content = to_xlsx(report) if format == "xlsx" else to_pdf(report)
    filename = f"{key}-{date.today():%Y-%m-%d}.{format}"
    return Response(
        content=content,
        media_type=MEDIA[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
