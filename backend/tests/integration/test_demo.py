"""Los datos de ejemplo se cargan con las reglas reales y dejan reportes con contenido."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.demo import has_data, seed_demo
from app.modules.identity.authorization import OWNER
from tests.factories import login_as


def test_seed_demo(client: TestClient, db: Session) -> None:
    assert not has_data(db)
    seed_demo(db)
    assert has_data(db)
    login_as(client, db, OWNER)
    profitability = client.get("/api/v1/reports/profitability").json()
    assert len(profitability["rows"]) == 2
    tomato = next(r for r in profitability["rows"] if "Tomate" in r["cells"]["name"])
    assert Decimal(str(tomato["cells"]["revenue"])) > 0
    result = client.get("/api/v1/reports/management_result").json()
    assert result["rows"]
    alerts = client.get("/api/v1/maintenance-alerts").json()
    assert alerts  # el plan del tractor quedó próximo o vencido
