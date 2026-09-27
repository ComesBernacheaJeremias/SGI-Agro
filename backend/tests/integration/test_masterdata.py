from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, READ_ONLY, STAFF
from tests.factories import login_as

VALID_CUIT = "33-69345023-9"


@pytest.fixture
def owner(client: TestClient, db: Session) -> TestClient:
    login_as(client, db, OWNER)
    return client


def unit_id(client: TestClient, code: str) -> str:
    units = client.get("/api/v1/units", params={"q": code, "page_size": 50}).json()["items"]
    return str(next(u["id"] for u in units if u["code"] == code))


def create_product(client: TestClient, **overrides: Any) -> dict[str, Any]:
    body = {"name": "Glifosato", "type": "input", "unit_id": unit_id(client, "L")} | overrides
    response = client.post("/api/v1/products", json=body)
    assert response.status_code == 201, response.json()
    return response.json()  # type: ignore[no-any-return]


# --- Opciones y unidades ---


def test_options_are_in_spanish(owner: TestClient) -> None:
    options = owner.get("/api/v1/masterdata/options").json()

    assert {"value": "input", "label": "Insumo"} in options["product_types"]
    assert {"value": "registered", "label": "Responsable Inscripto"} in options["vat_conditions"]
    assert "10.5" in options["vat_rates"]


def test_seeded_units_exist(owner: TestClient) -> None:
    codes = {
        u["code"] for u in owner.get("/api/v1/units", params={"page_size": 100}).json()["items"]
    }

    assert {"kg", "g", "tn", "L", "mL", "un", "cajón", "bin"} <= codes


# --- Productos ---


def test_product_code_is_generated_by_type(owner: TestClient) -> None:
    first = create_product(owner)
    second = create_product(owner, name="Urea")
    produce = create_product(
        owner, name="Tomate perita", type="own_produce", unit_id=unit_id(owner, "kg")
    )

    assert first["code"] == "INS-0001"
    assert second["code"] == "INS-0002"
    assert produce["code"] == "PRO-0001"


def test_manual_code_is_uppercased_and_unique(owner: TestClient) -> None:
    create_product(owner, code="gli-01")

    duplicate = owner.post(
        "/api/v1/products",
        json={"name": "Otro", "type": "input", "unit_id": unit_id(owner, "L"), "code": "GLI-01"},
    )

    assert duplicate.status_code == 409
    assert "GLI-01" in duplicate.json()["error"]["message"]


def test_product_conversions_and_history(owner: TestClient) -> None:
    product = create_product(
        owner,
        name="Manzana",
        type="own_produce",
        unit_id=unit_id(owner, "cajón"),
        conversions=[{"unit_id": unit_id(owner, "kg"), "quantity": "18"}],
    )

    assert product["conversions"][0]["unit"]["code"] == "kg"
    assert Decimal(product["conversions"][0]["quantity"]) == 18
    history = owner.get(f"/api/v1/audit/records/products/{product['id']}").json()["items"]
    conversions = next(c for c in history[0]["changes"] if c["field"] == "conversions")
    assert conversions["after"] == ["1 cajón = 18 kg"]


