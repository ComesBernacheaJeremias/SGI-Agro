import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import all_permissions
from app.modules.identity.authorization import OWNER, READ_ONLY, STAFF, SUPPORT
from app.modules.identity.models import RolePermission
from app.modules.identity.repository import RoleRepository
from tests.factories import login_as

PERMISSIONS = "/api/v1/permissions"
ME = "/api/v1/auth/me"


def test_me_returns_role_and_effective_permissions(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)

    body = client.get(ME).json()

    assert body["role"]["code"] == "support"
    assert body["role"]["name"] == "Soporte"
    assert set(body["permissions"]) == {p.code for p in all_permissions()}


def test_read_only_gets_only_read_permissions(client: TestClient, db: Session) -> None:
    login_as(client, db, READ_ONLY)

    permissions = client.get(ME).json()["permissions"]

    assert permissions
    assert all(code.endswith(":read") for code in permissions)


@pytest.mark.parametrize("role", [SUPPORT, OWNER, READ_ONLY])
def test_roles_with_users_read_can_list_permissions(
    client: TestClient, db: Session, role: str
) -> None:
    login_as(client, db, role)

    response = client.get(PERMISSIONS)

    assert response.status_code == 200
    groups = {group["group"] for group in response.json()}
    assert "Usuarios y roles" in groups


def test_staff_without_permission_gets_403_with_clear_message(
    client: TestClient, db: Session
) -> None:
    login_as(client, db, STAFF)

    response = client.get(PERMISSIONS)

    assert response.status_code == 403
    assert response.json()["error"]["message"] == (
        "No tenés permiso para: Usuarios y roles → Ver usuarios y roles."
    )


def test_editable_role_uses_stored_permissions(client: TestClient, db: Session) -> None:
    staff = RoleRepository(db).get_by_code(STAFF)
    assert staff is not None
    staff.permissions.append(RolePermission(permission="users:read"))
    db.flush()
    login_as(client, db, STAFF)

    assert client.get(PERMISSIONS).status_code == 200


def test_unauthenticated_gets_401(client: TestClient) -> None:
    assert client.get(PERMISSIONS).status_code == 401
