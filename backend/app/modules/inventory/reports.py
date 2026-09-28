"""Reportes de inventario (se registran al importar el módulo — ver app/reports.py)."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.formatting import format_date
from app.core.pagination import PageParams
from app.core.reports import (
    ReportColumn,
    ReportFilter,
    ReportParams,
    ReportRow,
    TableReport,
    define_report,
    sum_rows,
)
from app.modules.inventory.permissions import INVENTORY_READ
from app.modules.inventory.queries import StockFilters, StockQueries

ALL = PageParams(page=1, page_size=100_000)


@define_report(
    key="stock_valued",
    title="Stock valorizado",
    group="Inventario",
    description="Cantidad, costo promedio y valor de cada producto, hoy o a una fecha.",
    permission=INVENTORY_READ,
    filters=[
        ReportFilter(kind="date", label="Stock al"),
        ReportFilter(kind="warehouse", label="Almacén"),
    ],
)
def stock_valued(db: Session, p: ReportParams) -> TableReport:
    filters = StockFilters(at=p.date_to, warehouse_id=p.warehouse_id)
    items, _ = StockQueries(db).stock(filters, ALL)
    rows = [
        ReportRow(
            cells={
                "code": r.product.code,
                "product": r.product.name,
                "warehouse": r.warehouse.name if r.warehouse else "Todos",
                "quantity": r.quantity,
                "unit": r.unit,
                "avg_cost": r.avg_cost,
                "value": r.value,
            }
        )
        for r in items
    ]
    return TableReport(
        key="stock_valued",
        title="Stock valorizado",
        subtitle=f"Al {format_date(p.date_to)}" if p.date_to else "Al día de hoy",
        columns=[
            ReportColumn(key="code", label="Código"),
            ReportColumn(key="product", label="Producto"),
            ReportColumn(key="warehouse", label="Almacén"),
            ReportColumn(key="quantity", label="Cantidad", kind="quantity"),
            ReportColumn(key="unit", label="Unidad"),
            ReportColumn(key="avg_cost", label="Costo promedio", kind="money"),
            ReportColumn(key="value", label="Valor", kind="money"),
        ],
        rows=rows,
        totals={"value": sum_rows(rows, ["value"])["value"] or Decimal(0)},
        notes=["La producción propia entra al stock a costo 0 (su costo está en el cultivo)."],
    )
