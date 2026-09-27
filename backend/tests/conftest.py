"""Infraestructura de tests.

- Usa la base `<POSTGRES_DB>_test` (nunca la de desarrollo), migrada con Alembic al inicio.
- Cada test corre dentro de una transacción que se revierte al final: rápidos y aislados.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.main import app

TEST_DB_URL = get_settings().database_url(test=True)


@pytest.fixture(scope="session")
def connection() -> Iterator[Connection]:
    engine = create_engine(TEST_DB_URL)
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["url"] = TEST_DB_URL
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    with engine.connect() as conn:
        yield conn
    engine.dispose()


@pytest.fixture
def db(connection: Connection) -> Iterator[Session]:
    transaction = connection.begin()
    # join_transaction_mode: los commit() del código no cierran la transacción del test
    # autoflush=False: igual que la sesión de la app (app/core/db.py)
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def request_session() -> Iterator[Session]:
        """Como get_db: si el request falla, se revierte lo que hizo (savepoint propio)."""
        savepoint = db.begin_nested()
        try:
            yield db
        except Exception:
            if savepoint.is_active:
                savepoint.rollback()
            raise
        if savepoint.is_active:
            savepoint.commit()

    app.dependency_overrides[get_db] = request_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
