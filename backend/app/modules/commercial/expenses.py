"""Gastos registrados: líneas de gasto de compras (neto de IVA; la NC resta) y movimientos de
caja tipo gasto. Una sola consulta, la usan el costo del ciclo (producción) y los reportes de
costos, así la regla de qué es un gasto vive en un solo lugar.
"""

from sqlalchemy import Subquery, case, literal, null, select, union_all

from app.modules.commercial.models import (
    CashMovement,
    CashMovementKind,
    CommercialDocument,
    CommercialLine,
    Direction,
    DocumentKind,
    LineKind,
    Status,
)

SOURCE_PURCHASE = "purchase"
SOURCE_CASH = "cash"


def expense_rows() -> Subquery:
    """Subconsulta: date, source, source_id, party_id, category_id, description,
    farm_id, plot_id, crop_cycle_id, asset_id, amount."""
    sign = case((CommercialDocument.kind == DocumentKind.CREDIT_NOTE, -1), else_=1)
    purchases = (
        select(
            CommercialDocument.date.label("date"),
            literal(SOURCE_PURCHASE).label("source"),
            CommercialDocument.id.label("source_id"),
            CommercialDocument.party_id.label("party_id"),
            CommercialLine.expense_category_id.label("category_id"),
            CommercialLine.description.label("description"),
            CommercialLine.farm_id.label("farm_id"),
            CommercialLine.plot_id.label("plot_id"),
            CommercialLine.crop_cycle_id.label("crop_cycle_id"),
            CommercialLine.asset_id.label("asset_id"),
            (CommercialLine.net_amount * sign).label("amount"),
        )
        .join(CommercialDocument, CommercialDocument.id == CommercialLine.document_id)
        .where(
            CommercialLine.kind == LineKind.EXPENSE,
            CommercialDocument.direction == Direction.PURCHASE,
            CommercialDocument.status == Status.ACTIVE,
            CommercialDocument.is_opening_balance.is_(False),
        )
    )
    cash = select(
        CashMovement.date,
        literal(SOURCE_CASH),
        CashMovement.id,
        null(),
        CashMovement.expense_category_id,
        CashMovement.description,
        CashMovement.farm_id,
        CashMovement.plot_id,
        CashMovement.crop_cycle_id,
        CashMovement.asset_id,
        CashMovement.amount,
    ).where(CashMovement.kind == CashMovementKind.EXPENSE, CashMovement.status == Status.ACTIVE)
    return union_all(purchases, cash).subquery("expenses")
