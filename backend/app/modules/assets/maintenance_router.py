"""Endpoints de uso y mantenimiento: lecturas, planes, mantenimientos, avisos y ficha."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.core.crud import CrudRepository, CrudService
from app.core.crud_router import CrudPermissions, crud_router
from app.core.db import DbSession
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.pagination import Page, Pagination
from app.modules.assets.maintenance import (
    MaintenanceService,
    MeterQueries,
    PlanQueries,
    asset_costs,
    unit_of,
)
from app.modules.assets.models import (
    Asset,
    Maintenance,
    MaintenancePlan,
    MaintenanceStatus,
    MeterReading,
)
from app.modules.assets.permissions import ASSETS_READ, ASSETS_WRITE
from app.modules.assets.schemas import (
    AmountRow,
    AssetCostOut,
    AssetSheetOut,
    CodeRef,
    MaintenanceIn,
    MaintenanceOut,
    MaintenanceSavedOut,
    PartOut,
    PlanCreate,
    PlanOut,
    PlanStatusOut,
    PlanUpdate,
    ReadingCreate,
    ReadingOut,
    ReadingUpdate,
    Ref,
)
from app.modules.commercial.expenses import expense_rows
from app.modules.commercial.models import CommercialLine, ExpenseCategory
from app.modules.identity.authorization import require
from app.modules.identity.models import User
from app.modules.inventory.models import StockMove
from app.modules.inventory.schemas import StockAlertOut

Reader = Annotated[User, require(ASSETS_READ)]
Writer = Annotated[User, require(ASSETS_WRITE)]
ZERO = Decimal(0)


# --- Lecturas y planes (piezas CRUD) ---


class ReadingRepository(CrudRepository[MeterReading]):
    model = MeterReading
    default_sort = "date"


class ReadingService(CrudService[MeterReading, ReadingCreate, ReadingUpdate]):
    repository_class = ReadingRepository
    not_found_message = "No se encontró la lectura."

    def validate(self, obj: MeterReading) -> None:
        super().validate(obj)
        if obj.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")


class PlanRepository(CrudRepository[MaintenancePlan]):
    model = MaintenancePlan


class PlanService(CrudService[MaintenancePlan, PlanCreate, PlanUpdate]):
    repository_class = PlanRepository
    not_found_message = "No se encontró el plan."

    def values_for_create(self, data: PlanCreate) -> dict[str, Any]:
        values = data.model_dump()
        values["start_date"] = data.start_date or date.today()
        if data.start_reading is None:
            values["start_reading"] = MeterQueries(self.session).reading_at(
                data.asset_id, values["start_date"]
            )
        return values

    def validate(self, obj: MaintenancePlan) -> None:
        super().validate(obj)
        if not obj.every_usage and not obj.every_months:
            raise BusinessRuleError(
                "Indicá cada cuántas horas/km o cada cuántos meses.", code="PLAN_INTERVAL"
            )
        if self.session.get(Asset, obj.asset_id) is None:
            raise NotFoundError("No se encontró el activo.")


def _asset_filter(asset_id: Annotated[UUID | None, Query()] = None) -> dict[str, Any]:
    return {"asset_id": asset_id}


# --- Presentación ---


def maintenance_out(db: DbSession, m: Maintenance) -> MaintenanceOut:
    moves = (
        db.scalars(select(StockMove).where(StockMove.document_id == m.stock_document_id)).all()
        if m.stock_document_id
        else []
    )
    part_cost = {mv.line_no: -mv.total_cost for mv in moves if not mv.cancelled}
    purchase_cost = ZERO
    if m.purchase_document_id:
        purchase_cost = Decimal(
            db.scalar(
                select(func.sum(CommercialLine.net_amount)).where(
                    CommercialLine.document_id == m.purchase_document_id,
                    CommercialLine.asset_id == m.asset_id,
                )
            )
            or 0
        )
    parts = [
        PartOut(
            product=CodeRef(id=p.product.id, code=p.product.code, name=p.product.name),
            unit=Ref(id=p.unit.id, name=p.unit.code),
            quantity=p.quantity,
            cost=part_cost.get(p.line_no, ZERO),
        )
        for p in m.parts
    ]
    doc = m.purchase_document
    return MaintenanceOut(
        id=m.id,
        number=m.number,
        asset=Ref(id=m.asset.id, name=m.asset.name),
        date=m.date,
        kind=m.kind,
        plan=Ref(id=m.plan.id, name=m.plan.name) if m.plan else None,
        description=m.description,
        meter_reading=m.meter_reading,
        warehouse=Ref(id=m.warehouse.id, name=m.warehouse.name) if m.warehouse else None,
        purchase_document=Ref(id=doc.id, name=doc.invoice_label) if doc else None,
        purchase_cost=purchase_cost,
        parts=parts,
        parts_cost=sum((p.cost for p in parts), ZERO),
        status=m.status,
        stock_document_id=m.stock_document_id,
    )


def _saved(db: DbSession, m: Maintenance, alerts: list[StockAlertOut]) -> MaintenanceSavedOut:
    return MaintenanceSavedOut(maintenance=maintenance_out(db, m), alerts=alerts)


# --- Mantenimientos ---

maintenances_router = APIRouter(prefix="/api/v1/maintenances", tags=["assets"])


@maintenances_router.get("")
def list_maintenances(
    db: DbSession,
    _: Reader,
    page: Pagination,
    asset_id: UUID | None = None,
    status_: Annotated[MaintenanceStatus | None, Query(alias="status")] = None,
) -> Page[MaintenanceOut]:
    items, total = MaintenanceService(db).search(asset_id, status_, page)
    return Page(
        items=[maintenance_out(db, m) for m in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


@maintenances_router.get("/{id_}")
def get_maintenance(id_: UUID, db: DbSession, _: Reader) -> MaintenanceOut:
    return maintenance_out(db, MaintenanceService(db).get(id_))


@maintenances_router.post("", status_code=status.HTTP_201_CREATED)
def create_maintenance(body: MaintenanceIn, db: DbSession, _: Writer) -> MaintenanceSavedOut:
    return _saved(db, *MaintenanceService(db).create(body))


@maintenances_router.put("/{id_}")
def update_maintenance(
    id_: UUID, body: MaintenanceIn, db: DbSession, _: Writer
) -> MaintenanceSavedOut:
    return _saved(db, *MaintenanceService(db).update(id_, body))


@maintenances_router.post("/{id_}/cancel")
def cancel_maintenance(id_: UUID, db: DbSession, _: Writer) -> MaintenanceSavedOut:
    return _saved(db, *MaintenanceService(db).cancel(id_))


# --- Avisos y ficha ---

alerts_router = APIRouter(prefix="/api/v1/maintenance-alerts", tags=["assets"])


@alerts_router.get("")
def maintenance_alerts(db: DbSession, _: Reader) -> list[PlanStatusOut]:
    """Planes próximos o vencidos (campana, tablero)."""
    return PlanQueries(db).alerts()


@alerts_router.get("/plans")
def plan_statuses(db: DbSession, _: Reader, asset_id: UUID | None = None) -> list[PlanStatusOut]:
    """Estado de todos los planes activos (o los de un activo)."""
    return PlanQueries(db).statuses(asset_id)


sheets_router = APIRouter(prefix="/api/v1/asset-sheets", tags=["assets"])


@sheets_router.get("/{id_}")
def asset_sheet(
    id_: UUID,
    db: DbSession,
    _: Reader,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AssetSheetOut:
    """Ficha: lectura actual, costos reales vs. tarifa, planes, mantenimientos y lecturas."""
    asset = db.get(Asset, id_)
    if asset is None:
        raise NotFoundError("No se encontró el activo.")
    date_to = date_to or date.today()
    date_from = date_from or date_to - timedelta(days=365)
    cost = asset_costs(db, date_from, date_to, [asset.id]).get(asset.id)
    meter = MeterQueries(db)
    last = meter.last_reading(asset.id, date.today())

    e = expense_rows()
    by_category = db.execute(
        select(ExpenseCategory.name, func.sum(e.c.amount))
        .select_from(e)
        .outerjoin(ExpenseCategory, ExpenseCategory.id == e.c.category_id)
        .where(e.c.asset_id == asset.id, e.c.date >= date_from, e.c.date <= date_to)
        .group_by(ExpenseCategory.name)
    ).all()
    expenses = [AmountRow(name=r[0] or "Sin categoría", amount=Decimal(r[1])) for r in by_category]
    if cost and cost.parts:
        expenses.append(AmountRow(name="Repuestos (mantenimientos)", amount=cost.parts))

    maintenances = db.scalars(
        select(Maintenance)
        .where(Maintenance.asset_id == asset.id)
        .order_by(Maintenance.date.desc(), Maintenance.number.desc())
        .limit(50)
    ).all()
    readings = db.scalars(
        select(MeterReading)
        .where(MeterReading.asset_id == asset.id, MeterReading.is_active.is_(True))
        .order_by(MeterReading.date.desc())
        .limit(50)
    ).all()
    return AssetSheetOut(
        asset=Ref(id=asset.id, name=asset.name),
        unit=unit_of(asset),
        date_from=date_from,
        date_to=date_to,
        current_reading=meter.reading_at(asset.id, date.today()),
        last_reading_date=last[0] if last else None,
        costs=AssetCostOut(
            usage=cost.usage if cost else ZERO,
            rate_cost=cost.rate_cost if cost else ZERO,
            expenses=cost.expenses if cost else ZERO,
            parts=cost.parts if cost else ZERO,
            total=cost.total if cost else ZERO,
            real_rate=cost.real_rate if cost else None,
            rate=asset.rate,
        ),
        expenses_by_category=sorted(expenses, key=lambda r: -r.amount),
        plans=PlanQueries(db).statuses(asset.id),
        maintenances=[maintenance_out(db, m) for m in maintenances],
        readings=[ReadingOut.model_validate(r) for r in readings],
    )


routers = [
    maintenances_router,
    alerts_router,
    sheets_router,
    crud_router(
        prefix="/api/v1/meter-readings",
        tag="assets",
        service=ReadingService,
        out=ReadingOut,
        create=ReadingCreate,
        update=ReadingUpdate,
        permissions=CrudPermissions(read=ASSETS_READ, write=ASSETS_WRITE, deactivate=ASSETS_WRITE),
        filters=_asset_filter,
    ),
    crud_router(
        prefix="/api/v1/maintenance-plans",
        tag="assets",
        service=PlanService,
        out=PlanOut,
        create=PlanCreate,
        update=PlanUpdate,
        permissions=CrudPermissions(read=ASSETS_READ, write=ASSETS_WRITE, deactivate=ASSETS_WRITE),
        filters=_asset_filter,
    ),
]
