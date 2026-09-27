"""Motor de stock: costo promedio ponderado y control de stock negativo (ADR-010).

Cada vez que cambian los movimientos de un producto (alta, edición, anulación, carga con
fecha pasada) se recalcula su cadena desde la fecha afectada, en orden cronológico:

- Entrada con costo propio (ingreso, compra, cosecha): mueve el promedio
      promedio = (stock × promedio + cantidad × costo) / (stock + cantidad)
- Entrada derivada (elaboración): su costo = lo consumido en el mismo comprobante; también
  mueve el promedio. Si cambia el costo de un componente, se recalcula en cascada el
  producto elaborado (y lo que se elaboró con él…).
- Resto (salidas, transferencias, ajustes): toma el promedio vigente, no lo cambia.
- Movimientos congelados (ciclos finalizados): conservan su costo (las entradas congeladas
  igual cuentan para el promedio).
- Ningún almacén puede quedar con stock negativo en ningún momento → error claro.
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import BusinessRuleError
from app.core.formatting import format_date, format_quantity
from app.modules.inventory.models import CostMode, StockMove
from app.modules.masterdata.models import Product, Warehouse

COST_PRECISION = Decimal("0.000001")
MONEY_PRECISION = Decimal("0.01")

MAX_CASCADE = 1000  # tope de recálculos encadenados (protege de bucles)

CHRONOLOGICAL = (StockMove.date, StockMove.document_id, StockMove.line_no, StockMove.sub_no)


class StockEngine:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_products(self, product_ids: Iterable[UUID]) -> None:
        """Bloquea los productos hasta el fin de la transacción: dos cargas simultáneas del
        mismo producto se procesan una después de la otra (en orden de id: sin deadlocks)."""
        ids = sorted(set(product_ids))
        if ids:
            self.session.execute(
                select(Product.id).where(Product.id.in_(ids)).order_by(Product.id).with_for_update()
            )

    def recalculate_many(self, product_ids: Iterable[UUID], from_date: date) -> None:
        """Recalcula varios productos y, en cascada, los elaborados que dependen de ellos."""
        pending: dict[UUID, date] = dict.fromkeys(product_ids, from_date)
        for _ in range(MAX_CASCADE):
            if not pending:
                return
            product_id = min(pending)  # orden determinístico
            start = pending.pop(product_id)
            self.recalculate(product_id, start)
            for derived_id, derived_date in self._derived_from(product_id, start):
                self.lock_products([derived_id])
                pending[derived_id] = min(pending.get(derived_id, derived_date), derived_date)
        raise BusinessRuleError(
            "El recálculo de costos no terminó (¿recetas circulares?).", code="COST_CASCADE"
        )

    def _derived_from(self, product_id: UUID, from_date: date) -> list[tuple[UUID, date]]:
        """Productos elaborados (y desde qué fecha) que consumieron `product_id`."""
        consumed, produced = aliased(StockMove), aliased(StockMove)
        rows = self.session.execute(
            select(produced.product_id, func.min(produced.date))
            .join(consumed, consumed.document_id == produced.document_id)
            .where(
                consumed.product_id == product_id,
                consumed.quantity < 0,
                consumed.date >= from_date,
                consumed.cancelled.is_(False),
                produced.cost_mode == CostMode.DERIVED,
                produced.cancelled.is_(False),
            )
            .group_by(produced.product_id)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def _consumed_cost(self, move: StockMove) -> Decimal:
        """Costo total de lo que consumió el comprobante de una entrada derivada."""
        total = self.session.scalar(
            select(func.coalesce(func.sum(StockMove.total_cost), 0)).where(
                StockMove.document_id == move.document_id,
                StockMove.quantity < 0,
                StockMove.cancelled.is_(False),
            )
        )
        return -Decimal(total or 0)

    def recalculate(self, product_id: UUID, from_date: date) -> None:
        self.session.flush()
        active = (StockMove.product_id == product_id, StockMove.cancelled.is_(False))

        previous = self.session.scalars(
            select(StockMove)
            .where(*active, StockMove.date < from_date)
            .order_by(*(c.desc() for c in CHRONOLOGICAL))
            .limit(1)
        ).first()
        average = previous.avg_cost_after if previous else Decimal(0)
        total = previous.balance_after if previous else Decimal(0)
        by_warehouse: dict[UUID, Decimal] = dict(
            self.session.execute(
                select(StockMove.warehouse_id, func.sum(StockMove.quantity))
                .where(*active, StockMove.date < from_date)
                .group_by(StockMove.warehouse_id)
            ).all()
        )

        moves = self.session.scalars(
            select(StockMove).where(*active, StockMove.date >= from_date).order_by(*CHRONOLOGICAL)
        ).all()
        for move in moves:
            quantity = move.quantity
            if move.frozen or move.cost_mode == CostMode.OWN:
                cost = move.unit_cost  # congelado o costo propio: se respeta
            elif move.cost_mode == CostMode.DERIVED and quantity > 0:
                cost = self._consumed_cost(move) / quantity
            else:
                cost = average
            is_costed_entry = move.cost_mode in (CostMode.OWN, CostMode.DERIVED)
            if is_costed_entry and quantity > 0:
                new_total = total + quantity
                average = (
                    ((total * average + quantity * cost) / new_total).quantize(COST_PRECISION)
                    if new_total > 0
                    else cost
                )
            total += quantity
            balance = by_warehouse.get(move.warehouse_id, Decimal(0)) + quantity
            by_warehouse[move.warehouse_id] = balance
            if balance < 0:
                self._raise_insufficient(product_id, move, balance)

            move.unit_cost = cost.quantize(COST_PRECISION)
            move.total_cost = (quantity * cost).quantize(MONEY_PRECISION)
            move.avg_cost_after = average
            move.balance_after = total

    def _raise_insufficient(self, product_id: UUID, move: StockMove, balance: Decimal) -> None:
        product = self.session.get(Product, product_id)
        warehouse = self.session.get(Warehouse, move.warehouse_id)
        product_name = product.name if product else "el producto"
        unit = product.unit.code if product else ""
        warehouse_name = warehouse.name if warehouse else "el almacén"
        available = balance - move.quantity
        raise BusinessRuleError(
            f"No alcanza el stock de {product_name} en {warehouse_name} el "
            f"{format_date(move.date)}: hay {format_quantity(available)} {unit} "
            f"y quedaría en {format_quantity(balance)} {unit}.",
            code="INSUFFICIENT_STOCK",
            details={
                "product_id": str(product_id),
                "warehouse_id": str(move.warehouse_id),
                "date": move.date.isoformat(),
            },
        )
