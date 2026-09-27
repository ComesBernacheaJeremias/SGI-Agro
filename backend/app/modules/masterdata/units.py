"""Conversión de unidades de un producto (la usan inventario, compras, labores…)."""

from decimal import Decimal

from app.core.errors import BusinessRuleError
from app.modules.masterdata.models import Product, Unit, UnitKind


def unit_factor(product: Product, unit: Unit) -> Decimal:
    """Cuántas unidades base del producto equivale 1 `unit`.

    - Misma unidad: 1.
    - Equivalencia propia (1 cajón = 18 kg → 1 kg = 1/18 cajón).
    - Misma magnitud (g → kg, tn → kg, mL → L): por los factores de las unidades.
    """
    if unit.id == product.unit_id:
        return Decimal(1)
    for conversion in product.conversions:
        if conversion.unit_id == unit.id:
            return conversion.base_per_unit
    base = product.unit
    if unit.kind == base.kind and unit.kind != UnitKind.PACKAGE:
        return unit.factor / base.factor
    raise BusinessRuleError(
        f"No hay equivalencia entre {unit.code} y {base.code} para '{product.name}'. "
        "Cargala en Maestros → Productos → Equivalencias.",
        code="NO_UNIT_CONVERSION",
    )
