from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.inventory.schemas import StockAlertOut
from app.modules.manufacturing.models import OrderStatus

Positive = Annotated[Decimal, Field(gt=0)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class Ref(Schema):
    id: UUID
    name: str


class ProductRef(Schema):
    id: UUID
    code: str
    name: str


class UnitRef(Schema):
    id: UUID
    code: str


# --- Recetas ---


class ComponentIn(Schema):
    product_id: UUID
    unit_id: UUID
    quantity: Positive


class RecipeCreate(Schema):
    product_id: UUID
    yield_quantity: Positive
    yield_unit_id: UUID
    instructions: Text = ""
    components: list[ComponentIn] = Field(min_length=1)


class RecipeUpdate(Schema):
    yield_quantity: Positive | None = None
    yield_unit_id: UUID | None = None
    instructions: Text | None = None
    components: list[ComponentIn] | None = Field(default=None, min_length=1)


class ComponentOut(Schema):
    product: ProductRef
    product_type: str
    unit: UnitRef
    quantity: Decimal
    has_recipe: bool  # semielaborado con receta propia (se puede "preparar lo que falta")


class RecipeOut(Schema):
    id: UUID
    name: str
    product: ProductRef
    yield_quantity: Decimal
    yield_unit: UnitRef
    instructions: str
    components: list[ComponentOut]
    estimated_cost: Decimal  # con los costos promedio actuales, por unidad de rinde
    is_active: bool


# --- Preparaciones ---


class OrderLineIn(Schema):
    product_id: UUID
    unit_id: UUID
    quantity: Positive


class OrderIn(Schema):
    # El dispositivo genera el id: reintentar el guardado no duplica (ADR-024)
    id: UUID | None = None
    date: date
    recipe_id: UUID
    quantity: Positive
    components_warehouse_id: UUID
    target_warehouse_id: UUID
    # Cantidades reales usadas; si no se envían, se escalan desde la receta
    lines: list[OrderLineIn] | None = None
    # Preparar antes los semielaborados que falten (recursivo)
    prepare_missing: bool = False
    notes: Text = ""


class OrderCheckIn(Schema):
    date: date
    recipe_id: UUID
    quantity: Positive
    components_warehouse_id: UUID


class ComponentCheckOut(Schema):
    product: ProductRef
    unit: str  # unidad base
    required: Decimal
    available: Decimal
    missing: Decimal
    can_prepare: bool


class OrderLineOut(Schema):
    product: ProductRef
    unit: UnitRef
    quantity: Decimal
    cost: Decimal


class OrderOut(Schema):
    id: UUID
    number: str
    date: date
    recipe: Ref
    product: ProductRef
    quantity: Decimal
    unit: UnitRef
    components_warehouse: Ref
    target_warehouse: Ref
    status: OrderStatus
    notes: str
    lines: list[OrderLineOut]
    total_cost: Decimal
    unit_cost: Decimal
    parent_id: UUID | None
    stock_document_id: UUID | None


class OrderSavedOut(Schema):
    order: OrderOut
    # Preparaciones creadas automáticamente con "Preparar lo que falta"
    prepared: list[OrderOut]
    alerts: list[StockAlertOut]
