"""Elaboración (ADR-014).

- Receta: una por producto elaborado (semielaborado o terminado). Componentes: insumos y/o
  semielaborados (varios niveles, sin ciclos). Rinde `yield_quantity` en `yield_unit`.
- Preparación: ejecución de una receta (un nivel). Guarda las cantidades realmente usadas,
  así editar la receta no cambia preparaciones pasadas. Genera un comprobante de stock
  "Elaboración": salida de componentes + entrada del producto con costo derivado.
"""

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.formatting import format_quantity
from app.core.models import BaseModel
from app.modules.masterdata.models import Product, Unit, Warehouse


class Recipe(BaseModel):
    __tablename__ = "recipes"
    __label__ = "Receta"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(150), info={"label": "Nombre"})
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"), unique=True, info={"label": "Producto elaborado"}
    )
    yield_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), info={"label": "Rinde"})
    yield_unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), info={"label": "Unidad"})
    instructions: Mapped[str] = mapped_column(Text, default="", info={"label": "Instrucciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    product: Mapped[Product] = relationship(lazy="joined")
    yield_unit: Mapped[Unit] = relationship(lazy="joined")
    components: Mapped[list["RecipeComponent"]] = relationship(
        cascade="all, delete-orphan",
        order_by="RecipeComponent.line_no",
        lazy="selectin",
        info={"label": "Componentes", "audit_key": "summary"},
    )


class RecipeComponent(BaseModel):
    __tablename__ = "recipe_components"
    __audited__ = False

    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int]
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    product: Mapped[Product] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.product.name}: {format_quantity(self.quantity)} {self.unit.code}"


class OrderStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class ProductionOrder(BaseModel):
    __tablename__ = "production_orders"
    __label__ = "Preparación"
    __display__ = "number"

    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id"), info={"label": "Receta"})
    # Cantidad preparada, en la unidad de rinde de la receta
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), info={"label": "Cantidad"})
    components_warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén de componentes"}
    )
    target_warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén destino"}
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="production_order_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=OrderStatus.ACTIVE,
        info={"label": "Estado", "choices": {"active": "Vigente", "cancelled": "Anulada"}},
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    # Preparación "madre" cuando esta se generó con "Preparar lo que falta"
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_orders.id"), info={"audit": False}
    )
    stock_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stock_documents.id"), info={"audit": False}
    )

    recipe: Mapped[Recipe] = relationship(lazy="joined")
    components_warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[components_warehouse_id], lazy="joined"
    )
    target_warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[target_warehouse_id], lazy="joined"
    )
    lines: Mapped[list["ProductionOrderLine"]] = relationship(
        cascade="all, delete-orphan",
        order_by="ProductionOrderLine.line_no",
        lazy="selectin",
        info={"label": "Componentes usados", "audit_key": "summary"},
    )


class ProductionOrderLine(BaseModel):
    """Componente realmente usado en la preparación."""

    __tablename__ = "production_order_lines"
    __audited__ = False

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_orders.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int]
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    product: Mapped[Product] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.product.name}: {format_quantity(self.quantity)} {self.unit.code}"
