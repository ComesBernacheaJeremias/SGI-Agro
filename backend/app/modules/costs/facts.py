"""Hechos de costo con sus dimensiones (ADR-005): de acá salen todos los cálculos de costos.

- Insumos: salidas de stock de labores (costo promedio o congelado del ciclo).
- Maquinaria: uso × tarifa de las labores, repartido por superficie (costo por tarifa).
- Gastos: líneas de gasto de compras y gastos de caja (neto de IVA).
- Repuestos: consumos de stock de mantenimientos (costo del activo).
- Mermas: ajustes de stock y egresos manuales (a costo).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, RowMapping, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.modules.assets.maintenance import parts_rows
from app.modules.assets.models import Asset
from app.modules.commercial.expenses import expense_rows
from app.modules.commercial.models import CashMovement, CommercialDocument, ExpenseCategory
from app.modules.inventory.models import DocumentType, StockDocument, StockMove
from app.modules.masterdata.models import Party, Product, Unit
from app.modules.production.models import CropCycle, FieldOperation, OperationType, Plot
from app.modules.production.queries import machinery_rows

ZERO = Decimal(0)
ACTIVE_MOVE = StockMove.cancelled.is_(False)


@dataclass(frozen=True)
class Scope:
    """Filtro común de los hechos (todo opcional)."""

    date_from: date | None = None
    date_to: date | None = None
    cycle_ids: list[UUID] | None = None
    farm_id: UUID | None = None
    plot_id: UUID | None = None


def _between(
    column: ColumnElement[date] | InstrumentedAttribute[date], scope: Scope
) -> list[ColumnElement[bool]]:
    """Condiciones del período (vacío = sin límite)."""
    conditions: list[ColumnElement[bool]] = []
    if scope.date_from:
        conditions.append(column >= scope.date_from)
    if scope.date_to:
        conditions.append(column <= scope.date_to)
    return conditions


@dataclass(frozen=True)
class InputFact:
    date: date
    crop_cycle_id: UUID | None
    plot_id: UUID | None
    product_name: str
    unit: str
    operation_type: str
    quantity: Decimal
    cost: Decimal


def input_facts(session: Session, scope: Scope) -> list[InputFact]:
    query = (
        select(
            StockMove.date,
            StockMove.crop_cycle_id,
            StockMove.plot_id,
            Product.name,
            Unit.code,
            OperationType.name,
            -StockMove.quantity,
            -StockMove.total_cost,
        )
        .join(Product, Product.id == StockMove.product_id)
        .join(Unit, Unit.id == Product.unit_id)
        .join(FieldOperation, FieldOperation.id == StockMove.field_operation_id)
        .join(OperationType, OperationType.id == FieldOperation.operation_type_id)
        .where(StockMove.quantity < 0, ACTIVE_MOVE)
    )
    query = query.where(*_between(StockMove.date, scope))
    if scope.cycle_ids is not None:
        query = query.where(StockMove.crop_cycle_id.in_(scope.cycle_ids))
    if scope.plot_id:
        query = query.where(StockMove.plot_id == scope.plot_id)
    if scope.farm_id:
        query = query.where(StockMove.farm_id == scope.farm_id)
    return [InputFact(*r) for r in session.execute(query).all()]


@dataclass(frozen=True)
class MachineryFact:
    date: date
    crop_cycle_id: UUID
    plot_id: UUID
    asset_name: str
    meter: str
    operation_type: str
    usage: Decimal
    cost: Decimal


def machinery_facts(session: Session, scope: Scope) -> list[MachineryFact]:
    rows = machinery_rows()
    query = (
        select(
            rows.c.date,
            rows.c.crop_cycle_id,
            CropCycle.plot_id,
            Asset.name,
            Asset.meter,
            OperationType.name,
            rows.c.usage,
            rows.c.cost,
        )
        .join(CropCycle, CropCycle.id == rows.c.crop_cycle_id)
        .join(Plot, Plot.id == CropCycle.plot_id)
        .join(Asset, Asset.id == rows.c.asset_id)
        .join(OperationType, OperationType.id == rows.c.operation_type_id)
    )
    query = query.where(*_between(rows.c.date, scope))
    if scope.cycle_ids is not None:
        query = query.where(rows.c.crop_cycle_id.in_(scope.cycle_ids))
    if scope.plot_id:
        query = query.where(CropCycle.plot_id == scope.plot_id)
    if scope.farm_id:
        query = query.where(Plot.farm_id == scope.farm_id)
    return [
        MachineryFact(r[0], r[1], r[2], r[3], str(r[4]), r[5], Decimal(r[6]), Decimal(r[7]))
        for r in session.execute(query).all()
    ]


@dataclass(frozen=True)
class ExpenseFact:
    date: date
    source: str  # "purchase" | "cash"
    source_id: UUID
    label: str  # comprobante o número de movimiento
    party_name: str
    category: str
    description: str
    farm_id: UUID | None
    plot_id: UUID | None
    crop_cycle_id: UUID | None
    asset_id: UUID | None
    amount: Decimal

    @property
    def is_structure(self) -> bool:
        return not (self.farm_id or self.plot_id or self.crop_cycle_id or self.asset_id)


@dataclass(frozen=True)
class ExpenseScope(Scope):
    category_id: UUID | None = None
    asset_id: UUID | None = None


def expense_facts(session: Session, scope: ExpenseScope) -> list[ExpenseFact]:
    e = expense_rows()
    query = (
        select(e, ExpenseCategory.name.label("category_name"), Party.name.label("party_name"))
        .outerjoin(ExpenseCategory, ExpenseCategory.id == e.c.category_id)
        .outerjoin(Party, Party.id == e.c.party_id)
        .order_by(e.c.date)
    )
    query = query.where(*_between(e.c.date, scope))
    if scope.cycle_ids is not None:
        query = query.where(e.c.crop_cycle_id.in_(scope.cycle_ids))
    if scope.plot_id:
        query = query.where(e.c.plot_id == scope.plot_id)
    if scope.farm_id:
        query = query.where(e.c.farm_id == scope.farm_id)
    if scope.category_id:
        query = query.where(e.c.category_id == scope.category_id)
    if scope.asset_id:
        query = query.where(e.c.asset_id == scope.asset_id)
    rows = session.execute(query).mappings().all()
    labels = _source_labels(session, rows)
    return [
        ExpenseFact(
            date=r["date"],
            source=r["source"],
            source_id=r["source_id"],
            label=labels.get(r["source_id"], ""),
            party_name=r["party_name"] or "",
            category=r["category_name"] or "Sin categoría",
            description=r["description"] or "",
            farm_id=r["farm_id"],
            plot_id=r["plot_id"],
            crop_cycle_id=r["crop_cycle_id"],
            asset_id=r["asset_id"],
            amount=Decimal(r["amount"]),
        )
        for r in rows
    ]


def _source_labels(session: Session, rows: Sequence[RowMapping]) -> dict[UUID, str]:
    ids = {r["source_id"] for r in rows}
    labels = {
        d.id: d.invoice_label
        for d in session.scalars(select(CommercialDocument).where(CommercialDocument.id.in_(ids)))
    }
    labels.update(
        session.execute(
            select(CashMovement.id, CashMovement.number).where(CashMovement.id.in_(ids))
        ).all()
    )
    return labels


def parts_cost(session: Session, scope: Scope) -> Decimal:
    """Repuestos consumidos en mantenimientos de activos."""
    parts = parts_rows()
    query = select(func.coalesce(func.sum(parts.c.cost), 0)).where(*_between(parts.c.date, scope))
    return Decimal(session.execute(query).scalar_one())


def stock_losses(session: Session, scope: Scope) -> Decimal:
    """Mermas: ajustes de stock y egresos manuales, a costo (positivo = pérdida)."""
    query = (
        select(func.coalesce(-func.sum(StockMove.total_cost), 0))
        .join(StockDocument, StockDocument.id == StockMove.document_id)
        .where(
            StockDocument.type.in_([DocumentType.ADJUSTMENT, DocumentType.MANUAL_OUT]),
            ACTIVE_MOVE,
        )
    )
    return Decimal(session.execute(query.where(*_between(StockMove.date, scope))).scalar_one())
