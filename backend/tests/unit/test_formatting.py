from datetime import date
from decimal import Decimal

from app.core.formatting import format_date, format_money, format_quantity


def test_money_and_quantity_use_argentine_format() -> None:
    assert format_money(Decimal("1234567.891")) == "$ 1.234.567,89"
    assert format_quantity(Decimal("1234.5")) == "1.234,50"
    assert format_quantity(Decimal("0.125")) == "0,125"


def test_zero_never_has_minus_sign() -> None:
    assert format_money(Decimal("-0.001")) == "$ 0,00"
    assert format_quantity(Decimal("-0")) == "0,00"
    assert format_money(Decimal("-1.5")) == "-$ 1,50"


def test_date() -> None:
    assert format_date(date(2026, 9, 27)) == "27/09/2026"
