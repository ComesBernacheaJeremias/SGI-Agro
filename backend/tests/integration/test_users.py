from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, STAFF, SUPPORT
from app.modules.identity.repository import RoleRepository
from tests.factories import DEFAULT_PASSWORD, create_user, login_as

USERS = "/api/v1/users"


def role_id(db: Session, code: str) -> str:
    role = RoleRepository(db).get_by_code(code)
    assert role is not None
    return str(role.id)


def new_user_body(db: Session, **overrides: str) -> dict[str, str]:
    body = {
        "username": "juan",
        "full_name": "Juan Pérez",
        "role_id": role_id(db, STAFF),
        "password": "una-clave-larga",
    }
    return body | overrides


def test_create_and_get_user(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    created = client.post(USERS, json=new_user_body(db))

    assert created.status_code == 201
    body = created.json()
    assert body["username"] == "juan"
    assert body["role"]["code"] == STAFF
    assert "password" not in body and "password_hash" not in body
    assert client.get(f"{USERS}/{body['id']}").json()["full_name"] == "Juan Pérez"


def test_duplicate_username_ignores_case(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    client.post(USERS, json=new_user_body(db))

    response = client.post(USERS, json=new_user_body(db, username="JUAN"))

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Ya existe el usuario 'JUAN'."


def test_weak_password_is_rejected(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.post(USERS, json=new_user_body(db, password="corta"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"


def test_search_ignores_accents_and_case(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    client.post(USERS, json=new_user_body(db))

    items = client.get(USERS, params={"q": "PEREZ"}).json()["items"]

    assert [u["username"] for u in items] == ["juan"]


def test_owner_cannot_assign_support_role(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.post(USERS, json=new_user_body(db, role_id=role_id(db, SUPPORT)))

    assert response.status_code == 403


def test_owner_cannot_modify_support_user(client: TestClient, db: Session) -> None:
    support_user = create_user(db, username="dev", role=SUPPORT)
    login_as(client, db, OWNER)

    response = client.patch(f"{USERS}/{support_user.id}", json={"full_name": "Otro"})

    assert response.status_code == 403


def test_change_role_is_reflected(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    user_id = client.post(USERS, json=new_user_body(db)).json()["id"]

    response = client.patch(f"{USERS}/{user_id}", json={"role_id": role_id(db, OWNER)})

    assert response.json()["role"]["code"] == OWNER


def test_cannot_deactivate_yourself(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER, username="dueno")
    me = client.get("/api/v1/auth/me").json()

    response = client.post(f"{USERS}/{me['id']}/deactivate")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELF_DEACTIVATE"


def test_deactivated_user_cannot_login_and_is_hidden_by_default(
    client: TestClient, db: Session
) -> None:
    user = create_user(db, username="temporal")
    login_as(client, db, OWNER)

    client.post(f"{USERS}/{user.id}/deactivate")

    active = [u["username"] for u in client.get(USERS).json()["items"]]
    inactive = [
        u["username"] for u in client.get(USERS, params={"active": "false"}).json()["items"]
    ]
    assert "temporal" not in active and "temporal" in inactive
    login = client.post(
        "/api/v1/auth/login", json={"username": "temporal", "password": DEFAULT_PASSWORD}
    )
    assert login.status_code == 401


def test_reset_password(client: TestClient, db: Session) -> None:
    user = create_user(db, username="olvidadizo")
    login_as(client, db, OWNER)

    response = client.post(
        f"{USERS}/{user.id}/reset-password", json={"password": "clave-nueva-123"}
    )

    assert response.status_code == 204
    login = client.post(
        "/api/v1/auth/login", json={"username": "olvidadizo", "password": "clave-nueva-123"}
    )
    assert login.status_code == 200


def test_change_own_password(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF, username="yo")
    url = "/api/v1/auth/change-password"

    wrong = client.post(url, json={"current_password": "mala", "new_password": "clave-nueva-123"})
    ok = client.post(
        url, json={"current_password": DEFAULT_PASSWORD, "new_password": "clave-nueva-123"}
    )

    assert wrong.status_code == 401
    assert ok.status_code == 204


def test_staff_cannot_manage_users(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF)

    assert client.get(USERS).status_code == 403
    assert client.post(USERS, json=new_user_body(db)).status_code == 403
