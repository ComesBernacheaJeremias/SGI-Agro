"""Formato argentino para textos generados en el backend (mensajes de error, Excel, PDF).

Mismas reglas que el frontend: fechas dd/mm/aaaa; números 1.234.567,89;
precios 2 decimales; cantidades 2 decimales y hasta 3 si hace falta.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def _format(value: Decimal, min_decimals: int, max_decimals: int) -> str:
    rounded = value.quantize(Decimal(1).scaleb(-max_decimals), rounding=ROUND_HALF_UP)
    rounded = abs(rounded) if rounded == 0 else rounded  # sin "-0,00"
    text = f"{rounded:,.{max_decimals}f}"  # 1,234,567.891 (formato inglés)
    integer, _, fraction = text.partition(".")
    fraction = fraction.rstrip("0").ljust(min_decimals, "0")
    integer = integer.replace(",", ".")
    return f"{integer},{fraction}" if fraction else integer


def format_quantity(value: Decimal) -> str:
    return _format(value, 2, 3)


def format_money(value: Decimal) -> str:
    return f"$ {_format(value, 2, 2)}"


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")
