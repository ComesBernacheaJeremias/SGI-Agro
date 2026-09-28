"""Tablero: un resumen por módulo, solo de lo que el usuario puede ver."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import DbSession
from app.core.schemas import Schema
from app.modules.assets.maintenance import PlanQueries
from app.modules.assets.permissions import ASSETS_READ
from app.modules.assets.schemas import PlanStatusOut
from app.modules.commercial.cash_service import CashQueries
from app.modules.commercial.ledger import LedgerQueries
from app.modules.commercial.models import Direction
from app.modules.commercial.permissions import CASH_READ, COMMERCIAL_READ
from app.modules.commercial.schemas import CashBalanceOut
from app.modules.costs.permissions import COSTS_READ
from app.modules.costs.schemas import ResultOut
from app.modules.costs.service import CostQueries
from app.modules.identity.authorization import effective_permissions
from app.modules.identity.dependencies import CurrentUser
from app.modules.inventory.permissions import INVENTORY_READ
from app.modules.inventory.queries import StockFilters, StockQueries
from app.modules.inventory.schemas import StockAlertOut
from app.modules.production.models import CropCycle, CycleStatus
from app.modules.production.permissions import PRODUCTION_READ
from app.modules.production.queries import ProductionQueries
from app.modules.production.schemas import CycleOut
from app.modules.production.valuation import own_produce_total

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
ZERO = Decimal(0)


class SeasonResult(Schema):
    name: str
    current: ResultOut  # temporada actual hasta hoy
    previous: ResultOut  # temporada anterior hasta la misma fecha


class CyclesSummary(Schema):
    active: int
    total_cost: Decimal
    top: list[CycleOut]  # los de mayor costo


class StockSummary(Schema):
    #: A costo contable (la producción propia cuenta cero)
    value: Decimal
    #: Producción propia valorizada por costo del ciclo: solo informativo (ADR-012)
    own_produce_value: Decimal
    own_produce_provisional: bool
    alerts: list[StockAlertOut]


class AccountsSummary(Schema):
    receivable: Decimal
    receivable_overdue: Decimal
    payable: Decimal
    payable_overdue: Decimal


class CashSummary(Schema):
    total: Decimal
    accounts: list[CashBalanceOut]


class DashboardOut(Schema):
    maintenance: list[PlanStatusOut] | None  # planes próximos o vencidos
    result: SeasonResult | None
    cycles: CyclesSummary | None
    stock: StockSummary | None
    accounts: AccountsSummary | None
    cash: CashSummary | None


def _season_start(day: date) -> date:
    """Temporada 1/7 → 30/6 (ADR-013)."""
    return date(day.year if day.month >= 7 else day.year - 1, 7, 1)


def _one_year_before(day: date) -> date:
    return (
        day.replace(year=day.year - 1, day=28)
        if (day.month, day.day) == (2, 29)
        else day.replace(year=day.year - 1)
    )


def _result(db: Session, today: date) -> SeasonResult:
    start = _season_start(today)
    queries = CostQueries(db)
    return SeasonResult(
        name=f"{start.year}/{str(start.year + 1)[2:]}",
        current=queries.management_result(start, today),
        previous=queries.management_result(_one_year_before(start), _one_year_before(today)),
    )


def _cycles(db: Session) -> CyclesSummary:
    cycles = list(db.scalars(select(CropCycle).where(CropCycle.status == CycleStatus.ACTIVE)))
    summaries = ProductionQueries(db).cycle_summaries(cycles)
    return CyclesSummary(
        active=len(summaries),
        total_cost=sum((s.total_cost for s in summaries), ZERO),
        top=sorted(summaries, key=lambda s: -s.total_cost)[:6],
    )


def _stock(db: Session) -> StockSummary:
    queries = StockQueries(db)
    own = own_produce_total(db)
    return StockSummary(
        value=queries.total_value(StockFilters()),
        own_produce_value=own.value,
        own_produce_provisional=own.provisional,
        alerts=queries.alerts(),
    )


def _accounts(db: Session) -> AccountsSummary:
    ledger = LedgerQueries(db)
    sales, purchases = ledger.balances(Direction.SALE), ledger.balances(Direction.PURCHASE)
    return AccountsSummary(
        receivable=sum((b.balance for b in sales), ZERO),
        receivable_overdue=sum((b.overdue for b in sales), ZERO),
        payable=sum((b.balance for b in purchases), ZERO),
        payable_overdue=sum((b.overdue for b in purchases), ZERO),
    )


def _cash(db: Session) -> CashSummary:
    balances = CashQueries(db).balances()
    return CashSummary(total=sum((b.balance for b in balances), ZERO), accounts=balances)


@router.get("")
def dashboard(db: DbSession, user: CurrentUser) -> DashboardOut:
    can = effective_permissions(user.role)
    today = date.today()
    return DashboardOut(
        maintenance=PlanQueries(db).alerts() if ASSETS_READ.code in can else None,
        result=_result(db, today) if COSTS_READ.code in can else None,
        cycles=_cycles(db) if PRODUCTION_READ.code in can else None,
        stock=_stock(db) if INVENTORY_READ.code in can else None,
        accounts=_accounts(db) if COMMERCIAL_READ.code in can else None,
        cash=_cash(db) if CASH_READ.code in can else None,
    )
