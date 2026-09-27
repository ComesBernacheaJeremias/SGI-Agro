"""Costos, rentabilidad y resultado de gestión (M08). Todo calculado desde los hechos.

- Costo de un ciclo: insumos + maquinaria (por tarifa) + servicios y gastos con destino = ciclo.
- Ingresos de un ciclo: ventas de sus partidas (sin IVA; la NC resta), de cualquier fecha.
- Resultado de gestión de un período: ventas − costo de lo vendido − costos de producción
  (insumos aplicados + gastos con destino, maquinaria por gastos reales y no por tarifa)
  − mermas − gastos de estructura.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.commercial.sales import sale_facts
from app.modules.costs.facts import (
    ExpenseScope,
    Scope,
    expense_facts,
    input_facts,
    machinery_facts,
    parts_cost,
    stock_losses,
)
from app.modules.costs.schemas import (
    AmountRow,
    CycleCostOut,
    MonthRow,
    OperationTypeRow,
    QuantityRow,
    ResultLine,
    ResultOut,
    SaleBatchRow,
)
from app.modules.production.models import Batch, CropCycle
from app.modules.production.queries import ProductionQueries
from app.modules.production.schemas import CycleOut

ZERO = Decimal(0)
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY)


def _sum_by[T](
    items: Iterable[T], key: Callable[[T], str], value: Callable[[T], Decimal]
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for item in items:
        totals[key(item)] += value(item)
    return totals


@dataclass(frozen=True)
class CycleProfit:
    cycle: CropCycle
    summary: CycleOut
    revenue: Decimal
    sold: Decimal

    @property
    def margin(self) -> Decimal:
        return self.revenue - self.summary.total_cost


class CostQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Ciclos ---

    def profitability(self, cycles: list[CropCycle]) -> list[CycleProfit]:
        summaries = ProductionQueries(self.session).cycle_summaries(cycles)
        sales = sale_facts(self.session, cycle_ids=[c.id for c in cycles])
        revenue = _sum_by(sales, lambda f: str(f.crop_cycle_id), lambda f: f.revenue)
        sold = _sum_by(sales, lambda f: str(f.crop_cycle_id), lambda f: f.quantity)
        return [
            CycleProfit(c, s, _money(revenue.get(str(c.id), ZERO)), sold.get(str(c.id), ZERO))
            for c, s in zip(cycles, summaries, strict=True)
        ]

    def cycle_detail(self, cycle_id: UUID) -> CycleCostOut:
        cycle = self.session.get(CropCycle, cycle_id)
        if cycle is None:
            raise NotFoundError("No se encontró el ciclo.")
        profit = self.profitability([cycle])[0]
        scope = Scope(cycle_ids=[cycle.id])
        inputs = input_facts(self.session, scope)
        machinery = machinery_facts(self.session, scope)
        expenses = expense_facts(self.session, ExpenseScope(cycle_ids=[cycle.id]))
        sales = sale_facts(self.session, cycle_ids=[cycle.id])

        by_product: dict[tuple[str, str], list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        for f in inputs:
            by_product[(f.product_name, f.unit)][0] += f.quantity
            by_product[(f.product_name, f.unit)][1] += f.cost
        by_asset: dict[tuple[str, str], list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        for m in machinery:
            unit = "km" if m.meter == "km" else "h"
            by_asset[(m.asset_name, unit)][0] += m.usage
            by_asset[(m.asset_name, unit)][1] += m.cost

        types: dict[str, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        for f in inputs:
            types[f.operation_type][0] += f.cost
        for m in machinery:
            types[m.operation_type][1] += m.cost

        months: dict[str, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO, ZERO])
        for f in inputs:
            months[f.date.strftime("%Y-%m")][0] += f.cost
        for m in machinery:
            months[m.date.strftime("%Y-%m")][1] += m.cost
        for e in expenses:
            months[e.date.strftime("%Y-%m")][2] += e.amount

        batch_codes = dict(
            self.session.execute(
                select(Batch.id, Batch.code).where(Batch.crop_cycle_id == cycle.id)
            ).all()
        )
        by_batch: dict[UUID, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        for s in sales:
            if s.batch_id:
                by_batch[s.batch_id][0] += s.quantity
                by_batch[s.batch_id][1] += s.revenue

        summary = profit.summary
        return CycleCostOut(
            cycle=summary,
            revenue=profit.revenue,
            sold_quantity=profit.sold,
            margin=_money(profit.margin),
            margin_per_ha=_money(profit.margin / cycle.area_ha),
            inputs=[
                QuantityRow(name=name, unit=unit, quantity=q, amount=_money(c))
                for (name, unit), (q, c) in sorted(by_product.items(), key=lambda i: -i[1][1])
            ],
            machinery=[
                QuantityRow(name=name, unit=unit, quantity=_money(u), amount=_money(c))
                for (name, unit), (u, c) in sorted(by_asset.items(), key=lambda i: -i[1][1])
            ],
            expenses=[
                AmountRow(name=name, amount=_money(amount))
                for name, amount in sorted(
                    _sum_by(expenses, lambda e: e.category, lambda e: e.amount).items(),
                    key=lambda i: -i[1],
                )
            ],
            by_operation_type=[
                OperationTypeRow(
                    name=name, inputs=_money(i), machinery=_money(m), total=_money(i + m)
                )
                for name, (i, m) in sorted(types.items(), key=lambda t: -(t[1][0] + t[1][1]))
            ],
            by_month=[
                MonthRow(
                    month=month,
                    inputs=_money(i),
                    machinery=_money(m),
                    expenses=_money(e),
                    total=_money(i + m + e),
                )
                for month, (i, m, e) in sorted(months.items())
            ],
            sales=[
                SaleBatchRow(batch=batch_codes.get(b, ""), quantity=q, revenue=_money(r))
                for b, (q, r) in by_batch.items()
            ],
        )

    # --- Resultado de gestión ---

    def management_result(self, date_from: date | None, date_to: date | None) -> ResultOut:
        scope = Scope(date_from=date_from, date_to=date_to)
        sales = sale_facts(self.session, date_from, date_to)
        expenses = expense_facts(self.session, ExpenseScope(date_from=date_from, date_to=date_to))
        product_sales = sum((s.revenue for s in sales if s.product), ZERO)
        other_sales = sum((s.revenue for s in sales if not s.product), ZERO)
        total_sales = product_sales + other_sales
        cost_of_sales = sum((s.cost for s in sales), ZERO)
        inputs = sum((f.cost for f in input_facts(self.session, scope)), ZERO)
        with_destination = _sum_by(
            (e for e in expenses if not e.is_structure), lambda e: e.category, lambda e: e.amount
        )
        structure = _sum_by(
            (e for e in expenses if e.is_structure), lambda e: e.category, lambda e: e.amount
        )
        parts = parts_cost(self.session, scope)
        production = inputs + parts + sum(with_destination.values(), ZERO)
        losses = stock_losses(self.session, scope)
        structure_total = sum(structure.values(), ZERO)
        gross = total_sales - cost_of_sales
        result = gross - production - losses - structure_total

        lines = [
            ResultLine(label="Ventas de productos", amount=product_sales, indent=1),
            ResultLine(label="Otros conceptos facturados", amount=other_sales, indent=1),
            ResultLine(label="Ventas netas", amount=total_sales, style="subtotal"),
            ResultLine(label="Costo de lo vendido (reventa y elaborados)", amount=-cost_of_sales),
            ResultLine(label="Margen bruto", amount=gross, style="subtotal"),
            ResultLine(label="Insumos aplicados en labores", amount=-inputs, indent=1),
            ResultLine(label="Repuestos de mantenimientos", amount=-parts, indent=1),
            *(
                ResultLine(label=name, amount=-amount, indent=1)
                for name, amount in sorted(with_destination.items())
            ),
            ResultLine(label="Costos de producción", amount=-production, style="subtotal"),
            ResultLine(label="Mermas y ajustes de stock", amount=-losses),
            *(
                ResultLine(label=name, amount=-amount, indent=1)
                for name, amount in sorted(structure.items())
            ),
            ResultLine(label="Gastos de estructura", amount=-structure_total, style="subtotal"),
            ResultLine(label="Resultado", amount=result, style="total"),
        ]
        return ResultOut(
            date_from=date_from,
            date_to=date_to,
            sales=_money(total_sales),
            cost_of_sales=_money(cost_of_sales),
            production=_money(production),
            losses=_money(losses),
            structure=_money(structure_total),
            result=_money(result),
            lines=[line.model_copy(update={"amount": _money(line.amount)}) for line in lines],
        )
