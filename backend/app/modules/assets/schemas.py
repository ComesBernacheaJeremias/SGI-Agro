"""Esquemas de uso y mantenimiento de activos (F6)."""

import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.assets.models import MaintenanceKind, MaintenanceStatus
from app.modules.inventory.schemas import StockAlertOut

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Reading = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=1)]


class Ref(Schema):
    id: UUID
    name: str


# --- Lecturas ---


class ReadingOut(Schema):
    id: UUID
    asset_id: UUID
    date: dt.date
    value: Decimal
    notes: str
    is_active: bool


class ReadingCreate(Schema):
    asset_id: UUID
    date: dt.date
    value: Reading
    notes: Short = ""


class ReadingUpdate(Schema):
    date: dt.date | None = None
    value: Reading | None = None
    notes: Short | None = None


# --- Planes ---


class PlanOut(Schema):
    id: UUID
    asset_id: UUID
    name: str
    every_usage: Decimal | None
    every_months: int | None
    start_date: dt.date
    start_reading: Decimal
    is_active: bool


class PlanCreate(Schema):
    asset_id: UUID
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    every_usage: Annotated[Decimal, Field(gt=0)] | None = None
    every_months: Annotated[int, Field(gt=0, le=120)] | None = None
    start_date: dt.date | None = None  # vacío = hoy
    start_reading: Reading | None = None  # vacío = lectura actual estimada


class PlanUpdate(Schema):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None
    every_usage: Annotated[Decimal, Field(gt=0)] | None = None
    every_months: Annotated[int, Field(gt=0, le=120)] | None = None
    start_date: dt.date | None = None
    start_reading: Reading | None = None


PlanState = Literal["ok", "upcoming", "overdue"]


class PlanStatusOut(Schema):
    """Estado de un plan: cuándo toca el próximo y cuánto falta."""

    plan: PlanOut
    asset: Ref
    unit: str  # "horas" o "km"
    last_date: dt.date  # último mantenimiento (o inicio del plan)
    last_reading: Decimal
    due_reading: Decimal | None
    due_date: dt.date | None
    current_reading: Decimal
    remaining_usage: Decimal | None
    remaining_days: int | None
    state: PlanState


# --- Mantenimientos ---


class PartIn(Schema):
    product_id: UUID
    unit_id: UUID
    quantity: Annotated[Decimal, Field(gt=0)]


class MaintenanceIn(Schema):
    asset_id: UUID
    date: dt.date
    kind: MaintenanceKind
    plan_id: UUID | None = None
    description: Text = ""
    meter_reading: Reading | None = None
    warehouse_id: UUID | None = None  # obligatorio si hay repuestos
    purchase_document_id: UUID | None = None
    parts: list[PartIn] = Field(default_factory=list)


class CodeRef(Schema):
    id: UUID
    code: str
    name: str


class PartOut(Schema):
    product: CodeRef
    unit: Ref  # name = código
    quantity: Decimal
    cost: Decimal


class MaintenanceOut(Schema):
    id: UUID
    number: str
    asset: Ref
    date: dt.date
    kind: MaintenanceKind
    plan: Ref | None
    description: str
    meter_reading: Decimal | None
    warehouse: Ref | None
    purchase_document: Ref | None  # name = comprobante
    purchase_cost: Decimal  # gastos de esa compra con destino = este activo
    parts: list[PartOut]
    parts_cost: Decimal
    status: MaintenanceStatus
    stock_document_id: UUID | None


class MaintenanceSavedOut(Schema):
    maintenance: MaintenanceOut
    alerts: list[StockAlertOut]


# --- Ficha ---


class AmountRow(Schema):
    name: str
    amount: Decimal


class AssetCostOut(Schema):
    """Uso y costos de un activo en un período."""

    usage: Decimal  # horas/km de labores
    rate_cost: Decimal  # lo cargado a los ciclos por tarifa
    expenses: Decimal  # compras y caja con destino = activo
    parts: Decimal  # repuestos de mantenimientos
    total: Decimal  # gastos reales
    real_rate: Decimal | None  # total / uso
    rate: Decimal  # tarifa configurada


class AssetSheetOut(Schema):
    asset: Ref
    unit: str
    date_from: dt.date
    date_to: dt.date
    current_reading: Decimal
    last_reading_date: dt.date | None
    costs: AssetCostOut
    expenses_by_category: list[AmountRow]
    plans: list[PlanStatusOut]
    maintenances: list[MaintenanceOut]
    readings: list[ReadingOut]
