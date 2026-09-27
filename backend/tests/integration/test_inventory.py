"""Inventario: motor de stock (costo promedio, negativos, recálculo), comprobantes y consultas."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, STAFF
from tests.factories import login_as

DOCS = "/api/v1/stock-documents"
TODAY = date.today()


def day(offset: int) -> str:
    """Fecha relativa a hoy (negativo = pasado)."""
    return (TODAY + timedelta(days=offset)).isoformat()


class Inventory:
    """Ayudante: crea maestros y comprobantes con lo mínimo para cada test."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        units = client.get("/api/v1/units", params={"page_size": 100}).json()["items"]
        self.unit = {u["code"]: u["id"] for u in units}
        self.main = self.warehouse("Depósito central")
        self.field = self.warehouse("Galpón campo")

    def warehouse(self, name: str) -> str:
        return str(
            self.client.post("/api/v1/warehouses", json={"name": name, "kind": "depot"}).json()[
                "id"
            ]
        )

    def product(self, name: str, unit: str = "L", **extra: Any) -> str:
        body = {"name": name, "type": "input", "unit_id": self.unit[unit]} | extra
        response = self.client.post("/api/v1/products", json=body)
        assert response.status_code == 201, response.json()
        return str(response.json()["id"])

    def doc(
        self, type_: str, lines: list[dict[str, Any]], *, when: int = -10, **header: Any
    ) -> Any:
        body = {
            "type": type_,
            "date": day(when),
            "warehouse_id": self.main,
            "lines": lines,
        } | header
        return self.client.post(DOCS, json=body)

    def line(
        self, product: str, qty: str, unit: str = "L", cost: str | None = None
    ) -> dict[str, Any]:
        return {
            "product_id": product,
            "unit_id": self.unit[unit],
            "quantity": qty,
            "unit_cost": cost,
        }

    def stock(self, product: str, **params: Any) -> Decimal:
        rows = self.client.get("/api/v1/stock", params={"include_zero": True, **params}).json()[
            "items"
        ]
        return sum(
            (Decimal(r["quantity"]) for r in rows if r["product"]["id"] == product), Decimal(0)
        )

    def avg(self, product: str) -> Decimal:
        rows = self.client.get("/api/v1/stock", params={"include_zero": True}).json()["items"]
        return Decimal(next(r["avg_cost"] for r in rows if r["product"]["id"] == product))


@pytest.fixture
def inv(client: TestClient, db: Session) -> Inventory:
    login_as(client, db, OWNER)
    return Inventory(client)


def lines_cost(response: Any) -> Decimal:
    return Decimal(response.json()["document"]["lines"][0]["total_cost"])


# --- Costo promedio ---


def test_example_10_liters_for_10000_then_use_3(inv: Inventory) -> None:
    """Ejemplo del cliente: 10 L por $10.000 → $1.000/L; usar 3 L cuesta $3.000."""
    poison = inv.product("Veneno A")
    created = inv.doc("manual_in", [inv.line(poison, "10", cost="1000")])

    used = inv.doc("manual_out", [inv.line(poison, "3")], when=-5)

    assert created.status_code == 201
    assert created.json()["document"]["number"] == "ING-000001"
    assert lines_cost(used) == Decimal("3000.00")
    assert inv.stock(poison) == 7


def test_weighted_average_of_two_purchases(inv: Inventory) -> None:
    product = inv.product("Fertilizante")
    inv.doc("manual_in", [inv.line(product, "10", cost="1000")], when=-10)
    inv.doc("manual_in", [inv.line(product, "10", cost="1400")], when=-9)

    used = inv.doc("manual_out", [inv.line(product, "5")], when=-8)

    assert inv.avg(product) == Decimal("1200")
    assert lines_cost(used) == Decimal("6000.00")


def test_editing_old_purchase_price_recalculates_later_outputs(inv: Inventory) -> None:
    product = inv.product("Urea")
    purchase = inv.doc("manual_in", [inv.line(product, "10", cost="1000")], when=-10).json()
    used = inv.doc("manual_out", [inv.line(product, "4")], when=-5).json()

    body = {
        "type": "manual_in",
        "date": day(-10),
        "warehouse_id": inv.main,
        "lines": [inv.line(product, "10", cost="2000")],
    }
    assert inv.client.put(f"{DOCS}/{purchase['document']['id']}", json=body).status_code == 200

    output = inv.client.get(f"{DOCS}/{used['document']['id']}").json()
    assert Decimal(output["lines"][0]["total_cost"]) == Decimal("8000.00")


# --- Stock negativo ---


