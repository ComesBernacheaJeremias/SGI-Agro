"""Consultas de producción: resumen de costos/cosecha por ciclo y cuaderno de campo.

Costos de un ciclo (se calculan, no se guardan — ADR-005):
- Insumos: salidas de stock con `crop_cycle_id` = ciclo (a costo promedio o congelado).
- Maquinaria: uso × tarifa de cada labor, en proporción a la superficie del ciclo.
- Servicios y otros gastos: líneas de compra (neto de IVA; la nota de crédito resta) y
  gastos de caja con destino = ciclo.
Cosecha: entradas de stock del producto cosechado con `crop_cycle_id` = ciclo.
"""

from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Subquery, func, select
from sqlalchemy.orm import Session

from app.modules.assets.models import meter_unit
from app.modules.commercial.expenses import expense_rows
from app.modules.inventory.models import StockMove
from app.modules.production.models import (
    Batch,
    CropCycle,
    FieldOperation,
    FieldOperationAsset,
    FieldOperationCycle,
    OperationStatus,
)
from app.modules.production.schemas import (
    CodeRef,
    CycleOut,
    FieldBookAsset,
    FieldBookEntry,
    FieldBookInput,
    HarvestOut,
    OperationAssetOut,
    OperationCycleOut,
    OperationInputOut,
    OperationOut,
    OperationSummaryOut,
    Ref,
)

ZERO = Decimal(0)
MONEY = Decimal("0.01")
QTY = Decimal("0.0001")
ACTIVE_MOVE = StockMove.cancelled.is_(False)


def machinery_rows() -> Subquery:
    """Uso de maquinaria de labores vigentes repartido por superficie entre sus ciclos:
    crop_cycle_id, field_operation_id, date, operation_type_id, asset_id, usage, cost."""
    share = FieldOperationCycle.area_ha / FieldOperation.total_area_ha
    return (
        select(
            FieldOperationCycle.crop_cycle_id,
            FieldOperation.id.label("field_operation_id"),
            FieldOperation.date,
            FieldOperation.operation_type_id,
            FieldOperationAsset.asset_id,
            (FieldOperationAsset.usage * share).label("usage"),
            (FieldOperationAsset.usage * FieldOperationAsset.rate * share).label("cost"),
        )
        .join(FieldOperation, FieldOperation.id == FieldOperationCycle.field_operation_id)
        .join(FieldOperationAsset, FieldOperationAsset.field_operation_id == FieldOperation.id)
        .where(FieldOperation.status == OperationStatus.ACTIVE)
        .subquery("machinery")
    )


def _share(value: Decimal, part: Decimal, total: Decimal) -> Decimal:
    return value * part / total if total else ZERO


class ProductionQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Ciclos ---

    def cycle_summaries(self, cycles: Iterable[CropCycle]) -> list[CycleOut]:
        cycles = list(cycles)
        ids = [c.id for c in cycles]
        if not ids:
            return []
        input_costs = dict(
            self.session.execute(
                select(StockMove.crop_cycle_id, -func.sum(StockMove.total_cost))
                .where(StockMove.crop_cycle_id.in_(ids), StockMove.quantity < 0, ACTIVE_MOVE)
                .group_by(StockMove.crop_cycle_id)
            ).all()
        )
        rows = machinery_rows()
        machinery: dict[UUID, Decimal] = dict(
            self.session.execute(
                select(rows.c.crop_cycle_id, func.sum(rows.c.cost))
                .where(rows.c.crop_cycle_id.in_(ids))
                .group_by(rows.c.crop_cycle_id)
            ).all()
        )
        expenses = self._expense_costs(ids)
        harvested = {
            (row[0], row[1]): row[2]
            for row in self.session.execute(
                select(StockMove.crop_cycle_id, StockMove.product_id, func.sum(StockMove.quantity))
                .where(StockMove.crop_cycle_id.in_(ids), StockMove.quantity > 0, ACTIVE_MOVE)
                .group_by(StockMove.crop_cycle_id, StockMove.product_id)
            ).all()
        }
        return [
            self._cycle_out(
                c,
                Decimal(input_costs.get(c.id) or 0),
                Decimal(machinery.get(c.id) or 0),
                expenses.get(c.id, ZERO),
                Decimal(harvested.get((c.id, c.crop.harvest_product_id)) or 0),
            )
            for c in cycles
        ]

    def _expense_costs(self, ids: list[UUID]) -> dict[UUID, Decimal]:
        expenses = expense_rows()
        rows = self.session.execute(
            select(expenses.c.crop_cycle_id, func.sum(expenses.c.amount))
            .where(expenses.c.crop_cycle_id.in_(ids))
            .group_by(expenses.c.crop_cycle_id)
        ).all()
        return {row[0]: Decimal(row[1]) for row in rows}

    @staticmethod
    def _cycle_out(
        c: CropCycle, inputs: Decimal, machinery: Decimal, expenses: Decimal, harvested: Decimal
    ) -> CycleOut:
        inputs, machinery = inputs.quantize(MONEY), machinery.quantize(MONEY)
        expenses = expenses.quantize(MONEY)
        total = inputs + machinery + expenses
        return CycleOut(
            id=c.id,
            name=c.name,
            farm=Ref(id=c.plot.farm.id, name=c.plot.farm.name),
            plot=Ref(id=c.plot.id, name=c.plot.name),
            crop=Ref(id=c.crop.id, name=c.crop.name),
            season=Ref(id=c.season.id, name=c.season.name),
            area_ha=c.area_ha,
            start_date=c.start_date,
            expected_end_date=c.expected_end_date,
            end_date=c.end_date,
            status=c.status,
            notes=c.notes,
            reopen_reason=c.reopen_reason,
            input_cost=inputs,
            machinery_cost=machinery,
            expense_cost=expenses,
            total_cost=total,
            harvested_quantity=harvested,
            harvest_unit=c.crop.harvest_product.unit.code,
            yield_per_ha=(harvested / c.area_ha).quantize(QTY) if harvested else None,
            cost_per_ha=(total / c.area_ha).quantize(MONEY),
            cost_per_unit=(total / harvested).quantize(MONEY) if harvested else None,
        )

    # --- Labores ---

    def _input_costs(
        self, operation_ids: list[UUID]
    ) -> dict[tuple[UUID | None, int, UUID | None], Decimal]:
        """Costo de insumos por (labor, línea, ciclo)."""
        rows = self.session.execute(
            select(
                StockMove.field_operation_id,
                StockMove.line_no,
                StockMove.crop_cycle_id,
                -func.sum(StockMove.total_cost),
            )
            .where(
                StockMove.field_operation_id.in_(operation_ids), StockMove.quantity < 0, ACTIVE_MOVE
            )
            .group_by(StockMove.field_operation_id, StockMove.line_no, StockMove.crop_cycle_id)
        ).all()
        return {(r[0], r[1], r[2]): Decimal(r[3] or 0) for r in rows}

    def _batches(self, operation_ids: list[UUID]) -> dict[UUID, str]:
        rows = self.session.execute(
            select(Batch.field_operation_id, Batch.code).where(
                Batch.field_operation_id.in_(operation_ids)
            )
        ).all()
        return {r[0]: r[1] for r in rows}

    def operation_out(self, op: FieldOperation) -> OperationOut:
        costs = self._input_costs([op.id])
        batch = self._batches([op.id]).get(op.id)
        inputs = [
            OperationInputOut(
                product=CodeRef(id=i.product.id, code=i.product.code, name=i.product.name),
                unit_id=i.unit_id,
                unit=i.unit.code,
                warehouse=Ref(id=i.warehouse.id, name=i.warehouse.name),
                quantity=i.quantity,
                dose_per_ha=i.dose_per_ha,
                cost=sum(
                    (v for (o, line, _), v in costs.items() if o == op.id and line == i.line_no),
                    ZERO,
                ).quantize(MONEY),
            )
            for i in op.inputs
        ]
        assets = [
            OperationAssetOut(
                asset=Ref(id=a.asset.id, name=a.asset.name),
                meter=a.asset.meter,
                usage=a.usage,
                rate=a.rate,
                cost=a.cost,
            )
            for a in op.assets
        ]
        harvest = None
        if op.is_harvest and op.harvest_product and op.harvest_unit and op.harvest_warehouse:
            harvest = HarvestOut(
                product=CodeRef(
                    id=op.harvest_product.id,
                    code=op.harvest_product.code,
                    name=op.harvest_product.name,
                ),
                unit_id=op.harvest_unit.id,
                unit=op.harvest_unit.code,
                quantity=op.harvest_quantity or ZERO,
                warehouse=Ref(id=op.harvest_warehouse.id, name=op.harvest_warehouse.name),
                is_final=op.is_final_harvest,
                batch_code=batch,
            )
        return OperationOut(
            id=op.id,
            number=op.number,
            date=op.date,
            operation_type=Ref(id=op.operation_type.id, name=op.operation_type.name),
            is_harvest=op.is_harvest,
            status=op.status,
            notes=op.notes,
            total_area_ha=op.total_area_ha,
            cycles=[
                OperationCycleOut(
                    crop_cycle_id=c.crop_cycle_id,
                    name=c.crop_cycle.name,
                    area_ha=c.area_ha,
                    status=c.crop_cycle.status,
                )
                for c in op.cycles
            ],
            inputs=inputs,
            assets=assets,
            harvest=harvest,
            stock_document_id=op.stock_document_id,
            editable=op.status == OperationStatus.ACTIVE
            and not any(c.crop_cycle.is_finished for c in op.cycles),
            total_cost=sum((i.cost for i in inputs), ZERO) + sum((a.cost for a in assets), ZERO),
        )

    def operation_summary(self, op: FieldOperation) -> OperationSummaryOut:
        out = self.operation_out(op)
        return OperationSummaryOut(
            id=op.id,
            number=op.number,
            date=op.date,
            operation_type=out.operation_type,
            is_harvest=out.is_harvest,
            cycles=[c.name for c in out.cycles],
            status=op.status,
            total_cost=out.total_cost,
        )

    # --- Cuaderno de campo ---

    def field_book(self, cycle: CropCycle) -> list[FieldBookEntry]:
        operations = list(
            self.session.scalars(
                select(FieldOperation)
                .join(FieldOperationCycle)
                .where(
                    FieldOperationCycle.crop_cycle_id == cycle.id,
                    FieldOperation.status == OperationStatus.ACTIVE,
                )
                .order_by(FieldOperation.date, FieldOperation.number)
            ).unique()
        )
        ids = [op.id for op in operations]
        costs = self._input_costs(ids)
        batches = self._batches(ids)
        entries = []
        for op in operations:
            share = next(c for c in op.cycles if c.crop_cycle_id == cycle.id)
            area, total = share.area_ha, op.total_area_ha
            inputs = [
                FieldBookInput(
                    product=i.product.name,
                    quantity=_share(i.quantity, area, total).quantize(QTY),
                    unit=i.unit.code,
                    dose_per_ha=(i.quantity / total).quantize(QTY) if total else None,
                    cost=costs.get((op.id, i.line_no, cycle.id), ZERO).quantize(MONEY),
                )
                for i in op.inputs
            ]
            assets = [
                FieldBookAsset(
                    asset=a.asset.name,
                    usage=_share(a.usage, area, total).quantize(MONEY),
                    unit=meter_unit(a.asset.meter),
                    cost=_share(a.cost, area, total).quantize(MONEY),
                )
                for a in op.assets
            ]
            entries.append(
                FieldBookEntry(
                    id=op.id,
                    number=op.number,
                    date=op.date,
                    operation_type=op.operation_type.name,
                    is_harvest=op.is_harvest,
                    area_ha=area,
                    inputs=inputs,
                    assets=assets,
                    harvest_quantity=op.harvest_quantity if op.is_harvest else None,
                    harvest_unit=op.harvest_unit.code
                    if op.is_harvest and op.harvest_unit
                    else None,
                    batch_code=batches.get(op.id),
                    cost=sum((x.cost for x in inputs), ZERO) + sum((x.cost for x in assets), ZERO),
                    notes=op.notes,
                )
            )
        return entries
