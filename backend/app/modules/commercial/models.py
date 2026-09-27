"""Comercial y caja (ADR-011: gestión sin contabilidad formal).

- CommercialDocument: comprobante de compra o venta (factura, nota de crédito o débito).
  Siempre tiene número interno (CPR-/VTA-); si hubo factura, además tipo/letra/PV/número.
  Líneas de producto (mueven stock) o de gasto (categoría + destino opcional).
- Payment: cobro (a un cliente) o pago (a un proveedor), con medios y cuentas de dinero.
  Se imputa a comprobantes (Allocation); lo no imputado es anticipo.
- CashAccount / CashMovement: cajas y bancos; movimientos que no son con un tercero
  (retiros, comisiones, transferencias entre cuentas, gastos pagados en efectivo).
Saldos (cuenta corriente, caja) siempre calculados.
"""

import datetime as dt
import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.formatting import format_money, format_quantity
from app.core.models import BaseModel
from app.modules.masterdata.models import Party, Product, Unit, Warehouse


def _enum(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


# --- Configuración ---


class ExpenseCategory(BaseModel):
    __tablename__ = "expense_categories"
    __label__ = "Categoría de gasto"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(80), unique=True, info={"label": "Nombre"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


class CashAccountKind(enum.StrEnum):
    CASH = "cash"
    BANK = "bank"


CASH_ACCOUNT_KIND_LABELS = {CashAccountKind.CASH: "Caja", CashAccountKind.BANK: "Banco"}


class CashAccount(BaseModel):
    __tablename__ = "cash_accounts"
    __label__ = "Cuenta de dinero"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(80), unique=True, info={"label": "Nombre"})
    kind: Mapped[CashAccountKind] = mapped_column(
        _enum(CashAccountKind, "cash_account_kind"),
        info={"label": "Tipo", "choices": CASH_ACCOUNT_KIND_LABELS},
    )
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=0, info={"label": "Saldo inicial"}
    )
    opening_date: Mapped[date] = mapped_column(Date, info={"label": "Fecha del saldo inicial"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


# --- Comprobantes ---


class Direction(enum.StrEnum):
    PURCHASE = "purchase"
    SALE = "sale"


class DocumentKind(enum.StrEnum):
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"


DOCUMENT_KIND_LABELS = {
    DocumentKind.INVOICE: "Factura",
    DocumentKind.CREDIT_NOTE: "Nota de crédito",
    DocumentKind.DEBIT_NOTE: "Nota de débito",
}


class Status(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


STATUS_LABELS = {Status.ACTIVE: "Vigente", Status.CANCELLED: "Anulado"}


class CommercialDocument(BaseModel):
    __tablename__ = "commercial_documents"
    __label__ = "Comprobante comercial"
    __display__ = "internal_number"

    direction: Mapped[Direction] = mapped_column(
        _enum(Direction, "commercial_direction"),
        info={"label": "Operación", "choices": {"purchase": "Compra", "sale": "Venta"}},
    )
    kind: Mapped[DocumentKind] = mapped_column(
        _enum(DocumentKind, "commercial_document_kind"),
        info={"label": "Tipo", "choices": DOCUMENT_KIND_LABELS},
    )
    internal_number: Mapped[str] = mapped_column(
        String(20), unique=True, info={"label": "Número interno"}
    )
    # Datos de la factura (si hubo): letra A/B/C, punto de venta y número
    has_invoice: Mapped[bool] = mapped_column(default=True, info={"label": "Con factura"})
    letter: Mapped[str] = mapped_column(String(1), default="", info={"label": "Letra"})
    pos_number: Mapped[str] = mapped_column(String(5), default="", info={"label": "Punto de venta"})
    number: Mapped[str] = mapped_column(String(8), default="", info={"label": "Número"})
    party_id: Mapped[UUID] = mapped_column(ForeignKey("parties.id"), info={"label": "Tercero"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    due_date: Mapped[dt.date] = mapped_column(Date, info={"label": "Vencimiento"})
    status: Mapped[Status] = mapped_column(
        _enum(Status, "commercial_status"),
        default=Status.ACTIVE,
        info={"label": "Estado", "choices": STATUS_LABELS},
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén"}
    )
    net_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, info={"label": "Neto"})
    vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, info={"label": "IVA"})
    other_taxes: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=0, info={"label": "Percepciones y otros"}
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, info={"label": "Total"})
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    # Saldo inicial de cuenta corriente (importado al arrancar): no es venta ni gasto
    is_opening_balance: Mapped[bool] = mapped_column(
        default=False, server_default="false", info={"label": "Saldo inicial"}
    )
    stock_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stock_documents.id"), info={"audit": False}
    )
    # NC/ND: comprobante que corrige. La NC se aplica sola a ese comprobante (baja su pendiente).
    related_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("commercial_documents.id"), index=True, info={"label": "Comprobante asociado"}
    )

    party: Mapped[Party] = relationship(lazy="joined")
    warehouse: Mapped[Warehouse | None] = relationship(lazy="joined")
    related_document: Mapped["CommercialDocument | None"] = relationship(
        remote_side="CommercialDocument.id", lazy="joined"
    )
    lines: Mapped[list["CommercialLine"]] = relationship(
        cascade="all, delete-orphan",
        order_by="CommercialLine.line_no",
        lazy="selectin",
        info={"label": "Líneas", "audit_key": "summary"},
    )

    @property
    def sign(self) -> int:
        """Efecto en la cuenta corriente: la nota de crédito resta."""
        return -1 if self.kind == DocumentKind.CREDIT_NOTE else 1

    @property
    def invoice_label(self) -> str:
        if self.is_opening_balance:
            return f"Saldo inicial {self.notes or self.internal_number}"
        if not self.has_invoice:
            return self.internal_number
        return f"{DOCUMENT_KIND_LABELS[self.kind]} {self.letter} {self.pos_number}-{self.number}"