def test_output_larger_than_stock_is_rejected_with_clear_message(inv: Inventory) -> None:
    product = inv.product("Glifosato")
    inv.doc("manual_in", [inv.line(product, "10", cost="100")])

    response = inv.doc("manual_out", [inv.line(product, "12")], when=-5)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INSUFFICIENT_STOCK"
    assert "Glifosato" in error["message"] and "Depósito central" in error["message"]
    assert "hay 10,00 L" in error["message"]


def test_backdated_output_cannot_leave_past_negative(inv: Inventory) -> None:
    product = inv.product("Cobre")
    inv.doc("manual_in", [inv.line(product, "10", cost="100")], when=-5)

    # Antes del ingreso no había stock
    response = inv.doc("manual_out", [inv.line(product, "1")], when=-6)

    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_cancel_consumed_input_is_rejected_but_cancel_output_restores(inv: Inventory) -> None:
    product = inv.product("Aceite")
    purchase = inv.doc("manual_in", [inv.line(product, "10", cost="100")]).json()
    output = inv.doc("manual_out", [inv.line(product, "8")], when=-5).json()

    blocked = inv.client.post(f"{DOCS}/{purchase['document']['id']}/cancel")
    cancelled = inv.client.post(f"{DOCS}/{output['document']['id']}/cancel")

    assert blocked.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert cancelled.status_code == 200
    assert cancelled.json()["document"]["status"] == "cancelled"
    assert inv.stock(product) == 10


def test_cancelled_document_cannot_be_edited(inv: Inventory) -> None:
    product = inv.product("Azufre")
    doc = inv.doc("manual_in", [inv.line(product, "5", cost="10")]).json()["document"]
    inv.client.post(f"{DOCS}/{doc['id']}/cancel")

    again = inv.client.post(f"{DOCS}/{doc['id']}/cancel")

    assert again.json()["error"]["code"] == "CANCELLED"


# --- Transferencias ---


def test_transfer_moves_stock_between_warehouses(inv: Inventory) -> None:
    product = inv.product("Gasoil")
    inv.doc("manual_in", [inv.line(product, "100", cost="900")])

    response = inv.doc(
        "transfer", [inv.line(product, "30")], when=-5, target_warehouse_id=inv.field
    )

    assert response.status_code == 201
    assert inv.stock(product, warehouse_id=inv.main) == 70
    assert inv.stock(product, warehouse_id=inv.field) == 30
    assert inv.stock(product) == 100
    assert inv.avg(product) == 900


def test_transfer_validations(inv: Inventory) -> None:
    product = inv.product("Nafta")
    inv.doc("manual_in", [inv.line(product, "10", cost="1")])

    same = inv.doc("transfer", [inv.line(product, "1")], when=-5, target_warehouse_id=inv.main)
    too_much = inv.doc(
        "transfer", [inv.line(product, "11")], when=-5, target_warehouse_id=inv.field
    )

    assert same.json()["error"]["code"] == "SAME_WAREHOUSE"
    assert too_much.json()["error"]["code"] == "INSUFFICIENT_STOCK"


# --- Unidades ---


def test_quantity_in_boxes_is_converted_to_base_unit(inv: Inventory) -> None:
    apple = inv.product(
        "Manzana",
        unit="cajón",
        type="own_produce",
        conversions=[{"unit_id": inv.unit["kg"], "quantity": "18"}],  # 1 cajón = 18 kg
    )

    response = inv.doc("manual_in", [inv.line(apple, "36", unit="kg", cost="500")])

    line = response.json()["document"]["lines"][0]
    assert Decimal(line["base_quantity"]) == 2
    assert inv.stock(apple) == 2
    assert inv.avg(apple) == 9000  # $500/kg × 18 kg por cajón


def test_same_kind_units_convert_automatically(inv: Inventory) -> None:
    seed = inv.product("Semilla", unit="kg")
    inv.doc("manual_in", [inv.line(seed, "1", unit="tn", cost="100000")])

    inv.doc("manual_out", [inv.line(seed, "500", unit="g")], when=-5)

    assert inv.stock(seed) == Decimal("999.5")


def test_unit_without_equivalence_is_rejected(inv: Inventory) -> None:
    product = inv.product("Herbicida", unit="L")

    response = inv.doc("manual_in", [inv.line(product, "1", unit="kg", cost="1")])

    assert response.json()["error"]["code"] == "NO_UNIT_CONVERSION"


# --- Ajustes ---


def test_adjustment_generates_the_difference(inv: Inventory) -> None:
    product = inv.product("Insecticida")
    inv.doc("manual_in", [inv.line(product, "10", cost="50")])

    response = inv.doc("adjustment", [inv.line(product, "7")], when=-5, reason="Conteo mensual")

    line = response.json()["document"]["lines"][0]
    assert Decimal(line["moved_quantity"]) == -3
    assert inv.stock(product) == 7


