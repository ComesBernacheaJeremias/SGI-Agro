from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.core.crud_router import CrudPermissions, crud_router
from app.core.db import DbSession
from app.core.pagination import Page, Pagination, paginate
from app.modules.identity.authorization import require
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User
from app.modules.masterdata.schemas import Option
from app.modules.production.catalog import (
    CropCreate,
    CropOut,
    CropService,
    CropUpdate,
    FarmCreate,
    FarmOut,
    FarmService,
    FarmUpdate,
    OperationTypeCreate,
    OperationTypeOut,
    OperationTypeService,
    OperationTypeUpdate,
    PlotCreate,
    PlotOut,
    PlotService,
    PlotUpdate,
    SeasonOut,
    plot_filters,
)
from app.modules.production.models import (
    CROP_KIND_LABELS,
    CYCLE_STATUS_LABELS,
    PLOT_KIND_LABELS,
    CropCycle,
    CycleStatus,
    FieldOperation,
    FieldOperationCycle,
    OperationStatus,
    Plot,
    Season,
)
from app.modules.production.permissions import (
    PRODUCTION_CONFIG,
    PRODUCTION_READ,
    PRODUCTION_REOPEN,
    PRODUCTION_WRITE,
)
from app.modules.production.queries import ProductionQueries
from app.modules.production.schemas import (
    CycleCreate,
    CycleFinishIn,
    CycleOut,
    CycleReopenIn,
    CycleUpdate,
    FieldBookOut,
    OperationIn,
    OperationOut,
    OperationSavedOut,
    OperationSummaryOut,
)
from app.modules.production.service import CycleService, FieldOperationService

Reader = Annotated[User, require(PRODUCTION_READ)]
Writer = Annotated[User, require(PRODUCTION_WRITE)]
Reopener = Annotated[User, require(PRODUCTION_REOPEN)]

CATALOG = CrudPermissions(
    read=PRODUCTION_READ, write=PRODUCTION_CONFIG, deactivate=PRODUCTION_CONFIG
)


def _options(labels: dict[Any, str]) -> list[Option]:
    return [Option(value=str(k), label=v) for k, v in labels.items()]


misc_router = APIRouter(prefix="/api/v1/production", tags=["production"])


@misc_router.get("/options")
def production_options(_: CurrentUser) -> dict[str, list[Option]]:
    return {
        "plot_kinds": _options(PLOT_KIND_LABELS),
        "crop_kinds": _options(CROP_KIND_LABELS),
        "cycle_statuses": _options(CYCLE_STATUS_LABELS),
    }


@misc_router.get("/seasons")
def list_seasons(db: DbSession, _: Reader) -> list[SeasonOut]:
    seasons = db.scalars(select(Season).order_by(Season.start_date.desc()))
    return [SeasonOut.model_validate(s) for s in seasons]


# --- Ciclos ---

cycles_router = APIRouter(prefix="/api/v1/crop-cycles", tags=["production"])


