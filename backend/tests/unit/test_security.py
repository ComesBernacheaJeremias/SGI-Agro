from datetime import UTC, datetime, timedelta

from uuid6 import uuid7

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_password_hash_verifies_only_the_right_password() -> None:
    password_hash = hash_password("clave-segura-123")

    assert verify_password(password_hash, "clave-segura-123")
    assert not verify_password(password_hash, "otra-clave")
    assert not verify_password("hash-invalido", "clave-segura-123")


def test_access_token_roundtrip() -> None:
    user_id = uuid7()

    assert decode_access_token(create_access_token(user_id)) == user_id


def test_expired_access_token_is_rejected() -> None:
    issued_long_ago = datetime.now(UTC) - timedelta(hours=1)

    assert decode_access_token(create_access_token(uuid7(), now=issued_long_ago)) is None


def test_session_token_hash_is_stable_and_not_the_token() -> None:
    assert hash_session_token("abc") == hash_session_token("abc")
    assert hash_session_token("abc") != "abc"
