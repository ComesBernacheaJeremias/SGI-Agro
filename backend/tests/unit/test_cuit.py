from app.modules.masterdata.cuit import format_cuit, is_valid_cuit, normalize_cuit

VALID = "33693450239"  # CUIT de AFIP (dígito verificador correcto)


def test_valid_cuit_with_or_without_dashes() -> None:
    assert is_valid_cuit(VALID)
    assert is_valid_cuit("33-69345023-9")


def test_invalid_check_digit_or_length() -> None:
    assert not is_valid_cuit("33693450238")
    assert not is_valid_cuit("3369345023")
    assert not is_valid_cuit("")


def test_normalize_and_format() -> None:
    assert normalize_cuit("33-69345023-9") == VALID
    assert format_cuit(VALID) == "33-69345023-9"
