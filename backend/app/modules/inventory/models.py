"""Inventario en tres niveles:

- StockDocument: comprobante (cabecera): tipo, número, fecha, almacén(es), estado.
- StockDocumentLine: lo que cargó el usuario (producto, cantidad y unidad, costo). Va al historial.
- StockMove: libro de stock en unidad base, con signo y costo. Lo calcula el sistema; es la
  fuente del stock, el kardex y los costos. Lleva las dimensiones de costo (ADR-005).
"""

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.formatting import format_money, format_quantity
from app.core.models import BaseModel
from app.modules.masterdata.models import Party, Product, Unit, Warehouse


class DocumentType(enum.StrEnum):
    MANUAL_IN = "manual_in"  # ingreso
    MANUAL_OUT = "manual_out"  # egreso
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    # Generados por otros módulos (se editan desde su origen)
    PURCHASE = "purchase"
    SALE = "sale"
    CONSUMPTION = "consumption"
    HARVEST = "harvest"
    PRODUCTION = "production"


DOCUMENT_TYPE_LABELS = {
    DocumentType.MANUAL_IN: "Ingreso",
    DocumentType.MANUAL_OUT: "Egreso",
    DocumentType.TRANSFER: "Transferencia",
    DocumentType.ADJUSTMENT: "Ajuste",
    DocumentType.PURCHASE: "Compra",
    DocumentType.SALE: "Venta",
    DocumentType.CONSUMPTION: "Consumo",
    DocumentType.HARVEST: "Cosecha",
    DocumentType.PRODUCTION: "Elaboración",
}

# Prefijo de numeración por tipo
DOCUMENT_PREFIXES = {
    DocumentType.MANUAL_IN: "ING",
    DocumentType.MANUAL_OUT: "EGR",
    DocumentType.TRANSFER: "TRF",
    DocumentType.ADJUSTMENT: "AJU",
    DocumentType.PURCHASE: "RCP",  # recepción (el comprobante comercial es CPR-)
    DocumentType.SALE: "DSP",  # despacho (el comprobante comercial es VTA-)
    DocumentType.CONSUMPTION: "CON",
    DocumentType.HARVEST: "COS",
    DocumentType.PRODUCTION: "ELA",
}

MANUAL_TYPES = {
    DocumentType.MANUAL_IN,
    DocumentType.MANUAL_OUT,
    DocumentType.TRANSFER,
    DocumentType.ADJUSTMENT,
}


class DocumentStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


STATUS_LABELS = {DocumentStatus.ACTIVE: "Vigente", DocumentStatus.CANCELLED: "Anulado"}


class CostMode(enum.StrEnum):
    OWN = "own"  # entrada con costo propio (ingreso, compra): mueve el promedio
    AVERAGE = "average"  # toma el costo promedio vigente (salidas, transferencias, ajustes)
    # Entrada cuyo costo es lo consumido en el mismo comprobante (elaboración)
    DERIVED = "derived"


def _enum(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


class StockDocument(BaseModel):
    __tablename__ = "stock_documents"
    __label__ = "Comprobante de stock"
    __display__ = "number"

    type: Mapped[DocumentType] = mapped_column(
        _enum(DocumentType, "stock_document_type"),
        info={"label": "Tipo", "choices": DOCUMENT_TYPE_LABELS},
    )
    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    status: Mapped[DocumentStatus] = mapped_column(
        _enum(DocumentStatus, "stock_document_status"),
        default=DocumentStatus.ACTIVE,
        info={"label": "Estado", "choices": STATUS_LABELS},
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén"}
    )
    target_warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén destino"}
    )
    party_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parties.id"), info={"label": "Proveedor/Cliente"}
    )
    reference: Mapped[str] = mapped_column(
        String(60), default="", info={"label": "Comprobante de referencia"}
    )
    reason: Mapped[str] = mapped_column(String(120), default="", info={"label": "Motivo"})
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    # Documentos generados por otro módulo (compra, venta, labor…): se editan desde su origen
    source_module: Mapped[str | None] = mapped_column(String(30), info={"audit": False})
    source_id: Mapped[UUID | None] = mapped_column(info={"audit": False})

    warehouse: Mapped[Warehouse] = relationship(foreign_keys=[warehouse_id], lazy="joined")
    target_warehouse: Mapped[Warehouse | None] = relationship(
        foreign_keys=[target_warehouse_id], lazy="joined"
    )
    party: Mapped[Party | None] = relationship(lazy="joined")
    lines: Mapped[list["StockDocumentLine"]] = relationship(
        cascade="all, delete-orphan",
        order_by="StockDocumentLine.line_no",
        lazy="selectin",
        info={"label": "Líneas", "audit_key": "summary"},
    )

    @property
    def is_manual(self) -> bool:
        return self.type in MANUAL_TYPES


class StockDocumentLine(BaseModel):
    """Renglón tal como lo cargó el usuario (en la unidad que eligió)."""

    __tablename__ = "stock_document_lines"
    __audited__ = False  # se registra dentro del historial del comprobante

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("stock_documents.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int]
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"))
    # Cantidad cargada (en ajustes: la cantidad contada)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    # Unidades base por cada unidad cargada (2 cajones × 18 = 36 kg → factor 18)
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    # Costo por unidad cargada (solo ingresos)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))

    product: Mapped[Product] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        text = f"{self.product.name}: {format_quantity(self.quantity)} {self.unit.code}"
        if self.unit_cost is not None:
            text += f" × {format_money(self.unit_cost)}"
        return text


class StockMove(BaseModel):
    """Movimiento de stock en unidad base (+ entra / − sale). Lo calcula el sistema."""

    __tablename__ = "stock_moves"
    __audited__ = False  # derivado de las líneas; el historial está en el comprobante

    document_id: Mapped[UUID] = mapped_column(ForeignKey("stock_documents.id", ondelete="CASCADE"))
    line_no: Mapped[int]
    # Orden dentro de la línea (transferencia: 0 = salida, 1 = entrada)
    sub_no: Mapped[int] = mapped_column(default=0)
    date: Mapped[date] = mapped_column(Date)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_mode: Mapped[CostMode] = mapped_column(_enum(CostMode, "stock_cost_mode"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    # Costo promedio y stock total del producto después de este movimiento (para el kardex)
    avg_cost_after: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    cancelled: Mapped[bool] = mapped_column(default=False)
    # Costo congelado (movimientos de ciclos finalizados, F3): el recálculo no lo cambia
    frozen: Mapped[bool] = mapped_column(default=False)

    # Dimensiones de costo (ADR-005)
    farm_id: Mapped[UUID | None] = mapped_column(ForeignKey("farms.id"))
    plot_id: Mapped[UUID | None] = mapped_column(ForeignKey("plots.id"))
    crop_cycle_id: Mapped[UUID | None] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    field_operation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("field_operations.id"), index=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"))
    batch_id: Mapped[UUID | None] = mapped_column(ForeignKey("batches.id"), index=True)


# Consultas por producto en orden cronológico (recálculo, kardex) y stock por almacén
Index(
    "ix_stock_moves_product_order",
    StockMove.product_id,
    StockMove.date,
    StockMove.document_id,
    StockMove.line_no,
    StockMove.sub_no,
)
Index("ix_stock_moves_product_warehouse", StockMove.product_id, StockMove.warehouse_id)
Index("ix_stock_moves_document", StockMove.document_id)
