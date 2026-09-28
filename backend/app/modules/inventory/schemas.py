from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.inventory.models import DocumentStatus, DocumentType
from app.modules.masterdata.schemas import Option

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class Ref(Schema):
    id: UUID
    name: str


class ProductRef(Schema):
    id: UUID
    code: str
    name: str


class UnitCode(Schema):
    id: UUID
    code: str


# --- Entrada ---


class LineIn(Schema):
    product_id: UUID
    unit_id: UUID
    # Cantidad (en ajustes: cantidad contada, puede ser 0)
    quantity: Decimal = Field(ge=0)
    # Costo por unidad cargada: obligatorio en ingresos, ignorado en el resto
    unit_cost: Decimal | None = Field(default=None, ge=0)


class DocumentIn(Schema):
    # El dispositivo genera el id: reintentar el guardado no duplica (ADR-024)
    id: UUID | None = None
    type: DocumentType
    date: date
    warehouse_id: UUID
    target_warehouse_id: UUID | None = None
    party_id: UUID | None = None
    reference: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = ""
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    notes: Text = ""
    lines: list[LineIn] = Field(min_length=1)


# --- Salida ---


class LineOut(Schema):
    line_no: int
    product: ProductRef
    unit: UnitCode
    quantity: Decimal
    unit_cost: Decimal | None
    base_unit: str
    base_quantity: Decimal  # cantidad cargada en unidad base
    moved_quantity: Decimal  # lo que movió el stock (en ajustes: la diferencia)
    total_cost: Decimal


class DocumentSummaryOut(Schema):
    id: UUID
    type: DocumentType
    number: str
    date: date
    status: DocumentStatus
    warehouse: Ref
    target_warehouse: Ref | None
    party: Ref | None
    reference: str
    is_manual: bool
    line_count: int


class DocumentOut(DocumentSummaryOut):
    reason: str
    notes: str
    lines: list[LineOut]


class StockAlertOut(Schema):
    """Producto en su stock mínimo o por debajo: "Necesitás comprar"."""

    product: ProductRef
    unit: str
    quantity: Decimal
    min_stock: Decimal
    missing: Decimal


class DocumentSavedOut(Schema):
    document: DocumentOut
    alerts: list[StockAlertOut]


class BatchStockOut(Schema):
    """Partida con stock (cantidad en la unidad base del producto)."""

    id: UUID
    code: str
    date: date
    quantity: Decimal


class StockRowOut(Schema):
    product: ProductRef
    unit: str
    warehouse: Ref | None  # None = total de todos los almacenes
    quantity: Decimal
    avg_cost: Decimal
    value: Decimal
    min_stock: Decimal | None
    below_min: bool


class KardexRowOut(Schema):
    date: date
    document_id: UUID
    document_type: DocumentType
    document_number: str
    warehouse: Ref
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    balance: Decimal  # saldo acumulado (del almacén filtrado, o total)
    avg_cost_after: Decimal


class KardexOut(Schema):
    product: ProductRef
    unit: str
    opening_balance: Decimal
    rows: list[KardexRowOut]
    closing_balance: Decimal


class InventoryOptions(Schema):
    document_types: list[Option]
    statuses: list[Option]
