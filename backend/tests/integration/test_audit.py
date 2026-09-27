from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.db import DbSession
from app.main import app
from app.modules.identity.authorization import OWNER, STAFF, SUPPORT
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import RolePermission
from app.modules.identity.repository import RoleRepository
from tests.factories import create_user, login_as


def history(client: TestClient, table: str, record_id: object) -> list[dict]:  # type: ignore[type-arg]
    response = client.get(f"/api/v1/audit/records/{table}/{record_id}")
    assert response.status_code == 200
    return response.json()["items"]  # type: ignore[no-any-return]


def test_create_is_recorded_without_sensitive_fields(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)
    user = create_user(db, username="nuevo")

    entries = history(client, "users", user.id)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "create"
    assert entry["table_label"] == "Usuario"
    fields = {c["field"] for c in entry["changes"]}
    assert {"username", "full_name", "role_id"} <= fields
    assert "password_hash" not in fields


def test_update_records_only_changed_fields_with_labels(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)
    user = create_user(db, username="nuevo")

    user.full_name = "Nombre corregido"
    db.flush()

    latest = history(client, "users", user.id)[0]
    assert latest["action"] == "update"
    assert latest["changes"] == [
        {
            "field": "full_name",
            "label": "Nombre completo",
            "before": "Usuario de prueba",
            "after": "Nombre corregido",
        }
    ]


def test_references_are_shown_by_name(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)
    user = create_user(db, username="nuevo", role=STAFF)
    owner = RoleRepository(db).get_by_code(OWNER)
    assert owner is not None

    user.role = owner
    db.flush()

    change = history(client, "users", user.id)[0]["changes"][0]
    assert change == {
        "field": "role_id",
        "label": "Rol",
        "before": "Administrativo",
        "after": "Dueño",
    }


def test_deactivation_is_its_own_action(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)
    user = create_user(db, username="nuevo")

    user.is_active = False
    db.flush()

    assert history(client, "users", user.id)[0]["action"] == "deactivate"


def test_author_is_the_user_of_the_request(client: TestClient, db: Session) -> None:
    """El usuario se setea en un hilo (dependencia) y el cambio ocurre en otro (endpoint)."""
    staff = RoleRepository(db).get_by_code(STAFF)
    assert staff is not None

    @app.post("/api/test/rename-staff-role")
    def rename(user: CurrentUser, session: DbSession) -> None:
        role = RoleRepository(session).get_by_code(STAFF)
        assert role is not None
        role.description = "Cambiada por request"
        session.flush()

    login_as(client, db, SUPPORT, username="jefe")
    client.post("/api/test/rename-staff-role")

    entry = history(client, "roles", staff.id)[0]
    assert entry["user_name"] == "Usuario de prueba"
    assert staff.created_by is None  # creado por la migración
    assert staff.updated_by is not None  # modificado por el usuario del request


def test_role_permission_changes_are_recorded_as_list(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)
    staff = RoleRepository(db).get_by_code(STAFF)
    assert staff is not None

    staff.permissions.append(RolePermission(permission="users:read"))
    db.flush()

    change = history(client, "roles", staff.id)[0]["changes"][0]
    assert change["field"] == "permissions"
    assert change["label"] == "Permisos"
    assert "users:read" not in change["before"]
    assert change["after"] == sorted([*change["before"], "users:read"])


def test_session_tokens_are_not_audited(client: TestClient, db: Session) -> None:
    login_as(client, db, SUPPORT)

    tables = set(db.scalars(select(AuditLog.table_name)))

    assert "session_tokens" not in tables


def test_general_history_requires_permission(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF)

    assert client.get("/api/v1/audit").status_code == 403


def test_general_history_filters_by_table(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    create_user(db, username="otro")

    items = client.get("/api/v1/audit", params={"table": "users"}).json()["items"]

    assert items
    assert all(item["table_name"] == "users" for item in items)