def test_conversion_to_base_unit_is_rejected(owner: TestClient) -> None:
    kg = unit_id(owner, "kg")
    response = owner.post(
        "/api/v1/products",
        json={
            "name": "Pera",
            "type": "own_produce",
            "unit_id": kg,
            "conversions": [{"unit_id": kg, "quantity": "1"}],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_CONVERSION"


def test_update_product_replaces_conversions(owner: TestClient) -> None:
    product = create_product(
        owner, conversions=[{"unit_id": unit_id(owner, "bidón"), "quantity": "0.05"}]
    )

    updated = owner.patch(
        f"/api/v1/products/{product['id']}", json={"conversions": [], "name": "Glifosato 48%"}
    )

    assert updated.status_code == 200
    assert updated.json()["conversions"] == []
    assert updated.json()["name"] == "Glifosato 48%"


def test_filter_products_by_type(owner: TestClient) -> None:
    create_product(owner)
    create_product(owner, name="Servicio de flete", type="service", unit_id=unit_id(owner, "un"))

    items = owner.get("/api/v1/products", params={"type": "service"}).json()["items"]

    assert [p["name"] for p in items] == ["Servicio de flete"]


# --- Categorías ---


def test_category_path_and_cycle_prevention(owner: TestClient) -> None:
    root = owner.post("/api/v1/product-categories", json={"name": "Raíz"}).json()
    child = owner.post(
        "/api/v1/product-categories", json={"name": "Hija", "parent_id": root["id"]}
    ).json()

    assert child["path"] == "Raíz > Hija"
    cycle = owner.patch(f"/api/v1/product-categories/{root['id']}", json={"parent_id": child["id"]})
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "CATEGORY_CYCLE"


def test_category_name_unique_within_parent(owner: TestClient) -> None:
    root = owner.post("/api/v1/product-categories", json={"name": "Nivel"}).json()
    owner.post("/api/v1/product-categories", json={"name": "Otros", "parent_id": root["id"]})

    duplicate = owner.post(
        "/api/v1/product-categories", json={"name": "OTROS", "parent_id": root["id"]}
    )
    other_level = owner.post("/api/v1/product-categories", json={"name": "Otros"})

    assert duplicate.status_code == 409
    assert other_level.status_code == 201


# --- Clientes y proveedores ---


def party_body(**overrides: Any) -> dict[str, Any]:
    return {
        "name": "Agro SA",
        "vat_condition": "registered",
        "is_supplier": True,
        "cuit": VALID_CUIT,
    } | overrides


def test_create_party_normalizes_cuit(owner: TestClient) -> None:
    response = owner.post("/api/v1/parties", json=party_body())

    assert response.status_code == 201
    assert response.json()["cuit"] == "33693450239"


def test_invalid_and_duplicate_cuit(owner: TestClient) -> None:
    owner.post("/api/v1/parties", json=party_body())

    invalid = owner.post("/api/v1/parties", json=party_body(cuit="33-69345023-8"))
    duplicate = owner.post("/api/v1/parties", json=party_body(name="Otra", cuit="33693450239"))

    assert invalid.json()["error"]["code"] == "INVALID_CUIT"
    assert duplicate.json()["error"]["code"] == "DUPLICATE"


def test_party_without_cuit_is_allowed(owner: TestClient) -> None:
    first = owner.post(
        "/api/v1/parties", json=party_body(cuit=None, vat_condition="final_consumer")
    )
    second = owner.post(
        "/api/v1/parties", json=party_body(name="Otro", cuit="", vat_condition="final_consumer")
    )

    assert first.status_code == second.status_code == 201


def test_party_must_be_customer_or_supplier(owner: TestClient) -> None:
    response = owner.post("/api/v1/parties", json=party_body(is_supplier=False))

    assert response.json()["error"]["code"] == "PARTY_ROLE_REQUIRED"


def test_filter_parties_by_role(owner: TestClient) -> None:
    owner.post("/api/v1/parties", json=party_body())
    owner.post(
        "/api/v1/parties",
        json=party_body(name="Cliente SRL", cuit=None, is_supplier=False, is_customer=True),
    )

    customers = owner.get("/api/v1/parties", params={"role": "customer"}).json()["items"]

    assert [p["name"] for p in customers] == ["Cliente SRL"]


# --- Almacenes y permisos ---


def test_warehouse_unique_name_and_deactivation(owner: TestClient) -> None:
    created = owner.post(
        "/api/v1/warehouses", json={"name": "Depósito central", "kind": "depot"}
    ).json()

    duplicate = owner.post("/api/v1/warehouses", json={"name": "DEPOSITO CENTRAL", "kind": "shed"})
    deactivated = owner.post(f"/api/v1/warehouses/{created['id']}/deactivate")

    assert duplicate.status_code == 409  # sin distinguir mayúsculas ni tildes
    assert deactivated.json()["is_active"] is False


def test_staff_can_write_read_only_cannot(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF)
    assert (
        client.post("/api/v1/warehouses", json={"name": "Galpón", "kind": "shed"}).status_code
        == 201
    )

    login_as(client, db, READ_ONLY)
    assert client.get("/api/v1/warehouses").status_code == 200
    assert (
        client.post("/api/v1/warehouses", json={"name": "Otro", "kind": "shed"}).status_code == 403
    )