@cycles_router.get("")
def list_cycles(
    db: DbSession,
    _: Reader,
    page: Pagination,
    status_: Annotated[CycleStatus | None, Query(alias="status")] = None,
    farm_id: UUID | None = None,
    plot_id: UUID | None = None,
    crop_id: UUID | None = None,
    season_id: UUID | None = None,
    q: str | None = None,
) -> Page[CycleOut]:
    query = select(CropCycle).join(Plot).order_by(CropCycle.start_date.desc(), CropCycle.name)
    if status_:
        query = query.where(CropCycle.status == status_)
    if farm_id:
        query = query.where(Plot.farm_id == farm_id)
    if plot_id:
        query = query.where(CropCycle.plot_id == plot_id)
    if crop_id:
        query = query.where(CropCycle.crop_id == crop_id)
    if season_id:
        query = query.where(CropCycle.season_id == season_id)
    if q:
        query = query.where(CropCycle.name.ilike(f"%{q.strip()}%"))
    items, total = paginate(db, query, page)
    return Page(
        items=ProductionQueries(db).cycle_summaries(items),
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


def _cycle_out(db: DbSession, cycle: CropCycle) -> CycleOut:
    return ProductionQueries(db).cycle_summaries([cycle])[0]


@cycles_router.get("/{id_}")
def get_cycle(id_: UUID, db: DbSession, _: Reader) -> CycleOut:
    return _cycle_out(db, CycleService(db).get(id_))


@cycles_router.get("/{id_}/field-book")
def field_book(id_: UUID, db: DbSession, _: Reader) -> FieldBookOut:
    cycle = CycleService(db).get(id_)
    return FieldBookOut(
        cycle=_cycle_out(db, cycle), entries=ProductionQueries(db).field_book(cycle)
    )


@cycles_router.post("", status_code=status.HTTP_201_CREATED)
def create_cycle(body: CycleCreate, db: DbSession, _: Writer) -> CycleOut:
    return _cycle_out(db, CycleService(db).create(body))


@cycles_router.patch("/{id_}")
def update_cycle(id_: UUID, body: CycleUpdate, db: DbSession, _: Writer) -> CycleOut:
    return _cycle_out(db, CycleService(db).update(id_, body))


@cycles_router.post("/{id_}/finish")
def finish_cycle(id_: UUID, body: CycleFinishIn, db: DbSession, _: Writer) -> CycleOut:
    return _cycle_out(db, CycleService(db).finish(id_, body.end_date))


@cycles_router.post("/{id_}/reopen")
def reopen_cycle(id_: UUID, body: CycleReopenIn, db: DbSession, _: Reopener) -> CycleOut:
    return _cycle_out(db, CycleService(db).reopen(id_, body.reason))


# --- Labores ---

operations_router = APIRouter(prefix="/api/v1/field-operations", tags=["production"])


def _saved(db: DbSession, result: tuple[FieldOperation, list[Any]]) -> OperationSavedOut:
    operation, alerts = result
    return OperationSavedOut(
        operation=ProductionQueries(db).operation_out(operation), alerts=alerts
    )


@operations_router.get("")
def list_operations(
    db: DbSession,
    _: Reader,
    page: Pagination,
    crop_cycle_id: UUID | None = None,
    operation_type_id: UUID | None = None,
    status_: Annotated[OperationStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[OperationSummaryOut]:
    query = select(FieldOperation).order_by(
        FieldOperation.date.desc(), FieldOperation.number.desc()
    )
    if crop_cycle_id:
        query = query.where(
            FieldOperation.id.in_(
                select(FieldOperationCycle.field_operation_id).where(
                    FieldOperationCycle.crop_cycle_id == crop_cycle_id
                )
            )
        )
    if operation_type_id:
        query = query.where(FieldOperation.operation_type_id == operation_type_id)
    if status_:
        query = query.where(FieldOperation.status == status_)
    if date_from:
        query = query.where(FieldOperation.date >= date_from)
    if date_to:
        query = query.where(FieldOperation.date <= date_to)
    items, total = paginate(db, query, page)
    queries = ProductionQueries(db)
    return Page(
        items=[queries.operation_summary(op) for op in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


@operations_router.get("/{id_}")
def get_operation(id_: UUID, db: DbSession, _: Reader) -> OperationOut:
    return ProductionQueries(db).operation_out(FieldOperationService(db).get(id_))


@operations_router.post("", status_code=status.HTTP_201_CREATED)
def create_operation(body: OperationIn, db: DbSession, _: Writer) -> OperationSavedOut:
    return _saved(db, FieldOperationService(db).create(body))


@operations_router.put("/{id_}")
def update_operation(id_: UUID, body: OperationIn, db: DbSession, _: Writer) -> OperationSavedOut:
    return _saved(db, FieldOperationService(db).update(id_, body))


@operations_router.post("/{id_}/cancel")
def cancel_operation(id_: UUID, db: DbSession, _: Writer) -> OperationSavedOut:
    return _saved(db, FieldOperationService(db).cancel(id_))


routers = [
    misc_router,
    cycles_router,
    operations_router,
    crud_router(
        prefix="/api/v1/farms",
        tag="production",
        service=FarmService,
        out=FarmOut,
        create=FarmCreate,
        update=FarmUpdate,
        permissions=CATALOG,
    ),
    crud_router(
        prefix="/api/v1/plots",
        tag="production",
        service=PlotService,
        out=PlotOut,
        create=PlotCreate,
        update=PlotUpdate,
        permissions=CATALOG,
        filters=plot_filters,
    ),
    crud_router(
        prefix="/api/v1/crops",
        tag="production",
        service=CropService,
        out=CropOut,
        create=CropCreate,
        update=CropUpdate,
        permissions=CATALOG,
    ),
    crud_router(
        prefix="/api/v1/operation-types",
        tag="production",
        service=OperationTypeService,
        out=OperationTypeOut,
        create=OperationTypeCreate,
        update=OperationTypeUpdate,
        permissions=CATALOG,
    ),
]
