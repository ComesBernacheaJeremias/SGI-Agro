"""CUIT/CUIL: normalización y validación del dígito verificador (módulo 11)."""

import re

_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def normalize_cuit(value: str) -> str:
    """Deja solo los dígitos: '20-12345678-9' → '20123456789'."""
    return re.sub(r"\D", "", value)


def is_valid_cuit(value: str) -> bool:
    digits = normalize_cuit(value)
    if len(digits) != 11:
        return False
    total = sum(int(d) * w for d, w in zip(digits[:10], _WEIGHTS, strict=True))
    check = 11 - total % 11
    check = 0 if check == 11 else 9 if check == 10 else check
    return check == int(digits[10])


def format_cuit(value: str) -> str:
    digits = normalize_cuit(value)
    return f"{digits[:2]}-{digits[2:10]}-{digits[10:]}" if len(digits) == 11 else value
