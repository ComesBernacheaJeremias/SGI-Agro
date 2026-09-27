from datetime import date
from decimal import Decimal
from typing import Literal

from app.core.schemas import Schema
from app.modules.production.schemas import CycleOut


class QuantityRow(Schema):
    name: str
    unit: str
    quantity: Decimal
    amount: Decimal


class AmountRow(Schema):
    name: str
    amount: Decimal


class OperationTypeRow(Schema):
    name: str
    inputs: Decimal
    machinery: Decimal
    total: Decimal


class MonthRow(Schema):
    month: str  # "AAAA-MM"
    inputs: Decimal
    machinery: Decimal
    expenses: Decimal
    total: Decimal


class SaleBatchRow(Schema):
    batch: str
    quantity: Decimal  # unidad base del producto cosechado
    revenue: Decimal


class CycleCostOut(Schema):
    """Costo y rentabilidad de un ciclo, con desgloses."""

    cycle: CycleOut
    revenue: Decimal
    sold_quantity: Decimal
    margin: Decimal
    margin_per_ha: Decimal
    inputs: list[QuantityRow]
    machinery: list[QuantityRow]
    expenses: list[AmountRow]  # por categoría
    by_operation_type: list[OperationTypeRow]
    by_month: list[MonthRow]
    sales: list[SaleBatchRow]


class ResultLine(Schema):
    label: str
    amount: Decimal
    style: Literal["normal", "subtotal", "total"] = "normal"
    indent: int = 0


class ResultOut(Schema):
    """Resultado de gestión de un período."""

    date_from: date | None
    date_to: date | None
    sales: Decimal
    cost_of_sales: Decimal
    production: Decimal
    losses: Decimal
    structure: Decimal
    result: Decimal
    lines: list[ResultLine]
