"""Creación de datos de prueba legibles."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import STAFF
from app.modules.identity.models import User
from app.modules.identity.repository import RoleRepository
from app.modules.identity.schemas import UserCreate
from app.modules.identity.user_service import UserService

DEFAULT_PASSWORD = "clave-segura-123"


def create_user(
    db: Session,
    username: str = "secretario",
    password: str = DEFAULT_PASSWORD,
    role: str = STAFF,
    **fields: object,
) -> User:
    role_obj = RoleRepository(db).get_by_code(role)
    assert role_obj is not None
    data = UserCreate(
        username=username, full_name="Usuario de prueba", role_id=role_obj.id, password=password
    )
    user = UserService(db).create(data)
    for name, value in fields.items():
        setattr(user, name, value)
    db.flush()
    return user


def login_as(client: TestClient, db: Session, role: str, username: str | None = None) -> None:
    """Crea un usuario con el rol dado y deja al cliente autenticado (header Authorization)."""
    user = create_user(db, username=username or f"user_{role}", role=role)
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": DEFAULT_PASSWORD}
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