class LineKind(enum.StrEnum):
    PRODUCT = "product"
    EXPENSE = "expense"


class CommercialLine(BaseModel):
    __tablename__ = "commercial_lines"
    __audited__ = False  # se registra en el historial del comprobante

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("commercial_documents.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int]
    kind: Mapped[LineKind] = mapped_column(_enum(LineKind, "commercial_line_kind"))
    description: Mapped[str] = mapped_column(String(200), default="")
    # Producto (mueve stock)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id"))
    unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1)
    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("batches.id")
    )  # venta: partida elegida
    # Gasto: categoría y destino opcional (sin destino = gasto de estructura)
    expense_category_id: Mapped[UUID | None] = mapped_column(ForeignKey("expense_categories.id"))
    farm_id: Mapped[UUID | None] = mapped_column(ForeignKey("farms.id"))
    plot_id: Mapped[UUID | None] = mapped_column(ForeignKey("plots.id"))
    crop_cycle_id: Mapped[UUID | None] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"), index=True)
    # Importes (precio unitario neto de IVA)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=21)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    product: Mapped[Product | None] = relationship(lazy="joined")
    unit: Mapped[Unit | None] = relationship(lazy="joined")
    expense_category: Mapped[ExpenseCategory | None] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        if self.kind == LineKind.PRODUCT and self.product and self.unit:
            what = f"{self.product.name}: {format_quantity(self.quantity)} {self.unit.code}"
        else:
            category = self.expense_category.name if self.expense_category else "Gasto"
            what = f"{category}: {self.description}".rstrip(": ")
        return f"{what} × {format_money(self.unit_price)} (IVA {format_quantity(self.vat_rate)}%)"


# --- Cobros y pagos ---


class PaymentMethod(enum.StrEnum):
    CASH = "cash"
    TRANSFER = "transfer"
    # CHEQUE = "cheque"  → cuando se sumen cheques (preparado: el medio es un catálogo)


PAYMENT_METHOD_LABELS = {PaymentMethod.CASH: "Efectivo", PaymentMethod.TRANSFER: "Transferencia"}


