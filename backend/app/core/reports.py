"""Reportes: una sola definición por reporte → pantalla, Excel y PDF (ADR-019).

Cada módulo declara sus reportes con `@define_report(...)` en su `reports.py`; el constructor
recibe la sesión y los filtros (`ReportParams`) y devuelve un `TableReport` (columnas tipadas
+ filas). La pantalla y los exportadores formatean según el tipo de columna.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel as PydanticModel
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.formatting import format_date
from app.core.permissions import Permission
from app.core.schemas import Schema

ColumnKind = Literal["text", "money", "quantity", "percent", "date"]
RowStyle = Literal["normal", "subtotal", "total"]
Cell = str | Decimal | date | None


# --- Resultado de un reporte ---


class ReportColumn(Schema):
    key: str
    label: str
    kind: ColumnKind = "text"


class ReportLink(Schema):
    """Registro al que lleva la fila (la pantalla lo abre al tocarla)."""

    kind: Literal["cycle", "commercial_document", "cash_movement", "payment"]
    id: UUID


class ReportRow(Schema):
    cells: dict[str, Cell]
    style: RowStyle = "normal"
    indent: int = 0
    link: ReportLink | None = None


class TableReport(Schema):
    key: str
    title: str
    subtitle: str
    columns: list[ReportColumn]
    rows: list[ReportRow]
    totals: dict[str, Cell] | None = None
    notes: list[str] = Field(default_factory=list)


def sum_rows(rows: Iterable[ReportRow], keys: Iterable[str]) -> dict[str, Cell]:
    """Totales de las columnas `keys` (solo filas normales)."""
    rows = [r for r in rows if r.style == "normal"]
    return {
        k: sum((v for r in rows if isinstance(v := r.cells.get(k), Decimal)), Decimal(0))
        for k in keys
    }


def percent(part: Decimal, whole: Decimal) -> Decimal | None:
    return (part * 100 / whole).quantize(Decimal("0.1")) if whole else None


# --- Filtros ---

FilterKind = Literal[
    "period",  # date_from / date_to / season_id
    "date",  # date_to (ej. "stock al")
    "season",
    "farm",
    "plot",
    "crop",
    "expense_category",
    "party",
    "product",
    "product_type",
    "cash_account",
    "asset",
    "warehouse",
    "choice",  # `name` = group_by | scope | direction
]


class FilterOption(Schema):
    value: str
    label: str


class ReportFilter(Schema):
    kind: FilterKind
    label: str
    name: str | None = None  # solo "choice"
    options: list[FilterOption] = Field(default_factory=list)
    default: str | None = None
    required: bool = False


class ReportParams(PydanticModel):
    date_from: date | None = None
    date_to: date | None = None
    season_id: UUID | None = None
    farm_id: UUID | None = None
    plot_id: UUID | None = None
    crop_id: UUID | None = None
    expense_category_id: UUID | None = None
    party_id: UUID | None = None
    product_id: UUID | None = None
    product_type: str | None = None
    cash_account_id: UUID | None = None
    asset_id: UUID | None = None
    warehouse_id: UUID | None = None
    group_by: str | None = None
    scope: str | None = None
    direction: str | None = None


def _params(
    date_from: date | None = None,
    date_to: date | None = None,
    season_id: UUID | None = None,
    farm_id: UUID | None = None,
    plot_id: UUID | None = None,
    crop_id: UUID | None = None,
    expense_category_id: UUID | None = None,
    party_id: UUID | None = None,
    product_id: UUID | None = None,
    product_type: str | None = None,
    cash_account_id: UUID | None = None,
    asset_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    group_by: str | None = None,
    scope: str | None = None,
    direction: str | None = None,
) -> ReportParams:
    """Filtros como query params (todos opcionales; cada reporte usa los suyos)."""
    return ReportParams(**locals())


ReportQuery = Annotated[ReportParams, Depends(_params)]


def choice(name: str, label: str, options: dict[str, str], default: str) -> ReportFilter:
    return ReportFilter(
        kind="choice",
        name=name,
        label=label,
        options=[FilterOption(value=k, label=v) for k, v in options.items()],
        default=default,
    )


def period_text(date_from: date | None, date_to: date | None) -> str:
    if date_from and date_to:
        return f"Del {format_date(date_from)} al {format_date(date_to)}"
    if date_from:
        return f"Desde el {format_date(date_from)}"
    if date_to:
        return f"Hasta el {format_date(date_to)}"
    return "Todo el período"


# --- Registro ---

Builder = Callable[[Session, ReportParams], TableReport]


@dataclass(frozen=True)
class ReportDef:
    key: str
    title: str
    group: str
    description: str
    permission: Permission
    build: Builder
    filters: list[ReportFilter] = field(default_factory=list)


REPORTS: dict[str, ReportDef] = {}


def define_report(
    *,
    key: str,
    title: str,
    group: str,
    description: str,
    permission: Permission,
    filters: list[ReportFilter],
) -> Callable[[Builder], Builder]:
    def register(build: Builder) -> Builder:
        if key in REPORTS:
            raise ValueError(f"Reporte duplicado: {key}")
        REPORTS[key] = ReportDef(key, title, group, description, permission, build, filters)
        return build

    return register


def get_report(key: str) -> ReportDef:
    report = REPORTS.get(key)
    if report is None:
        raise NotFoundError("No existe el reporte.")
    return report


def require_value[T](value: T | None, message: str) -> T:
    if value is None:
        raise BusinessRuleError(message, code="REPORT_FILTER")
    return value
