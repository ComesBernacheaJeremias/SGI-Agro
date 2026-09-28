"""Costos, rentabilidad, resultado de gestión, reportes (pantalla/Excel/PDF) y tablero."""

from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, STAFF
from tests.factories import login_as
from tests.integration.test_commercial import Shop, created
from tests.integration.test_production import day


class Season(Shop):
    """Un ciclo con insumos, maquinaria, un servicio y ventas; reventa; gasto de estructura.

    - Insumos: 2 L × $1.000 = 2.000 · Maquinaria: 2 h × $5.000 = 10.000 (tarifa)
    - Servicio con destino al ciclo: 30.000 · Cosecha 10 cajones, venta de 6 × $10.000
    - Reventa: compra 10 × $100, venta 4 × $250 · Estructura: 5.000 por caja
    """

    def __init__(self, client: TestClient) -> None:
        super().__init__(client)
        self.cycle_id = self.cycle()["id"]
        response = self.apply(self.cycle_id, "2", assets=[{"asset_id": self.tractor, "usage": "2"}])
        assert response.status_code == 201, response.json()
        service = {
            "kind": "expense",
            "expense_category_id": self.category["Servicios contratados"],
            "description": "Poda",
            "unit_price": "30000",
            "crop_cycle_id": self.cycle_id,
        }
        created(self.purchase([service], number="500", warehouse_id=None))
        assert self.harvest(self.cycle_id, "10").status_code == 201
        created(self.sale("6"))
        self.goods = self.post(
            "/api/v1/products", name="Bolsas", type="resale", unit_id=self.unit["un"]
        )["id"]
        goods = {"kind": "product", "product_id": self.goods, "unit_id": self.unit["un"]}
        created(self.purchase([goods | {"quantity": "10", "unit_price": "100"}], number="501"))
        created(
            self.sale(
                "1",
                lines=[goods | {"quantity": "4", "unit_price": "250", "vat_rate": "21"}],
            )
        )
        movement = {
            "date": day(-1),
            "kind": "expense",
            "cash_account_id": self.cash,
            "amount": "5000",
            "expense_category_id": self.category["Seguros"],
        }
        created(client.post("/api/v1/cash/movements", json=movement))

    def report(self, key: str, **params: Any) -> Any:
        response = self.c.get(f"/api/v1/reports/{key}", params=params)
        assert response.status_code == 200, response.json()
        return response.json()


@pytest.fixture
def season(client: TestClient, db: Session) -> Season:
    login_as(client, db, OWNER)
    return Season(client)


def money(value: Any) -> Decimal:
    return Decimal(str(value))


def test_cycle_cost_detail(season: Season) -> None:
    detail = season.c.get(f"/api/v1/costs/cycles/{season.cycle_id}").json()
    cycle = detail["cycle"]
    assert money(cycle["input_cost"]) == 2000
    assert money(cycle["machinery_cost"]) == 10000
    assert money(cycle["expense_cost"]) == 30000
    assert money(cycle["total_cost"]) == 42000
    assert money(detail["revenue"]) == 60000
    assert money(detail["margin"]) == 18000
    assert money(detail["margin_per_ha"]) == 15000  # 1,2 ha
    assert [(r["name"], money(r["amount"])) for r in detail["inputs"]] == [
        ("Insecticida", Decimal(2000))
    ]
    assert [(r["name"], money(r["amount"])) for r in detail["expenses"]] == [
        ("Servicios contratados", Decimal(30000))
    ]
    assert [money(r["quantity"]) for r in detail["sales"]] == [6]


def test_profitability_by_cycle_and_crop(season: Season) -> None:
    report = season.report("profitability")
    row = report["rows"][0]
    assert row["link"] == {"kind": "cycle", "id": season.cycle_id}
    assert money(row["cells"]["revenue"]) == 60000
    assert money(row["cells"]["margin"]) == 18000
    assert money(row["cells"]["margin_pct"]) == 30
    by_crop = season.report("profitability", group_by="crop")
    assert by_crop["rows"][0]["cells"]["name"] == "Tomate perita"


def test_management_result_uses_real_expenses_not_machinery_rate(season: Season) -> None:
    report = season.report("management_result")
    lines = {r["cells"]["label"]: money(r["cells"]["amount"]) for r in report["rows"]}
    assert lines["Ventas netas"] == 61000
    assert lines["Costo de lo vendido (reventa y elaborados)"] == -400
    assert lines["Costos de producción"] == -32000  # insumos + servicio (sin tarifa)
    assert lines["Gastos de estructura"] == -5000
    assert lines["Resultado"] == 23600


def test_expenses_structure_and_plot_costs(season: Season) -> None:
    structure = season.report("expenses", scope="structure", group_by="detail")
    assert money(structure["totals"]["amount"]) == 5000
    assert structure["rows"][0]["link"]["kind"] == "cash_movement"
    plots = season.report("plot_costs")
    assert money(plots["totals"]["total"]) == 42000


def test_product_margin(season: Season) -> None:
    report = season.report("product_margin", product_type="resale")
    row = report["rows"][0]["cells"]
    assert (money(row["revenue"]), money(row["cost"]), money(row["margin"])) == (
        Decimal(1000),
        Decimal(400),
        Decimal(600),
    )


def test_commercial_reports(season: Season) -> None:
    sales = season.report("sales")
    assert money(sales["totals"]["net"]) == 61000
    by_product = season.report("sales", group_by="product")
    assert {r["cells"]["name"] for r in by_product["rows"]} == {"Tomate perita", "Bolsas"}
    book = season.report("accountant", direction="purchase")
    assert money(book["totals"]["net_21"]) == 31000  # servicio + reventa
    assert season.report("balances", direction="sale")["rows"]
    stock = season.report("stock_valued")
    assert money(stock["totals"]["value"]) == Decimal("8600")  # 8 L × 1.000 + 6 bolsas × 100


def test_cash_statement_requires_account(season: Season) -> None:
    response = season.c.get("/api/v1/reports/cash_statement")
    assert response.status_code == 409
    report = season.report("cash_statement", cash_account_id=season.cash)
    assert money(report["totals"]["balance"]) == 95000


def test_exports(season: Season) -> None:
    xlsx = season.c.get("/api/v1/reports/management_result/export", params={"format": "xlsx"})
    assert xlsx.status_code == 200
    assert "attachment" in xlsx.headers["content-disposition"]
    sheet = load_workbook(BytesIO(xlsx.content)).active
    assert sheet is not None and sheet["A1"].value == "Resultado de gestión"
    pdf = season.c.get("/api/v1/reports/profitability/export", params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_dashboard(season: Season) -> None:
    board = season.c.get("/api/v1/dashboard").json()
    assert money(board["result"]["current"]["result"]) == 23600
    assert board["cycles"]["active"] == 1
    assert money(board["accounts"]["receivable"]) > 0
    assert money(board["cash"]["total"]) == 95000


def test_catalog_starts_with_profitability(season: Season) -> None:
    groups = [r["group"] for r in season.c.get("/api/v1/reports").json()]
    assert list(dict.fromkeys(groups)) == [
        "Costos y rentabilidad",
        "Comercial y caja",
        "Inventario",
        "Activos",
    ]


def test_staff_does_not_see_costs(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF)
    keys = {r["key"] for r in client.get("/api/v1/reports").json()}
    assert "sales" in keys and "profitability" not in keys
    assert client.get("/api/v1/reports/profitability").status_code == 403
    assert client.get("/api/v1/dashboard").json()["result"] is None