def test_adjustment_requires_reason(inv: Inventory) -> None:
    product = inv.product("Fungicida")

    response = inv.doc("adjustment", [inv.line(product, "1")], when=-5)

    assert response.json()["error"]["code"] == "REASON_REQUIRED"


def test_staff_cannot_adjust_by_default(client: TestClient, db: Session) -> None:
    login_as(client, db, OWNER)
    inv = Inventory(client)
    product = inv.product("Acaricida")
    login_as(client, db, STAFF)

    adjustment = inv.doc("adjustment", [inv.line(product, "1")], reason="x")
    normal = inv.doc("manual_in", [inv.line(product, "1", cost="1")])

    assert adjustment.status_code == 403
    assert normal.status_code == 201


# --- Validaciones ---


@pytest.mark.parametrize(
    ("type_", "line_cost", "when", "code"),
    [
        ("manual_in", None, -1, "COST_REQUIRED"),
        ("manual_in", "1", 3, "FUTURE_DATE"),
        ("purchase", "1", -1, "NOT_MANUAL"),
    ],
)
def test_document_validations(
    inv: Inventory, type_: str, line_cost: str | None, when: int, code: str
) -> None:
    product = inv.product("Producto X")

    response = inv.doc(type_, [inv.line(product, "1", cost=line_cost)], when=when)

    assert response.json()["error"]["code"] == code


def test_services_do_not_have_stock(inv: Inventory) -> None:
    service = inv.product("Flete", unit="un", type="service")

    response = inv.doc("manual_in", [inv.line(service, "1", unit="un", cost="1")])

    assert response.json()["error"]["code"] == "SERVICE_PRODUCT"


# --- Alertas de mínimo ---


def test_alert_when_stock_reaches_minimum(inv: Inventory) -> None:
    product = inv.product("Clorpirifos", min_stock="5")
    first = inv.doc("manual_in", [inv.line(product, "10", cost="1")])

    output = inv.doc("manual_out", [inv.line(product, "6")], when=-5)

    assert first.json()["alerts"] == []
    alert = output.json()["alerts"][0]
    assert alert["product"]["name"] == "Clorpirifos"
    assert Decimal(alert["missing"]) == 1
    assert [a["product"]["id"] for a in inv.client.get("/api/v1/stock/alerts").json()] == [product]
    below = inv.client.get("/api/v1/stock", params={"below_min": True}).json()["items"]
    assert [r["product"]["id"] for r in below] == [product]


# --- Consultas ---


def test_stock_at_a_past_date(inv: Inventory) -> None:
    product = inv.product("Abono")
    inv.doc("manual_in", [inv.line(product, "10", cost="1")], when=-10)
    inv.doc("manual_out", [inv.line(product, "4")], when=-2)

    assert inv.stock(product, at=day(-5)) == 10
    assert inv.stock(product) == 6


def test_kardex_with_running_balance(inv: Inventory) -> None:
    product = inv.product("Cal")
    inv.doc("manual_in", [inv.line(product, "10", cost="100")], when=-10)
    inv.doc("manual_out", [inv.line(product, "3")], when=-6)
    inv.doc("manual_in", [inv.line(product, "5", cost="100")], when=-2)

    kardex = inv.client.get(
        "/api/v1/stock/kardex", params={"product_id": product, "date_from": day(-7)}
    ).json()

    assert Decimal(kardex["opening_balance"]) == 10
    assert [Decimal(r["balance"]) for r in kardex["rows"]] == [7, 12]
    assert Decimal(kardex["closing_balance"]) == 12


def test_document_history_has_single_entry_with_lines(inv: Inventory) -> None:
    product = inv.product("Zinc")
    doc = inv.doc("manual_in", [inv.line(product, "2", cost="1500")]).json()["document"]

    history = inv.client.get(f"/api/v1/audit/records/stock_documents/{doc['id']}").json()["items"]

    assert len(history) == 1
    lines = next(c for c in history[0]["changes"] if c["field"] == "lines")
    assert lines["after"] == ["Zinc: 2,00 L × $ 1.500,00"]


def test_base_unit_cannot_change_after_movements(inv: Inventory) -> None:
    product = inv.product("Potasio", unit="kg")
    inv.doc("manual_in", [inv.line(product, "5", unit="kg", cost="1")])

    response = inv.client.patch(f"/api/v1/products/{product}", json={"unit_id": inv.unit["L"]})

    assert response.json()["error"]["code"] == "BASE_UNIT_LOCKED"
