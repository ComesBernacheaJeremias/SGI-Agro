"""Producción: ciclos, labores (reparto por superficie, maquinaria), cosecha, congelamiento."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, SUPPORT
from tests.factories import login_as

TODAY = date.today()


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def expected_season(d: date) -> str:
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}/{str(start + 1)[2:]}"


class Farm:
    """Arma un escenario: depósito, insecticida con stock, tomate, lote de 2 ha, tractor."""

    def __init__(self, client: TestClient) -> None:
        self.c = client
        units = client.get("/api/v1/units", params={"page_size": 100}).json()["items"]
        self.unit = {u["code"]: u["id"] for u in units}
        self.warehouse = self.post("/api/v1/warehouses", name="Depósito", kind="depot")["id"]
        self.poison = self.post(
            "/api/v1/products", name="Insecticida", type="input", unit_id=self.unit["L"]
        )["id"]
        self.tomato = self.post(
            "/api/v1/products",
            name="Tomate perita",
            type="own_produce",
            unit_id=self.unit["cajón"],
            conversions=[{"unit_id": self.unit["kg"], "quantity": "18"}],  # 1 cajón = 18 kg
        )["id"]
        self.crop = self.post(
            "/api/v1/crops",
            species="Tomate",
            variety="perita",
            kind="vegetable",
            harvest_product_id=self.tomato,
        )["id"]
        farm = self.post("/api/v1/farms", name="La Esperanza")["id"]
        self.plot = self.post(
            "/api/v1/plots", farm_id=farm, name="Lote 3", area_ha="2", kind="greenhouse"
        )["id"]
        self.tractor = self.post(
            "/api/v1/assets", name="Tractor 1", kind="machinery", meter="hours", rate="5000"
        )["id"]
        types = client.get("/api/v1/operation-types", params={"page_size": 50}).json()["items"]
        self.type = {t["name"]: t["id"] for t in types}
        # 10 L de insecticida a $1.000
        response = client.post(
            "/api/v1/stock-documents",
            json={
                "type": "manual_in",
                "date": day(-30),
                "warehouse_id": self.warehouse,
                "lines": [
                    {
                        "product_id": self.poison,
                        "unit_id": self.unit["L"],
                        "quantity": "10",
                        "unit_cost": "1000",
                    }
                ],
            },
        )
        assert response.status_code == 201, response.json()

    def post(self, url: str, **body: Any) -> Any:
        response = self.c.post(url, json=body)
        assert response.status_code == 201, response.json()
        return response.json()

    def cycle(self, area: str = "1.2", start: int = -20) -> dict[str, Any]:
        return self.post(  # type: ignore[no-any-return]
            "/api/v1/crop-cycles",
            plot_id=self.plot,
            crop_id=self.crop,
            area_ha=area,
            start_date=day(start),
        )

    def operation(
        self, cycles: list[dict[str, Any]], type_: str = "Aplicación", **extra: Any
    ) -> Any:
        body = {"date": day(-10), "operation_type_id": self.type[type_], "cycles": cycles} | extra
        return self.c.post("/api/v1/field-operations", json=body)

    def apply(self, cycle_id: str, liters: str = "2", **extra: Any) -> Any:
        inputs = [
            {
                "product_id": self.poison,
                "unit_id": self.unit["L"],
                "warehouse_id": self.warehouse,
                "quantity": liters,
            }
        ]
        return self.operation([{"crop_cycle_id": cycle_id}], inputs=inputs, **extra)

    def harvest(self, cycle_id: str, boxes: str = "10", final: bool = False) -> Any:
        return self.operation(
            [{"crop_cycle_id": cycle_id}],
            type_="Cosecha",
            harvest={
                "unit_id": self.unit["cajón"],
                "quantity": boxes,
                "warehouse_id": self.warehouse,
                "is_final": final,
            },
        )

    def get_cycle(self, cycle_id: str) -> dict[str, Any]:
        return self.c.get(f"/api/v1/crop-cycles/{cycle_id}").json()  # type: ignore[no-any-return]

    def stock(self, product: str) -> Decimal:
        rows = self.c.get("/api/v1/stock", params={"include_zero": True}).json()["items"]
        return sum(
            (Decimal(r["quantity"]) for r in rows if r["product"]["id"] == product), Decimal(0)
        )


@pytest.fixture
def farm(client: TestClient, db: Session) -> Farm:
    login_as(client, db, OWNER)
    return Farm(client)


# --- Ciclos ---


def test_cycle_gets_name_and_season_automatically(farm: Farm) -> None:
    cycle = farm.cycle()

    season = expected_season(TODAY - timedelta(days=20))
    assert cycle["name"] == f"Tomate perita · Lote 3 · {season}"
    assert cycle["season"]["name"] == season
    assert cycle["status"] == "active"


def test_cycles_cannot_exceed_plot_area(farm: Farm) -> None:
    farm.cycle(area="1.2")

    response = farm.c.post(
        "/api/v1/crop-cycles",
        json={
            "plot_id": farm.plot,
            "crop_id": farm.crop,
            "area_ha": "1",
            "start_date": day(-5),
        },
    )

    assert response.json()["error"]["code"] == "PLOT_AREA"
    assert "quedan 0,80 ha libres" in response.json()["error"]["message"]


# --- Labores ---


def test_application_consumes_stock_and_costs_the_cycle(farm: Farm) -> None:
    cycle = farm.cycle()

    response = farm.apply(cycle["id"], liters="2")

    assert response.status_code == 201, response.json()
    assert response.json()["operation"]["number"] == "LAB-000001"
    assert farm.stock(farm.poison) == 8
    assert Decimal(farm.get_cycle(cycle["id"])["input_cost"]) == Decimal("2000.00")


def test_dose_per_hectare_computes_total(farm: Farm) -> None:
    cycle = farm.cycle(area="1.2")
    inputs = [
        {
            "product_id": farm.poison,
            "unit_id": farm.unit["L"],
            "warehouse_id": farm.warehouse,
            "dose_per_ha": "1",
        }
    ]

    response = farm.operation([{"crop_cycle_id": cycle["id"]}], inputs=inputs)

    assert Decimal(response.json()["operation"]["inputs"][0]["quantity"]) == Decimal("1.2")


def test_operation_on_two_cycles_splits_by_area(farm: Farm) -> None:
    big, small = farm.cycle(area="1.2"), farm.cycle(area="0.8")

    farm.operation(
        [{"crop_cycle_id": big["id"]}, {"crop_cycle_id": small["id"]}],
        inputs=[
            {
                "product_id": farm.poison,
                "unit_id": farm.unit["L"],
                "warehouse_id": farm.warehouse,
                "quantity": "2",
            }
        ],
        assets=[{"asset_id": farm.tractor, "usage": "2"}],
    )

    big_cycle, small_cycle = farm.get_cycle(big["id"]), farm.get_cycle(small["id"])
    assert Decimal(big_cycle["input_cost"]) == Decimal("1200.00")
    assert Decimal(small_cycle["input_cost"]) == Decimal("800.00")
    assert Decimal(big_cycle["machinery_cost"]) == Decimal("6000.00")
    assert Decimal(small_cycle["machinery_cost"]) == Decimal("4000.00")


def test_machinery_keeps_rate_of_the_moment(farm: Farm) -> None:
    cycle = farm.cycle()
    farm.operation(
        [{"crop_cycle_id": cycle["id"]}],
        type_="Poda",
        assets=[{"asset_id": farm.tractor, "usage": "3"}],
    )

    farm.c.patch(f"/api/v1/assets/{farm.tractor}", json={"rate": "9000"})

    assert Decimal(farm.get_cycle(cycle["id"])["machinery_cost"]) == Decimal("15000.00")


def test_insufficient_stock_in_operation(farm: Farm) -> None:
    cycle = farm.cycle()

    response = farm.apply(cycle["id"], liters="50")

    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_operation_before_cycle_start_is_rejected(farm: Farm) -> None:
    cycle = farm.cycle(start=-5)

    response = farm.apply(cycle["id"])  # la labor es del día -10

    assert response.json()["error"]["code"] == "BEFORE_CYCLE"


def test_type_rules(farm: Farm) -> None:
    cycle = farm.cycle()

    pruning_with_inputs = farm.operation(
        [{"crop_cycle_id": cycle["id"]}],
        type_="Poda",
        inputs=[
            {
                "product_id": farm.poison,
                "unit_id": farm.unit["L"],
                "warehouse_id": farm.warehouse,
                "quantity": "1",
            }
        ],
    )
    harvest_without_data = farm.operation([{"crop_cycle_id": cycle["id"]}], type_="Cosecha")

    assert pruning_with_inputs.json()["error"]["code"] == "NO_INPUTS"
    assert harvest_without_data.json()["error"]["code"] == "HARVEST_REQUIRED"


def test_cancel_operation_returns_stock(farm: Farm) -> None:
    cycle = farm.cycle()
    operation = farm.apply(cycle["id"]).json()["operation"]

    response = farm.c.post(f"/api/v1/field-operations/{operation['id']}/cancel")

    assert response.json()["operation"]["status"] == "cancelled"
    assert farm.stock(farm.poison) == 10
    assert Decimal(farm.get_cycle(cycle["id"])["input_cost"]) == 0


def test_edit_operation_replaces_consumption(farm: Farm) -> None:
    cycle = farm.cycle()
    operation = farm.apply(cycle["id"], liters="2").json()["operation"]

    body = {
        "date": day(-10),
        "operation_type_id": farm.type["Aplicación"],
        "cycles": [{"crop_cycle_id": cycle["id"]}],
        "inputs": [
            {
                "product_id": farm.poison,
                "unit_id": farm.unit["L"],
                "warehouse_id": farm.warehouse,
                "quantity": "5",
            }
        ],
    }
    response = farm.c.put(f"/api/v1/field-operations/{operation['id']}", json=body)

    assert response.status_code == 200, response.json()
    assert farm.stock(farm.poison) == 5


# --- Cosecha ---


def test_harvest_enters_stock_with_batch_and_yield(farm: Farm) -> None:
    cycle = farm.cycle(area="1.2")
    farm.apply(cycle["id"], liters="2")

    response = farm.harvest(cycle["id"], boxes="10")

    harvest = response.json()["operation"]["harvest"]
    assert harvest["batch_code"].startswith("LOTE3-TOMATE-")
    assert farm.stock(farm.tomato) == 10  # cajones
    summary = farm.get_cycle(cycle["id"])
    assert Decimal(summary["harvested_quantity"]) == 10
    assert Decimal(summary["yield_per_ha"]) == Decimal("8.3333")  # 10 cajones / 1,2 ha
    assert Decimal(summary["cost_per_unit"]) == Decimal("200.00")  # $2.000 / 10 cajones


def test_field_book_lists_operations_in_order(farm: Farm) -> None:
    cycle = farm.cycle()
    farm.apply(cycle["id"])
    farm.harvest(cycle["id"])

    book = farm.c.get(f"/api/v1/crop-cycles/{cycle['id']}/field-book").json()

    assert [e["operation_type"] for e in book["entries"]] == ["Aplicación", "Cosecha"]
    assert Decimal(book["entries"][0]["inputs"][0]["cost"]) == Decimal("2000.00")


# --- Finalizar y reabrir ---


def test_finished_cycle_is_locked_and_costs_frozen(
    farm: Farm, client: TestClient, db: Session
) -> None:
    purchase = farm.c.get("/api/v1/stock-documents", params={"type": "manual_in"}).json()["items"][
        0
    ]
    cycle = farm.cycle()
    farm.apply(cycle["id"], liters="2")

    finish = farm.c.post(f"/api/v1/crop-cycles/{cycle['id']}/finish", json={"end_date": day(-1)})
    assert finish.json()["status"] == "finished"

    # Cambia el precio de la compra: el ciclo finalizado no cambia su costo
    farm.c.put(
        f"/api/v1/stock-documents/{purchase['id']}",
        json={
            "type": "manual_in",
            "date": day(-30),
            "warehouse_id": farm.warehouse,
            "lines": [
                {
                    "product_id": farm.poison,
                    "unit_id": farm.unit["L"],
                    "quantity": "10",
                    "unit_cost": "3000",
                }
            ],
        },
    )
    assert Decimal(farm.get_cycle(cycle["id"])["input_cost"]) == Decimal("2000.00")

    # No se pueden cargar más labores
    assert farm.apply(cycle["id"]).json()["error"]["code"] == "CYCLE_FINISHED"

    # El Dueño no puede reabrir; Soporte sí, y el costo vuelve a seguir al promedio
    reopen = f"/api/v1/crop-cycles/{cycle['id']}/reopen"
    assert farm.c.post(reopen, json={"reason": "Error"}).status_code == 403
    login_as(client, db, SUPPORT)
    assert client.post(reopen, json={"reason": "Faltó una labor"}).status_code == 200
    assert Decimal(farm.get_cycle(cycle["id"])["input_cost"]) == Decimal("6000.00")


def test_cannot_finish_before_last_operation(farm: Farm) -> None:
    cycle = farm.cycle(start=-20)
    farm.apply(cycle["id"])  # labor del día -10

    response = farm.c.post(f"/api/v1/crop-cycles/{cycle['id']}/finish", json={"end_date": day(-15)})

    assert response.json()["error"]["code"] == "CYCLE_END"
