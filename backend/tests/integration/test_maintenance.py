"""Activos: lecturas y medidor estimado, planes con avisos, mantenimientos con repuestos,
ficha con costo real vs. tarifa, reporte y tablero."""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER
from tests.factories import login_as
from tests.integration.test_commercial import Shop, created, error_code
from tests.integration.test_production import day


class Workshop(Shop):
    """Tractor ($5.000/h) con lectura 1.000 h hace 20 días y una labor de 2 h hace 10 días;
    filtros de aceite en stock (10 × $1.500)."""

    def __init__(self, client: TestClient) -> None:
        super().__init__(client)
        created(
            client.post(
                "/api/v1/meter-readings",
                json={"asset_id": self.tractor, "date": day(-20), "value": "1000"},
            )
        )
        cycle = self.cycle()
        response = self.apply(cycle["id"], "1", assets=[{"asset_id": self.tractor, "usage": "2"}])
        assert response.status_code == 201, response.json()
        self.filter = self.post(
            "/api/v1/products", name="Filtro de aceite", type="input", unit_id=self.unit["un"]
        )["id"]
        line = {"kind": "product", "product_id": self.filter, "unit_id": self.unit["un"]}
        created(self.purchase([line | {"quantity": "10", "unit_price": "1500"}], number="900"))

    def plan(self, **body: Any) -> Any:
        return self.c.post(
            "/api/v1/maintenance-plans",
            json={"asset_id": self.tractor, "name": "Cambio de aceite"} | body,
        )

    def maintenance(self, **body: Any) -> Any:
        base = {"asset_id": self.tractor, "date": day(-1), "kind": "preventive"}
        return self.c.post("/api/v1/maintenances", json=base | body)

    def statuses(self) -> dict[str, Any]:
        rows = self.c.get(
            "/api/v1/maintenance-alerts/plans", params={"asset_id": self.tractor}
        ).json()
        return {r["plan"]["id"]: r for r in rows}


@pytest.fixture
def shop(client: TestClient, db: Session) -> Workshop:
    login_as(client, db, OWNER)
    return Workshop(client)


def test_current_reading_adds_usage_after_last_reading(shop: Workshop) -> None:
    sheet = shop.c.get(f"/api/v1/asset-sheets/{shop.tractor}").json()
    assert Decimal(sheet["current_reading"]) == Decimal(1002)
    assert sheet["last_reading_date"] == day(-20)
    assert sheet["unit"] == "horas"


def test_plan_states(shop: Workshop) -> None:
    ok = created(shop.plan(every_usage="250"))  # desde la lectura actual (1.002)
    upcoming = created(shop.plan(name="Engrase", every_usage="250", start_reading="760"))
    overdue = created(shop.plan(name="Filtros", every_months=6, start_date=day(-200)))
    states = shop.statuses()
    assert Decimal(states[ok["id"]]["remaining_usage"]) == Decimal(250)
    assert states[ok["id"]]["state"] == "ok"
    assert states[upcoming["id"]]["state"] == "upcoming"  # faltan 8 h (≤ 10 %)
    assert states[overdue["id"]]["state"] == "overdue"
    alerts = shop.c.get("/api/v1/maintenance-alerts").json()
    assert [a["plan"]["id"] for a in alerts] == [overdue["id"], upcoming["id"]]
    assert error_code(shop.plan(name="Sin intervalo")) == "PLAN_INTERVAL"


def test_maintenance_resets_plan_and_consumes_parts(shop: Workshop) -> None:
    plan = created(shop.plan(every_usage="250", start_reading="700"))
    assert shop.statuses()[plan["id"]]["state"] == "overdue"
    service = {
        "kind": "expense",
        "expense_category_id": shop.category["Reparaciones y repuestos"],
        "description": "Service",
        "unit_price": "3000",
        "asset_id": shop.tractor,
    }
    purchase = created(shop.purchase([service], number="901", warehouse_id=None))["document"]
    saved = created(
        shop.maintenance(
            plan_id=plan["id"],
            meter_reading="1002",
            warehouse_id=shop.warehouse,
            purchase_document_id=purchase["id"],
            parts=[{"product_id": shop.filter, "unit_id": shop.unit["un"], "quantity": "2"}],
        )
    )["maintenance"]
    assert saved["number"].startswith("MNT-")
    assert Decimal(saved["parts_cost"]) == Decimal(3000)
    assert Decimal(saved["purchase_cost"]) == Decimal(3000)
    assert shop.stock(shop.filter) == Decimal(8)
    status = shop.statuses()[plan["id"]]
    assert (status["state"], Decimal(status["due_reading"])) == ("ok", Decimal(1252))

    sheet = shop.c.get(f"/api/v1/asset-sheets/{shop.tractor}").json()
    costs = sheet["costs"]
    assert Decimal(costs["usage"]) == Decimal(2)
    assert Decimal(costs["rate_cost"]) == Decimal(10000)
    assert Decimal(costs["total"]) == Decimal(6000)  # service + repuestos
    assert Decimal(costs["real_rate"]) == Decimal(3000)

    report = shop.c.get("/api/v1/reports/asset_costs").json()
    assert Decimal(report["totals"]["total"]) == Decimal(6000)
    result = shop.c.get("/api/v1/reports/management_result").json()
    lines = {r["cells"]["label"]: Decimal(str(r["cells"]["amount"])) for r in result["rows"]}
    assert lines["Repuestos de mantenimientos"] == Decimal(-3000)

    created(shop.c.post(f"/api/v1/maintenances/{saved['id']}/cancel"))
    assert shop.stock(shop.filter) == Decimal(10)
    assert shop.statuses()[plan["id"]]["state"] == "overdue"


def test_maintenance_validations(shop: Workshop) -> None:
    other = shop.post("/api/v1/assets", name="Camioneta", kind="vehicle", meter="km", rate="300")[
        "id"
    ]
    plan = created(shop.plan(every_usage="250"))
    wrong_plan = shop.maintenance(asset_id=other, plan_id=plan["id"])
    assert error_code(wrong_plan) == "PLAN"
    no_warehouse = shop.maintenance(
        parts=[{"product_id": shop.filter, "unit_id": shop.unit["un"], "quantity": "1"}]
    )
    assert error_code(no_warehouse) == "WAREHOUSE_REQUIRED"


def test_dashboard_lists_pending_maintenance(shop: Workshop) -> None:
    created(shop.plan(every_months=1, start_date=day(-40)))
    board = shop.c.get("/api/v1/dashboard").json()
    assert [m["state"] for m in board["maintenance"]] == ["overdue"]
