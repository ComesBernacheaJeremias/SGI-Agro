import datetime as dt
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.core.schemas import Schema
from app.modules.commercial.models import (
    CashAccountKind,
    CashMovementKind,
    Direction,
    DocumentKind,
    LineKind,
    PaymentMethod,
    Status,
)
from app.modules.inventory.schemas import StockAlertOut

Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]
Positive = Annotated[Decimal, Field(gt=0)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class Ref(Schema):
    id: UUID
    name: str


class CodeRef(Schema):
    id: UUID
    code: str
    name: str


# --- Destino de un gasto (dimensiones) ---


class Destination(Schema):
    farm_id: UUID | None = None
    plot_id: UUID | None = None
    crop_cycle_id: UUID | None = None
    asset_id: UUID | None = None


class DestinationOut(Schema):
    farm: Ref | None
    plot: Ref | None
    crop_cycle: Ref | None
    asset: Ref | None


# --- Configuración ---


class ExpenseCategoryOut(Schema):
    id: UUID
    name: str
    is_active: bool


class ExpenseCategoryIn(Schema):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ExpenseCategoryUpdate(Schema):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None
    ) = None


class CashAccountOut(Schema):
    id: UUID
    name: str
    kind: CashAccountKind
    opening_balance: Decimal
    opening_date: date
    is_active: bool


class CashAccountIn(Schema):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    kind: CashAccountKind
    opening_balance: Decimal = Decimal(0)
    opening_date: date


class CashAccountUpdate(Schema):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None
    ) = None
    opening_balance: Decimal | None = None
    opening_date: date | None = None


# --- Comprobantes ---


class CommercialLineIn(Destination):
    kind: LineKind
    description: Short = ""
    product_id: UUID | None = None
    unit_id: UUID | None = None
    quantity: Positive = Decimal(1)
    batch_id: UUID | None = (
        None  # venta/NC de producción propia: partida (vacío = las más antiguas)
    )
    expense_category_id: UUID | None = None
    unit_price: Money
    vat_rate: Annotated[Decimal, Field(ge=0, le=100)] = Decimal(21)


class CommercialDocumentIn(Schema):
    direction: Direction
    kind: DocumentKind = DocumentKind.INVOICE
    has_invoice: bool = True
    letter: Annotated[
        str, StringConstraints(strip_whitespace=True, to_upper=True, max_length=1)
    ] = ""
    pos_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5)] = ""
    number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=8)] = ""
    party_id: UUID
    date: date
    due_date: dt.date | None = None  # por defecto: fecha + días de pago del tercero
    warehouse_id: UUID | None = None  # obligatorio si hay productos
    related_document_id: UUID | None = None  # NC/ND: comprobante que corrige
    other_taxes: Money = Decimal(0)
    notes: Text = ""
    lines: list[CommercialLineIn] = Field(min_length=1)


class CommercialLineOut(Schema):
    line_no: int
    kind: LineKind
    description: str
    product: CodeRef | None
    unit: Ref | None  # name = código de la unidad
    quantity: Decimal
    batch_id: UUID | None
    expense_category: Ref | None
    destination: DestinationOut
    unit_price: Decimal
    vat_rate: Decimal
    net_amount: Decimal
    vat_amount: Decimal


class CommercialDocumentSummaryOut(Schema):
    id: UUID
    direction: Direction
    kind: DocumentKind
    internal_number: str
    invoice_label: str
    has_invoice: bool
    party: Ref
    date: date
    due_date: dt.date
    status: Status
    total: Decimal
    allocated: Decimal  # cobrado/pagado
    credited: Decimal  # notas de crédito asociadas
    pending: Decimal


class CommercialDocumentOut(CommercialDocumentSummaryOut):
    letter: str
    pos_number: str
    number: str
    warehouse: Ref | None
    related_document: Ref | None  # name = etiqueta del comprobante
    net_total: Decimal
    vat_total: Decimal
    other_taxes: Decimal
    notes: str
    lines: list[CommercialLineOut]
    stock_document_id: UUID | None


class CommercialDocumentSavedOut(Schema):
    document: CommercialDocumentOut
    alerts: list[StockAlertOut]


# --- Cobros y pagos ---


class PaymentLineIn(Schema):
    method: PaymentMethod
    cash_account_id: UUID
    amount: Positive
    reference: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = ""


class AllocationIn(Schema):
    document_id: UUID
    amount: Positive


class PaymentIn(Schema):
    direction: Direction  # sale = cobro a cliente · purchase = pago a proveedor
    party_id: UUID
    date: date
    lines: list[PaymentLineIn] = Field(min_length=1)
    allocations: list[AllocationIn] = Field(default_factory=list)
    notes: Text = ""


class PaymentLineOut(Schema):
    method: PaymentMethod
    cash_account: Ref
    amount: Decimal
    reference: str


class AllocationOut(Schema):
    document_id: UUID
    invoice_label: str
    amount: Decimal


class PaymentOut(Schema):
    id: UUID
    direction: Direction
    number: str
    party: Ref
    date: date
    total: Decimal
    allocated: Decimal
    unallocated: Decimal  # anticipo / saldo a favor
    status: Status
    notes: str
    lines: list[PaymentLineOut]
    allocations: list[AllocationOut]


# --- Cuentas corrientes ---


class LedgerRowOut(Schema):
    date: date
    kind: str  # "document" | "payment"
    id: UUID
    label: str
    debit: Decimal  # aumenta el saldo (factura / nota de débito)
    credit: Decimal  # disminuye el saldo (cobro o pago / nota de crédito)
    balance: Decimal


class LedgerOut(Schema):
    party: Ref
    direction: Direction
    opening_balance: Decimal
    rows: list[LedgerRowOut]
    closing_balance: Decimal


class BalanceOut(Schema):
    party: Ref
    direction: Direction
    balance: Decimal  # cliente: nos debe · proveedor: le debemos
    overdue: Decimal
    days_0_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_over_90: Decimal
    advances: Decimal  # anticipos y NC sin aplicar


# --- Caja y bancos ---


class CashMovementIn(Destination):
    date: date
    kind: CashMovementKind
    cash_account_id: UUID
    target_account_id: UUID | None = None
    amount: Positive
    description: Short = ""
    expense_category_id: UUID | None = None


class CashMovementOut(Schema):
    id: UUID
    number: str
    date: date
    kind: CashMovementKind
    cash_account: Ref
    target_account: Ref | None
    amount: Decimal
    description: str
    expense_category: Ref | None
    destination: DestinationOut
    status: Status


class CashBalanceOut(Schema):
    account: Ref
    kind: CashAccountKind
    balance: Decimal


class CashStatementRowOut(Schema):
    date: date
    source: str  # "payment" | "movement"
    id: UUID
    label: str
    amount: Decimal  # + entra / − sale
    balance: Decimal


class CashStatementOut(Schema):
    account: Ref
    opening_balance: Decimal
    rows: list[CashStatementRowOut]
    closing_balance: Decimal
