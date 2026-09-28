"""Reportes de activos (se registran al importar el módulo — ver app/reports.py)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.formatting import format_quantity
from app.core.reports import (
    ReportColumn,
    ReportFilter,
    ReportParams,
    ReportRow,
    TableReport,
    define_report,
    percent,
    period_text,
    sum_rows,
)
from app.modules.assets.maintenance import asset_costs, unit_of
from app.modules.assets.models import ASSET_KIND_LABELS, Asset
from app.modules.assets.permissions import ASSETS_READ
from app.modules.production.catalog import report_period


@define_report(
    key="asset_costs",
    title="Costo por activo",
    group="Activos",
    description="Uso, lo cargado a los ciclos por tarifa y los gastos reales de cada activo.",
    permission=ASSETS_READ,
    filters=[ReportFilter(kind="period", label="Período")],
)
def asset_costs_report(db: Session, p: ReportParams) -> TableReport:
    date_from, date_to = report_period(db, p.date_from, p.date_to, p.season_id)
    costs = asset_costs(db, date_from, date_to)
    assets = db.scalars(select(Asset).where(Asset.is_active.is_(True)).order_by(Asset.name))
    rows = []
    for asset in assets:
        cost = costs.get(asset.id)
        if cost is None:
            continue
        real = cost.real_rate
        rows.append(
            ReportRow(
                cells={
                    "asset": asset.name,
                    "kind": ASSET_KIND_LABELS[asset.kind],
                    "usage": f"{format_quantity(cost.usage)} {unit_of(asset)}",
                    "rate_cost": cost.rate_cost,
                    "expenses": cost.expenses,
                    "parts": cost.parts,
                    "total": cost.total,
                    "real_rate": real,
                    "rate": asset.rate,
                    "diff": percent(real - asset.rate, asset.rate) if real is not None else None,
                }
            )
        )
    return TableReport(
        key="asset_costs",
        title="Costo por activo",
        subtitle=period_text(date_from, date_to),
        columns=[
            ReportColumn(key="asset", label="Activo"),
            ReportColumn(key="kind", label="Tipo"),
            ReportColumn(key="usage", label="Uso en labores"),
            ReportColumn(key="rate_cost", label="Cargado a ciclos (tarifa)", kind="money"),
            ReportColumn(key="expenses", label="Gastos (compras y caja)", kind="money"),
            ReportColumn(key="parts", label="Repuestos", kind="money"),
            ReportColumn(key="total", label="Gasto real", kind="money"),
            ReportColumn(key="real_rate", label="Costo real (por hora o km)", kind="money"),
            ReportColumn(key="rate", label="Tarifa", kind="money"),
            ReportColumn(key="diff", label="Real vs. tarifa", kind="percent"),
        ],
        rows=rows,
        totals=sum_rows(rows, ["rate_cost", "expenses", "parts", "total"]),
        notes=[
            "Costo real = gastos con destino al activo + repuestos, dividido el uso en labores. "
            "Si es muy distinto de la tarifa, conviene ajustarla (Activos → editar).",
            "Montos sin IVA.",
        ],
    )
