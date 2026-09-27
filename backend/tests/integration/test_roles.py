from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import all_permissions
from app.modules.identity.authorization import OWNER, STAFF
from tests.factories import create_user, login_as

ROLES = "/api/v1/roles"


def roles_by_code(client: TestClient) -> dict[str, dict]:  # type: ignore[type-arg]
    return {r["code"]: r for r in client.get(ROLES).json()}


def test_list_roles_with_effective_permissions(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    roles = roles_by_code(client)

    assert set(roles) >= {"support", "owner", "staff", "read_only"}
    assert roles["support"]["permissions_editable"] is False
    assert roles["staff"]["permissions_editable"] is True
    assert set(roles["support"]["permissions"]) == {p.code for p in all_permissions()}
    assert roles["owner"]["user_count"] >= 1


def test_create_custom_role(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.post(
        ROLES, json={"name": "Encargado de campo", "permissions": ["users:read"]}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "encargado_de_campo"
    assert body["permissions"] == ["users:read"]


def test_duplicate_role_name_is_rejected(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.post(ROLES, json={"name": "administrativo"})

    assert response.status_code == 409


def test_unknown_permission_is_rejected(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.post(ROLES, json={"name": "Raro", "permissions": ["no:existe"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_PERMISSION"


def test_computed_roles_cannot_be_modified(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    owner_id = roles_by_code(client)["owner"]["id"]

    response = client.patch(f"{ROLES}/{owner_id}", json={"permissions": []})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SYSTEM_ROLE"


def test_staff_permissions_are_editable(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    staff_id = roles_by_code(client)["staff"]["id"]

    response = client.patch(f"{ROLES}/{staff_id}", json={"permissions": ["users:read"]})

    assert response.status_code == 200
    assert response.json()["permissions"] == ["users:read"]


def test_role_in_use_cannot_be_deleted(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    role = client.post(ROLES, json={"name": "Temporal"}).json()
    create_user(db, username="asignado", role=role["code"])

    response = client.delete(f"{ROLES}/{role['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROLE_IN_USE"


def test_unused_custom_role_can_be_deleted(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    role = client.post(ROLES, json={"name": "Descartable"}).json()

    assert client.delete(f"{ROLES}/{role['id']}").status_code == 204
    assert "descartable" not in roles_by_code(client)


def test_system_roles_cannot_be_deleted(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)

    response = client.delete(f"{ROLES}/{roles_by_code(client)[STAFF]['id']}")

    assert response.status_code == 409
