"""Catálogos de producción: establecimientos, lotes, cultivos, tipos de labor y temporadas."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import Query
from pydantic import Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.crud import CrudRepository, CrudService
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.schemas import Schema
from app.modules.masterdata.models import Product, ProductType
from app.modules.production.models import (
    Crop,
    CropCycle,
    CropKind,
    CycleStatus,
    Farm,
    OperationType,
    Plot,
    PlotKind,
    Season,
)

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Area = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class Ref(Schema):
    id: UUID
    name: str


# --- Establecimientos ---


class FarmOut(Schema):
    id: UUID
    name: str
    location: str
    area_ha: Decimal | None
    notes: str
    is_active: bool


class FarmCreate(Schema):
    name: Name
    location: Text = ""
    area_ha: Area | None = None
    notes: Text = ""


class FarmUpdate(Schema):
    name: Name | None = None
    location: Text | None = None
    area_ha: Area | None = None
    notes: Text | None = None


class FarmRepository(CrudRepository[Farm]):
    model = Farm
    search_fields = ("name", "location")


class FarmService(CrudService[Farm, FarmCreate, FarmUpdate]):
    repository_class = FarmRepository
    unique_fields = {"name": "Ya existe el establecimiento '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el establecimiento."


# --- Lotes ---


class PlotOut(Schema):
    id: UUID
    farm: Ref
    name: str
    area_ha: Decimal
    kind: PlotKind
    notes: str
    is_active: bool


class PlotCreate(Schema):
    farm_id: UUID
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    area_ha: Area
    kind: PlotKind
    notes: Text = ""


class PlotUpdate(Schema):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)] | None
    ) = None
    area_ha: Area | None = None
    kind: PlotKind | None = None
    notes: Text | None = None


class PlotRepository(CrudRepository[Plot]):
    model = Plot
    search_fields = ("name",)


def active_cycles_area(
    session: Session, plot_id: UUID, exclude_cycle: UUID | None = None
) -> Decimal:
    """Hectáreas ocupadas por ciclos en curso en un lote."""
    query = select(func.coalesce(func.sum(CropCycle.area_ha), 0)).where(
        CropCycle.plot_id == plot_id, CropCycle.status == CycleStatus.ACTIVE
    )
    if exclude_cycle:
        query = query.where(CropCycle.id != exclude_cycle)
    return Decimal(session.scalar(query) or 0)


class PlotService(CrudService[Plot, PlotCreate, PlotUpdate]):
    repository_class = PlotRepository
    not_found_message = "No se encontró el lote."

    def validate(self, obj: Plot) -> None:
        super().validate(obj)
        farm = self.session.get(Farm, obj.farm_id)
        if farm is None:
            raise NotFoundError("No se encontró el establecimiento.")
        query = select(Plot.id).where(
            Plot.farm_id == obj.farm_id, func.lower(Plot.name) == obj.name.lower()
        )
        if obj.id:
            query = query.where(Plot.id != obj.id)
        if self.session.scalar(query) is not None:
            raise BusinessRuleError(
                f"Ya existe el lote '{obj.name}' en {farm.name}.", code="DUPLICATE"
            )
        if obj.id and obj.area_ha < active_cycles_area(self.session, obj.id):
            raise BusinessRuleError(
                "La superficie no puede ser menor a la ocupada por los cultivos en curso.",
                code="PLOT_AREA",
            )


# --- Cultivos ---


class CropOut(Schema):
    id: UUID
    name: str
    species: str
    variety: str
    kind: CropKind
    harvest_product: Ref
    is_active: bool


class CropCreate(Schema):
    species: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    variety: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = ""
    kind: CropKind
    harvest_product_id: UUID


class CropUpdate(Schema):
    species: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)] | None
    ) = None
    variety: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None
    kind: CropKind | None = None
    harvest_product_id: UUID | None = None


class CropRepository(CrudRepository[Crop]):
    model = Crop
    search_fields = ("name",)


class CropService(CrudService[Crop, CropCreate, CropUpdate]):
    repository_class = CropRepository
    unique_fields = {"name": "Ya existe el tipo de cultivo '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el tipo de cultivo."

    def validate(self, obj: Crop) -> None:
        obj.name = f"{obj.species} {obj.variety}".strip()
        super().validate(obj)
        product = self.session.get(Product, obj.harvest_product_id)
        if product is None or product.type != ProductType.OWN_PRODUCE:
            raise BusinessRuleError(
                "El producto que se cosecha tiene que ser de tipo 'Producción propia'.",
                code="HARVEST_PRODUCT",
            )


# --- Tipos de labor ---


class OperationTypeOut(Schema):
    id: UUID
    name: str
    uses_inputs: bool
    uses_assets: bool
    is_harvest: bool
    is_active: bool


class OperationTypeCreate(Schema):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    uses_inputs: bool = False
    uses_assets: bool = True
    is_harvest: bool = False


class OperationTypeUpdate(Schema):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)] | None
    ) = None
    uses_inputs: bool | None = None
    uses_assets: bool | None = None
    is_harvest: bool | None = None


class OperationTypeRepository(CrudRepository[OperationType]):
    model = OperationType
    search_fields = ("name",)


class OperationTypeService(CrudService[OperationType, OperationTypeCreate, OperationTypeUpdate]):
    repository_class = OperationTypeRepository
    unique_fields = {"name": "Ya existe el tipo de labor '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el tipo de labor."

    def validate(self, obj: OperationType) -> None:
        super().validate(obj)
        if obj.is_harvest and obj.uses_inputs:
            raise BusinessRuleError(
                "Una cosecha no consume insumos: cargalos en una labor aparte.",
                code="HARVEST_INPUTS",
            )


# --- Temporadas ---


class SeasonOut(Schema):
    id: UUID
    name: str
    start_date: date
    end_date: date


def season_for(session: Session, day: date) -> Season:
    """Temporada (1/7 → 30/6) que contiene `day`; si no existe, se crea."""
    season = session.scalar(select(Season).where(Season.start_date <= day, Season.end_date >= day))
    if season is not None:
        return season
    start_year = day.year if day.month >= 7 else day.year - 1
    start = date(start_year, 7, 1)
    season = Season(
        name=f"{start_year}/{str(start_year + 1)[2:]}",
        start_date=start,
        end_date=date(start_year + 1, 7, 1) - timedelta(days=1),
    )
    session.add(season)
    session.flush()
    return season


def plot_filters(farm_id: Annotated[UUID | None, Query()] = None) -> dict[str, Any]:
    return {"farm_id": farm_id}


def report_period(
    session: Session, date_from: date | None, date_to: date | None, season_id: UUID | None
) -> tuple[date | None, date | None]:
    """Período de un reporte: la temporada elegida o las fechas."""
    if season_id is None:
        return date_from, date_to
    season = session.get(Season, season_id)
    if season is None:
        raise NotFoundError("No se encontró la temporada.")
    return season.start_date, season.end_date
