"""Valorización INFORMATIVA de la producción propia en stock (ADR-012).

La cosecha entra al stock a costo cero: su costo vive en el ciclo. Para que Inventario y el
tablero no muestren $0, acá se estima cuánto vale lo que queda en stock de cada partida:
cantidad × costo por unidad de su ciclo (costo del ciclo ÷ cantidad cosechada).

⚠️ SOLO PARA MOSTRAR. No usar en costo de lo vendido, kardex, costo promedio ni resultado:
esos siguen con costo cero, porque el resultado de gestión ya descuenta el costo del ciclo
como "costos de producción"; usarlo ahí lo contaría dos veces.

Si el ciclo está en curso, el valor es **provisorio**: el costo por unidad cambia con cada
labor o cosecha nueva.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventory.models import StockMove
from app.modules.production.models import Batch, CropCycle, CycleStatus
from app.modules.production.queries import ProductionQueries

ZERO = Decimal(0)
MONEY = Decimal("0.01")


@dataclass(frozen=True)
class EstimatedValue:
    value: Decimal
    #: Algún ciclo de origen sigue en curso
    provisional: bool

    def __add__(self, other: "EstimatedValue") -> "EstimatedValue":
        return EstimatedValue(self.value + other.value, self.provisional or other.provisional)


NONE = EstimatedValue(ZERO, provisional=False)


def own_produce_values(
    session: Session,
    *,
    at: date | None = None,
    warehouse_id: UUID | None = None,
    by_warehouse: bool = False,
) -> dict[tuple[UUID, UUID | None], EstimatedValue]:
    """Valor estimado por (producto, almacén); almacén `None` = todos los almacenes."""
    per_warehouse = by_warehouse or warehouse_id is not None
    keys = [StockMove.product_id, Batch.crop_cycle_id]
    if per_warehouse:
        keys.append(StockMove.warehouse_id)
    query = (
        select(*keys, func.sum(StockMove.quantity).label("quantity"))
        .join(Batch, Batch.id == StockMove.batch_id)
        .where(StockMove.cancelled.is_(False))
        .group_by(*keys)
    )
    if at:
        query = query.where(StockMove.date <= at)
    if warehouse_id:
        query = query.where(StockMove.warehouse_id == warehouse_id)
    rows = [row for row in session.execute(query).all() if row.quantity > 0]

    cycle_ids = {row[1] for row in rows}
    cycles = session.scalars(select(CropCycle).where(CropCycle.id.in_(cycle_ids)))
    summaries = {s.id: s for s in ProductionQueries(session).cycle_summaries(cycles)}

    result: dict[tuple[UUID, UUID | None], EstimatedValue] = {}
    for row in rows:
        cycle = summaries[row[1]]
        if cycle.cost_per_unit is None:
            continue
        key = (row[0], row[2] if per_warehouse else None)
        value = EstimatedValue(
            (Decimal(row.quantity) * cycle.cost_per_unit).quantize(MONEY),
            provisional=cycle.status == CycleStatus.ACTIVE,
        )
        result[key] = result.get(key, NONE) + value
    return result


def own_produce_total(
    session: Session,
    *,
    at: date | None = None,
    warehouse_id: UUID | None = None,
    product_ids: set[UUID] | None = None,
) -> EstimatedValue:
    """Valor estimado de toda la producción propia en stock (opcional: solo esos productos)."""
    values = own_produce_values(session, at=at, warehouse_id=warehouse_id)
    return sum(
        (v for (product, _), v in values.items() if product_ids is None or product in product_ids),
        NONE,
    )