class Payment(BaseModel):
    """Cobro (dirección venta: el cliente paga) o pago (dirección compra: pagamos)."""

    __tablename__ = "payments"
    __label__ = "Cobro/Pago"
    __display__ = "number"

    direction: Mapped[Direction] = mapped_column(
        _enum(Direction, "commercial_direction"),
        info={"label": "Operación", "choices": {"purchase": "Pago", "sale": "Cobro"}},
    )
    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    party_id: Mapped[UUID] = mapped_column(ForeignKey("parties.id"), info={"label": "Tercero"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), info={"label": "Total"})
    status: Mapped[Status] = mapped_column(
        _enum(Status, "commercial_status"),
        default=Status.ACTIVE,
        info={"label": "Estado", "choices": STATUS_LABELS},
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})

    party: Mapped[Party] = relationship(lazy="joined")
    lines: Mapped[list["PaymentLine"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Medios", "audit_key": "summary"},
    )
    allocations: Mapped[list["Allocation"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Imputaciones", "audit_key": "summary"},
    )


class PaymentLine(BaseModel):
    __tablename__ = "payment_lines"
    __audited__ = False

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(_enum(PaymentMethod, "payment_method"))
    cash_account_id: Mapped[UUID] = mapped_column(ForeignKey("cash_accounts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    reference: Mapped[str] = mapped_column(String(60), default="")

    cash_account: Mapped[CashAccount] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        method = PAYMENT_METHOD_LABELS[self.method]
        return f"{method} ({self.cash_account.name}): {format_money(self.amount)}"


class Allocation(BaseModel):
    """Parte de un cobro/pago aplicada a un comprobante."""

    __tablename__ = "allocations"
    __audited__ = False

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("commercial_documents.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    document: Mapped[CommercialDocument] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.document.invoice_label}: {format_money(self.amount)}"


# --- Movimientos de caja ---


class CashMovementKind(enum.StrEnum):
    INCOME = "income"  # ingreso (aporte, cobro sin tercero, intereses…)
    EXPENSE = "expense"  # egreso / gasto (con categoría y destino)
    WITHDRAWAL = "withdrawal"  # retiro del dueño
    TRANSFER = "transfer"  # entre cuentas propias


CASH_MOVEMENT_KIND_LABELS = {
    CashMovementKind.INCOME: "Ingreso",
    CashMovementKind.EXPENSE: "Gasto",
    CashMovementKind.WITHDRAWAL: "Retiro",
    CashMovementKind.TRANSFER: "Transferencia entre cuentas",
}


class CashMovement(BaseModel):
    __tablename__ = "cash_movements"
    __label__ = "Movimiento de caja"
    __display__ = "number"

    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    kind: Mapped[CashMovementKind] = mapped_column(
        _enum(CashMovementKind, "cash_movement_kind"),
        info={"label": "Tipo", "choices": CASH_MOVEMENT_KIND_LABELS},
    )
    cash_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("cash_accounts.id"), index=True, info={"label": "Cuenta"}
    )
    target_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cash_accounts.id"), info={"label": "Cuenta destino"}
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), info={"label": "Importe"})
    description: Mapped[str] = mapped_column(String(200), default="", info={"label": "Descripción"})
    # Gasto: categoría y destino opcional
    expense_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("expense_categories.id"), info={"label": "Categoría"}
    )
    farm_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("farms.id"), info={"label": "Establecimiento"}
    )
    plot_id: Mapped[UUID | None] = mapped_column(ForeignKey("plots.id"), info={"label": "Lote"})
    crop_cycle_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crop_cycles.id"), index=True, info={"label": "Ciclo"}
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"), info={"label": "Activo"})
    status: Mapped[Status] = mapped_column(
        _enum(Status, "commercial_status"),
        default=Status.ACTIVE,
        info={"label": "Estado", "choices": STATUS_LABELS},
    )

    cash_account: Mapped[CashAccount] = relationship(foreign_keys=[cash_account_id], lazy="joined")
    target_account: Mapped[CashAccount | None] = relationship(
        foreign_keys=[target_account_id], lazy="joined"
    )
    expense_category: Mapped[ExpenseCategory | None] = relationship(lazy="joined")


Index("ix_commercial_documents_party", CommercialDocument.party_id, CommercialDocument.direction)
Index("ix_payments_party", Payment.party_id, Payment.direction)
