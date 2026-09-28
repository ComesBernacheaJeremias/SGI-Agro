"""Altas con id generado en el dispositivo: reintentar el guardado no duplica (ADR-024)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER
from tests.factories import login_as
from tests.integration.test_production import Farm, day


@pytest.fixture
def farm(client: TestClient, db: Session) -> Farm:
    login_as(client, db, OWNER)
    return Farm(client)


def test_resending_an_operation_does_not_duplicate(farm: Farm) -> None:
    cycle = farm.cycle()
    op_id = str(uuid4())
    first = farm.apply(cycle["id"], "2", id=op_id)
    second = farm.apply(cycle["id"], "2", id=op_id)
    assert first.status_code == second.status_code == 201
    assert first.json()["operation"]["id"] == second.json()["operation"]["id"] == op_id
    assert farm.stock(farm.poison) == Decimal(8)  # se consumió una sola vez


def test_resending_a_stock_document_does_not_duplicate(farm: Farm) -> None:
    doc_id = str(uuid4())
    body = {
        "id": doc_id,
        "type": "manual_out",
        "date": day(-1),
        "warehouse_id": farm.warehouse,
        "lines": [{"product_id": farm.poison, "unit_id": farm.unit["L"], "quantity": "1"}],
    }
    for _ in range(2):
        response = farm.c.post("/api/v1/stock-documents", json=body)
        assert response.status_code == 201, response.json()
        assert response.json()["document"]["id"] == doc_id
    assert farm.stock(farm.poison) == Decimal(9)
