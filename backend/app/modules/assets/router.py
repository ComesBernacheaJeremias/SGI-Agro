"""Activos: esquemas, reglas y endpoints (entidad simple sobre las piezas CRUD)."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import Field, StringConstraints

from app.core.crud import CrudRepository, CrudService
from app.core.crud_router import CrudPermissions, crud_router
from app.core.schemas import Schema
from app.modules.assets.maintenance_router import routers as maintenance_routers
from app.modules.assets.models import (
    ASSET_KIND_LABELS,
    ASSET_METER_LABELS,
    ASSET_STATUS_LABELS,
    Asset,
    AssetKind,
    AssetMeter,
    AssetStatus,
)
from app.modules.assets.permissions import ASSETS_DEACTIVATE, ASSETS_READ, ASSETS_WRITE
from app.modules.identity.dependencies import CurrentUser
from app.modules.masterdata.schemas import Option

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]


class AssetOut(Schema):
    id: UUID
    name: str
    kind: AssetKind
    brand: str
    model: str
    year: int | None
    identifier: str
    meter: AssetMeter
    rate: Decimal
    status: AssetStatus
    notes: str
    is_active: bool


class AssetCreate(Schema):
    name: Name
    kind: AssetKind
    brand: Short = ""
    model: Short = ""
    year: int | None = Field(default=None, ge=1900, le=2100)
    identifier: Short = ""
    meter: AssetMeter
    rate: Decimal = Field(default=Decimal(0), ge=0)
    status: AssetStatus = AssetStatus.OPERATIONAL
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class AssetUpdate(Schema):
    name: Name | None = None
    kind: AssetKind | None = None
    brand: Short | None = None
    model: Short | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    identifier: Short | None = None
    meter: AssetMeter | None = None
    rate: Decimal | None = Field(default=None, ge=0)
    status: AssetStatus | None = None
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class AssetOptions(Schema):
    kinds: list[Option]
    meters: list[Option]
    statuses: list[Option]


class AssetRepository(CrudRepository[Asset]):
    model = Asset
    search_fields = ("name", "brand", "model", "identifier")


class AssetService(CrudService[Asset, AssetCreate, AssetUpdate]):
    repository_class = AssetRepository
    unique_fields = {"name": "Ya existe el activo '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el activo."


def _asset_filters(
    kind: Annotated[AssetKind | None, Query()] = None,
    status: Annotated[AssetStatus | None, Query()] = None,
) -> dict[str, Any]:
    return {"kind": kind, "status": status}


def _options(labels: dict[Any, str]) -> list[Option]:
    return [Option(value=str(value), label=label) for value, label in labels.items()]


options_router = APIRouter(prefix="/api/v1/assets-options", tags=["assets"])


@options_router.get("")
def asset_options(_: CurrentUser) -> AssetOptions:
    return AssetOptions(
        kinds=_options(ASSET_KIND_LABELS),
        meters=_options(ASSET_METER_LABELS),
        statuses=_options(ASSET_STATUS_LABELS),
    )


routers = [
    *maintenance_routers,
    options_router,
    crud_router(
        prefix="/api/v1/assets",
        tag="assets",
        service=AssetService,
        out=AssetOut,
        create=AssetCreate,
        update=AssetUpdate,
        permissions=CrudPermissions(
            read=ASSETS_READ, write=ASSETS_WRITE, deactivate=ASSETS_DEACTIVATE
        ),
        filters=_asset_filters,
    ),
]
