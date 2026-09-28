"""Seguridad de accesos: registro de ingresos, tope por IP, cierre de sesiones, claves débiles."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.ratelimit import RateLimiter
from app.modules.identity.auth_router import SESSION_COOKIE
from app.modules.identity.authorization import OWNER, STAFF
from app.modules.identity.models import LoginEvent, LoginResult, SessionToken
from tests.factories import DEFAULT_PASSWORD, create_user, login_as

LOGIN = "/api/v1/auth/login"


def attempt(client: TestClient, username: str, password: str = DEFAULT_PASSWORD) -> int:
    response = client.post(LOGIN, json={"username": username, "password": password})
    return response.status_code


def test_login_attempts_are_recorded_with_ip(client: TestClient, db: Session) -> None:
    create_user(db, username="ana")
    assert attempt(client, "ana") == 200
    assert attempt(client, "ana", "clave-mala-1234") == 401
    assert attempt(client, "nadie") == 401
    events = db.scalars(select(LoginEvent).order_by(LoginEvent.created_at)).all()
    assert [(e.username, e.result) for e in events] == [
        ("ana", LoginResult.SUCCESS),
        ("ana", LoginResult.FAILED),
        ("nadie", LoginResult.FAILED),
    ]
    assert all(e.ip == "testclient" for e in events)


def test_too_many_failures_from_one_ip_are_blocked(client: TestClient, db: Session) -> None:
    create_user(db, username="ana")
    limit = get_settings().login_ip_max_attempts
    for i in range(limit):  # usuarios distintos: el bloqueo por usuario no alcanza
        assert attempt(client, f"inventado{i}") == 401
    response = client.post(LOGIN, json={"username": "ana", "password": DEFAULT_PASSWORD})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_owner_sees_login_events_and_staff_does_not(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    rows = client.get("/api/v1/audit/logins").json()["items"]
    assert rows[0]["result"] == "success" and rows[0]["result_label"] == "Ingreso correcto"
    login_as(client, db, STAFF)
    assert client.get("/api/v1/audit/logins").status_code == 403


def test_admin_closes_all_sessions_of_a_user(client: TestClient, db: Session) -> None:
    staff = create_user(db, username="empleado")
    assert attempt(client, "empleado") == 200
    client.cookies.clear()
    login_as(client, db, OWNER)
    response = client.post(f"/api/v1/users/{staff.id}/revoke-sessions")
    assert response.status_code == 204
    open_sessions = db.scalars(
        select(SessionToken).where(
            SessionToken.user_id == staff.id, SessionToken.revoked_at.is_(None)
        )
    ).all()
    assert open_sessions == []


def test_changing_own_password_closes_the_other_sessions(client: TestClient, db: Session) -> None:
    user = create_user(db, username="ana")
    other = client.post(LOGIN, json={"username": "ana", "password": DEFAULT_PASSWORD})
    assert other.status_code == 200
    client.cookies.clear()
    current = client.post(LOGIN, json={"username": "ana", "password": DEFAULT_PASSWORD})
    token = current.json()["access_token"]
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "otra-clave-segura-99"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
    still_open = db.scalars(
        select(SessionToken).where(
            SessionToken.user_id == user.id, SessionToken.revoked_at.is_(None)
        )
    ).all()
    assert len(still_open) == 1  # solo la sesión desde la que se cambió
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert SESSION_COOKIE in client.cookies


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = RateLimiter(per_minute=3)
    assert [limiter.allow("1.2.3.4", now=t) for t in (0, 1, 2, 3)] == [True, True, True, False]
    assert limiter.allow("5.6.7.8", now=3)  # otra IP, su propio tope
    assert limiter.allow("1.2.3.4", now=61)  # pasó el minuto


@pytest.mark.parametrize(
    ("secret", "password", "ok"),
    [
        ("cambiar-por-una-clave-larga-y-aleatoria", "una-clave-larga-123", False),
        ("x" * 40, "sgi_dev_password", False),
        ("x" * 40, "corta", False),
        ("clave-aleatoria-" * 3, "una-clave-larga-123", True),
    ],
)
def test_production_refuses_weak_secrets(secret: str, password: str, ok: bool) -> None:
    settings = Settings(
        environment="production",
        postgres_user="sgi",
        postgres_password=password,
        postgres_db="sgi",
        jwt_secret=secret,
    )
    if ok:
        settings.check_production()
    else:
        with pytest.raises(RuntimeError, match="insegura"):
            settings.check_production()
