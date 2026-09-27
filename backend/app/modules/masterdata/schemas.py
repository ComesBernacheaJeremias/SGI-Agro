from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.masterdata.models import ProductType, UnitKind, VatCondition, WarehouseKind

# Textos: se recortan espacios; los "Required*" no pueden quedar vacíos
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Required10 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
Required20 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Required40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Required80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Optional20 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]
CuitText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=13)]


class Option(Schema):
    value: str
    label: str


class MasterdataOptions(Schema):
    """Opciones de los desplegables (una sola fuente de las etiquetas en español)."""

    product_types: list[Option]
    unit_kinds: list[Option]
    vat_conditions: list[Option]
    warehouse_kinds: list[Option]
    vat_rates: list[Decimal]


# --- Unidades ---


class UnitOut(Schema):
    id: UUID
    code: str
    name: str
    kind: UnitKind
    factor: Decimal
    is_active: bool


class UnitCreate(Schema):
    code: Required10
    name: Required40
    kind: UnitKind
    factor: Decimal = Field(default=Decimal(1), gt=0)


class UnitUpdate(Schema):
    code: Required10 | None = None
    name: Required40 | None = None
    factor: Decimal | None = Field(default=None, gt=0)


class UnitRef(Schema):
    id: UUID
    code: str
    name: str
    kind: UnitKind


# --- Categorías ---


class CategoryOut(Schema):
    id: UUID
    name: str
    parent_id: UUID | None
    path: str  # "Insumos > Agroquímicos > Insecticidas"
    is_active: bool


class CategoryCreate(Schema):
    name: Name
    parent_id: UUID | None = None


class CategoryUpdate(Schema):
    name: Name | None = None
    parent_id: UUID | None = None


class CategoryRef(Schema):
    id: UUID
    name: str


# --- Productos ---


class ConversionIn(Schema):
    """1 unidad del producto = `quantity` de `unit_id` (ej. 1 cajón = 18 kg)."""

    unit_id: UUID
    quantity: Decimal = Field(gt=0)


class ConversionOut(Schema):
    unit: UnitRef
    quantity: Decimal


class ProductOut(Schema):
    id: UUID
    code: str
    name: str
    type: ProductType
    category: CategoryRef | None
    unit: UnitRef
    vat_rate: Decimal
    min_stock: Decimal | None
    notes: str
    conversions: list[ConversionOut]
    is_active: bool


class ProductCreate(Schema):
    code: Optional20 | None = None
    name: Name
    type: ProductType
    category_id: UUID | None = None
    unit_id: UUID
    vat_rate: Decimal = Field(default=Decimal(21), ge=0, le=100)
    min_stock: Decimal | None = Field(default=None, ge=0)
    notes: Text = ""
    conversions: list[ConversionIn] = Field(default_factory=list)


class ProductUpdate(Schema):
    code: Required20 | None = None
    name: Name | None = None
    type: ProductType | None = None
    category_id: UUID | None = None
    unit_id: UUID | None = None
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100)
    min_stock: Decimal | None = Field(default=None, ge=0)
    notes: Text | None = None
    conversions: list[ConversionIn] | None = None


# --- Clientes y proveedores ---


class PartyOut(Schema):
    id: UUID
    name: str
    trade_name: str
    cuit: str | None
    vat_condition: VatCondition
    is_customer: bool
    is_supplier: bool
    address: str
    city: str
    province: str
    phone: str
    email: str
    payment_days: int
    notes: str
    is_active: bool


class PartyCreate(Schema):
    name: Name
    trade_name: Text = ""
    cuit: CuitText | None = None
    vat_condition: VatCondition
    is_customer: bool = False
    is_supplier: bool = False
    address: Text = ""
    city: Text = ""
    province: Text = ""
    phone: Text = ""
    email: Text = ""
    payment_days: int = Field(default=0, ge=0, le=365)
    notes: Text = ""


class PartyUpdate(Schema):
    name: Name | None = None
    trade_name: Text | None = None
    cuit: CuitText | None = None
    vat_condition: VatCondition | None = None
    is_customer: bool | None = None
    is_supplier: bool | None = None
    address: Text | None = None
    city: Text | None = None
    province: Text | None = None
    phone: Text | None = None
    email: Text | None = None
    payment_days: int | None = Field(default=None, ge=0, le=365)
    notes: Text | None = None


# --- Almacenes ---


class WarehouseOut(Schema):
    id: UUID
    name: str
    kind: WarehouseKind
    location: str
    is_active: bool


class WarehouseCreate(Schema):
    name: Required80
    kind: WarehouseKind
    location: Text = ""


class WarehouseUpdate(Schema):
    name: Required80 | None = None
    kind: WarehouseKind | None = None
    location: Text | None = None
