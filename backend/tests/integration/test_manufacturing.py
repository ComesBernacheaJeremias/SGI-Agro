"""Elaboración: recetas multinivel, preparación, faltantes, costo derivado y cascada."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER
from tests.factories import login_as

TODAY = date.today()


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


class Kitchen:
    """Venenos A y B, agua; Mezcla base (semielaborado) e Insecticida (terminado)."""

    def __init__(self, client: TestClient) -> None:
        self.c = client
        units = client.get("/api/v1/units", params={"page_size": 100}).json()["items"]
        self.L = next(u["id"] for u in units if u["code"] == "L")
        self.wh = self.post("/api/v1/warehouses", name="Depósito", kind="depot")["id"]
        self.poison_a = self.product("Veneno A", "input")
        self.poison_b = self.product("Veneno B", "input")
        self.water = self.product("Agua", "input")
        self.base = self.product("Mezcla base", "semi_finished")
        self.insecticide = self.product("Insecticida tomate", "finished")
        self.purchase = self.buy(
            [(self.poison_a, "10", "1000"), (self.poison_b, "10", "2000"), (self.water, "100", "0")]
        )
        self.base_recipe = self.recipe(self.base, [(self.poison_b, "0.7"), (self.water, "0.3")])
        self.insecticide_recipe = self.recipe(
            self.insecticide, [(self.poison_a, "1"), (self.base, "0.5")]
        )

    def post(self, url: str, **body: Any) -> Any:
        response = self.c.post(url, json=body)
        assert response.status_code == 201, response.json()
        return response.json()

    def product(self, name: str, type_: str) -> str:
        return str(self.post("/api/v1/products", name=name, type=type_, unit_id=self.L)["id"])

    def buy(self, lines: list[tuple[str, str, str]]) -> Any:
        return self.post(
            "/api/v1/stock-documents",
            type="manual_in",
            date=day(-30),
            warehouse_id=self.wh,
            lines=[
                {"product_id": p, "unit_id": self.L, "quantity": q, "unit_cost": c}
                for p, q, c in lines
            ],
        )["document"]

    def recipe(self, product: str, components: list[tuple[str, str]]) -> str:
        return str(
            self.post(
                "/api/v1/recipes",
                product_id=product,
                yield_quantity="1",
                yield_unit_id=self.L,
                components=[
                    {"product_id": p, "unit_id": self.L, "quantity": q} for p, q in components
                ],
            )["id"]
        )

    def prepare(self, recipe: str, quantity: str, **extra: Any) -> Any:
        return self.c.post(
            "/api/v1/production-orders",
            json={
                "date": day(-10),
                "recipe_id": recipe,
                "quantity": quantity,
                "components_warehouse_id": self.wh,
                "target_warehouse_id": self.wh,
            }
            | extra,
        )

    def stock(self, product: str) -> Decimal:
        rows = self.c.get("/api/v1/stock", params={"include_zero": True}).json()["items"]
        return sum(
            (Decimal(r["quantity"]) for r in rows if r["product"]["id"] == product), Decimal(0)
        )

    def avg(self, product: str) -> Decimal:
        rows = self.c.get("/api/v1/stock", params={"include_zero": True}).json()["items"]
        return Decimal(next(r["avg_cost"] for r in rows if r["product"]["id"] == product))


@pytest.fixture
def kitchen(client: TestClient, db: Session) -> Kitchen:
    login_as(client, db, OWNER)
    return Kitchen(client)


def test_example_10_liters_of_poison_make_10_liters(kitchen: Kitchen) -> None:
    """Ejemplo del cliente: 1 L de veneno A por litro; 10 L alcanzan justo para 10 L."""
    recipe = kitchen.recipe(kitchen.product("Producto X", "finished"), [(kitchen.poison_a, "1")])

    ok = kitchen.prepare(recipe, "10")
    too_much = kitchen.prepare(recipe, "1")

    assert ok.status_code == 201, ok.json()
    assert kitchen.stock(kitchen.poison_a) == 0
    assert too_much.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_cost_is_sum_of_components(kitchen: Kitchen) -> None:
    kitchen.prepare(kitchen.base_recipe, "2")  # 0,7 L B ($1.400) + 0,3 L agua ($0) por litro

    order = kitchen.prepare(kitchen.insecticide_recipe, "1").json()["order"]

    assert kitchen.avg(kitchen.base) == 1400
    assert Decimal(order["unit_cost"]) == Decimal("1700.00")  # 1 L A ($1.000) + 0,5 L base ($700)


def test_check_shows_missing_semi_finished(kitchen: Kitchen) -> None:
    check = kitchen.c.post(
        "/api/v1/production-orders/check",
        json={
            "date": day(-10),
            "recipe_id": kitchen.insecticide_recipe,
            "quantity": "4",
            "components_warehouse_id": kitchen.wh,
        },
    ).json()

    base = next(c for c in check if c["product"]["id"] == kitchen.base)
    assert Decimal(base["missing"]) == 2
    assert base["can_prepare"] is True


def test_prepare_missing_creates_sub_orders(kitchen: Kitchen) -> None:
    without = kitchen.prepare(kitchen.insecticide_recipe, "4")
    response = kitchen.prepare(kitchen.insecticide_recipe, "4", prepare_missing=True)

    assert without.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    body = response.json()
    assert response.status_code == 201, body
    assert [o["recipe"]["name"] for o in body["prepared"]] == ["Mezcla base"]
    assert Decimal(body["prepared"][0]["quantity"]) == 2
    assert kitchen.stock(kitchen.insecticide) == 4
    assert kitchen.stock(kitchen.base) == 0


def test_component_price_change_cascades_to_elaborated_cost(kitchen: Kitchen) -> None:
    kitchen.prepare(kitchen.base_recipe, "1")

    kitchen.c.put(
        f"/api/v1/stock-documents/{kitchen.purchase['id']}",
        json={
            "type": "manual_in",
            "date": day(-30),
            "warehouse_id": kitchen.wh,
            "lines": [
                {
                    "product_id": kitchen.poison_a,
                    "unit_id": kitchen.L,
                    "quantity": "10",
                    "unit_cost": "1000",
                },
                {
                    "product_id": kitchen.poison_b,
                    "unit_id": kitchen.L,
                    "quantity": "10",
                    "unit_cost": "4000",
                },
                {
                    "product_id": kitchen.water,
                    "unit_id": kitchen.L,
                    "quantity": "100",
                    "unit_cost": "0",
                },
            ],
        },
    )

    assert kitchen.avg(kitchen.base) == 2800  # 0,7 L × $4.000


def test_circular_recipe_is_rejected(kitchen: Kitchen) -> None:
    response = kitchen.c.patch(
        f"/api/v1/recipes/{kitchen.base_recipe}",
        json={
            "components": [
                {"product_id": kitchen.insecticide, "unit_id": kitchen.L, "quantity": "1"}
            ],
        },
    )

    assert response.json()["error"]["code"] == "RECIPE_CYCLE"


def test_recipe_product_must_be_elaborated(kitchen: Kitchen) -> None:
    response = kitchen.c.post(
        "/api/v1/recipes",
        json={
            "product_id": kitchen.poison_a,
            "yield_quantity": "1",
            "yield_unit_id": kitchen.L,
            "components": [{"product_id": kitchen.water, "unit_id": kitchen.L, "quantity": "1"}],
        },
    )

    assert response.json()["error"]["code"] == "RECIPE_PRODUCT"


def test_cancel_order_restores_stock(kitchen: Kitchen) -> None:
    order = kitchen.prepare(kitchen.base_recipe, "2").json()["order"]

    kitchen.c.post(f"/api/v1/production-orders/{order['id']}/cancel")

    assert kitchen.stock(kitchen.base) == 0
    assert kitchen.stock(kitchen.poison_b) == 10


def test_recipe_estimated_cost(kitchen: Kitchen) -> None:
    recipe = kitchen.c.get(f"/api/v1/recipes/{kitchen.insecticide_recipe}").json()

    # Sin stock de mezcla, estima con su propia receta: 1.000 + 0,5 × 1.400
    assert Decimal(recipe["estimated_cost"]) == Decimal("1700.00")
    assert next(c for c in recipe["components"] if c["product"]["id"] == kitchen.base)["has_recipe"]
