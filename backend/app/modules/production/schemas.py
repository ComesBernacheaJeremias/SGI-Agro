from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.assets.models import AssetMeter
from app.modules.inventory.schemas import StockAlertOut
from app.modules.production.models import CycleStatus, OperationStatus

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Positive = Annotated[Decimal, Field(gt=0)]


class Ref(Schema):
    id: UUID
    name: str


class CodeRef(Schema):
    id: UUID
    code: str
    name: str


# --- Ciclos ---


class CycleCreate(Schema):
    plot_id: UUID
    crop_id: UUID
    area_ha: Positive
    start_date: date
    expected_end_date: date | None = None
    notes: Text = ""


class CycleUpdate(Schema):
    area_ha: Positive | None = None
    start_date: date | None = None
    expected_end_date: date | None = None
    notes: Text | None = None


class CycleFinishIn(Schema):
    end_date: date


class CycleReopenIn(Schema):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class CycleOut(Schema):
    id: UUID
    name: str
    farm: Ref
    plot: Ref
    crop: Ref
    season: Ref
    area_ha: Decimal
    start_date: date
    expected_end_date: date | None
    end_date: date | None
    status: CycleStatus
    notes: str
    reopen_reason: str
    # Resumen de costos y cosecha
    input_cost: Decimal
    machinery_cost: Decimal
    expense_cost: Decimal  # servicios y otros gastos (compras y caja con destino = ciclo)
    total_cost: Decimal
    harvested_quantity: Decimal
    harvest_unit: str
    yield_per_ha: Decimal | None
    cost_per_ha: Decimal
    cost_per_unit: Decimal | None


# --- Labores ---


class CycleShareIn(Schema):
    crop_cycle_id: UUID
    # Superficie trabajada en el ciclo (por defecto, la del ciclo)
    area_ha: Positive | None = None


class InputIn(Schema):
    product_id: UUID
    unit_id: UUID
    warehouse_id: UUID
    # Cantidad total, o dosis por hectárea (el sistema calcula el total)
    quantity: Positive | None = None
    dose_per_ha: Positive | None = None


class AssetUseIn(Schema):
    asset_id: UUID
    usage: Positive  # horas o km


class HarvestIn(Schema):
    product_id: UUID | None = None  # por defecto, el producto del cultivo
    unit_id: UUID
    quantity: Positive
    warehouse_id: UUID
    is_final: bool = False


class OperationIn(Schema):
    # El dispositivo genera el id: reintentar el guardado no duplica (ADR-024)
    id: UUID | None = None
    date: date
    operation_type_id: UUID
    cycles: list[CycleShareIn] = Field(min_length=1)
    inputs: list[InputIn] = Field(default_factory=list)
    assets: list[AssetUseIn] = Field(default_factory=list)
    harvest: HarvestIn | None = None
    notes: Text = ""


class OperationCycleOut(Schema):
    crop_cycle_id: UUID
    name: str
    area_ha: Decimal
    status: CycleStatus


class OperationInputOut(Schema):
    product: CodeRef
    unit_id: UUID
    unit: str
    warehouse: Ref
    quantity: Decimal
    dose_per_ha: Decimal | None
    cost: Decimal


class OperationAssetOut(Schema):
    asset: Ref
    meter: AssetMeter
    usage: Decimal
    rate: Decimal
    cost: Decimal


class HarvestOut(Schema):
    product: CodeRef
    unit_id: UUID
    unit: str
    quantity: Decimal
    warehouse: Ref
    is_final: bool
    batch_code: str | None


class OperationSummaryOut(Schema):
    id: UUID
    number: str
    date: date
    operation_type: Ref
    is_harvest: bool
    cycles: list[str]
    status: OperationStatus
    total_cost: Decimal


class OperationOut(Schema):
    id: UUID
    number: str
    date: date
    operation_type: Ref
    is_harvest: bool
    status: OperationStatus
    notes: str
    total_area_ha: Decimal
    cycles: list[OperationCycleOut]
    inputs: list[OperationInputOut]
    assets: list[OperationAssetOut]
    harvest: HarvestOut | None
    stock_document_id: UUID | None
    editable: bool
    total_cost: Decimal


class OperationSavedOut(Schema):
    operation: OperationOut
    alerts: list[StockAlertOut]


# --- Cuaderno de campo ---


class FieldBookInput(Schema):
    product: str
    quantity: Decimal  # parte de este ciclo
    unit: str
    dose_per_ha: Decimal | None
    cost: Decimal


class FieldBookAsset(Schema):
    asset: str
    usage: Decimal  # parte de este ciclo
    unit: str
    cost: Decimal


class FieldBookEntry(Schema):
    id: UUID
    number: str
    date: date
    operation_type: str
    is_harvest: bool
    area_ha: Decimal
    inputs: list[FieldBookInput]
    assets: list[FieldBookAsset]
    harvest_quantity: Decimal | None
    harvest_unit: str | None
    batch_code: str | None
    cost: Decimal
    notes: str


class FieldBookOut(Schema):
    cycle: CycleOut
    entries: list[FieldBookEntry]
