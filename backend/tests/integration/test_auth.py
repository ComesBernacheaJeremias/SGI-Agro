from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.modules.identity.auth_router import SESSION_COOKIE
from tests.factories import DEFAULT_PASSWORD, create_user

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def login(
    client: TestClient, username: str = "secretario", password: str = DEFAULT_PASSWORD
) -> Response:
    return client.post(LOGIN, json={"username": username, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Login ---


def test_login_ok_returns_token_user_and_session_cookie(client: TestClient, db: Session) -> None:
    create_user(db)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["username"] == "secretario"
    assert SESSION_COOKIE in response.cookies


def test_login_is_case_insensitive_on_username(client: TestClient, db: Session) -> None:
    create_user(db)

    assert login(client, username="SECRETARIO").status_code == 200


def test_login_wrong_password_and_unknown_user_give_same_message(
    client: TestClient, db: Session
) -> None:
    create_user(db)

    wrong_password = login(client, password="otra-clave-123")
    unknown_user = login(client, username="nadie")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["error"]["message"] == "Usuario o contraseña incorrectos."
    assert unknown_user.json()["error"]["message"] == "Usuario o contraseña incorrectos."


def test_account_locks_after_max_failed_attempts(client: TestClient, db: Session) -> None:
    create_user(db)

    for _ in range(5):
        login(client, password="incorrecta-123")
    response = login(client)  # ahora con la contraseña correcta

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    create_user(db, is_active=False)

    assert login(client).status_code == 401


# --- Sesión ---


def test_me_requires_valid_token(client: TestClient, db: Session) -> None:
    create_user(db)
    token = login(client).json()["access_token"]

    assert client.get(ME).status_code == 401
    assert client.get(ME, headers=auth_header("token-falso")).status_code == 401
    response = client.get(ME, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["username"] == "secretario"


def test_refresh_rotates_session_token(client: TestClient, db: Session) -> None:
    create_user(db)
    first_cookie = login(client).cookies[SESSION_COOKIE]

    response = client.post(REFRESH)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies[SESSION_COOKIE] != first_cookie


def test_reusing_old_session_token_revokes_all_sessions(client: TestClient, db: Session) -> None:
    create_user(db)
    old_cookie = login(client).cookies[SESSION_COOKIE]
    client.post(REFRESH)  # rota: old_cookie queda revocada
    current_cookie = client.cookies[SESSION_COOKIE]

    client.cookies.set(SESSION_COOKIE, old_cookie, path="/api/v1/auth")
    reuse = client.post(REFRESH)
    client.cookies.set(SESSION_COOKIE, current_cookie, path="/api/v1/auth")
    after = client.post(REFRESH)

    assert reuse.status_code == 401
    assert after.status_code == 401  # la sesión vigente también quedó cerrada


def test_refresh_without_cookie_fails(client: TestClient) -> None:
    response = client.post(REFRESH)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SESSION"


def test_logout_invalidates_session(client: TestClient, db: Session) -> None:
    create_user(db)
    login(client)
    cookie = client.cookies[SESSION_COOKIE]

    assert client.post(LOGOUT).status_code == 204
    client.cookies.set(SESSION_COOKIE, cookie, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401
