"""Producción (ADR-013): establecimiento → lote → ciclo productivo → labores y cosechas.

- Temporada: período 1/7 → 30/6 igual para toda la empresa; se crea sola cuando hace falta.
- Ciclo: un cultivo en (parte de) un lote entre dos fechas. Acumula costos. Al finalizarlo
  se congelan sus costos (movimientos de stock `frozen`); solo Soporte lo reabre.
- Labor: trabajo en uno o varios ciclos (insumos y horas se reparten por superficie).
  Si el tipo de labor es cosecha: un solo ciclo, ingresa producto al stock con una partida.
"""

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.formatting import format_money, format_quantity
from app.core.models import BaseModel
from app.modules.assets.models import Asset
from app.modules.masterdata.models import Product, Unit, Warehouse


def _enum(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


# --- Establecimientos y lotes ---


class Farm(BaseModel):
    __tablename__ = "farms"
    __label__ = "Establecimiento"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(100), unique=True, info={"label": "Nombre"})
    location: Mapped[str] = mapped_column(String(200), default="", info={"label": "Ubicación"})
    area_ha: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), info={"label": "Superficie (ha)"}
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


class PlotKind(enum.StrEnum):
    OPEN_FIELD = "open_field"
    GREENHOUSE = "greenhouse"
    FOREST = "forest"


PLOT_KIND_LABELS = {
    PlotKind.OPEN_FIELD: "Campo abierto",
    PlotKind.GREENHOUSE: "Invernadero",
    PlotKind.FOREST: "Forestal",
}


class Plot(BaseModel):
    __tablename__ = "plots"
    __table_args__ = (UniqueConstraint("farm_id", "name"),)
    __label__ = "Lote"
    __display__ = "name"

    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), info={"label": "Establecimiento"})
    name: Mapped[str] = mapped_column(String(60), info={"label": "Nombre"})
    area_ha: Mapped[Decimal] = mapped_column(Numeric(12, 2), info={"label": "Superficie (ha)"})
    kind: Mapped[PlotKind] = mapped_column(
        _enum(PlotKind, "plot_kind"), info={"label": "Tipo", "choices": PLOT_KIND_LABELS}
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    farm: Mapped[Farm] = relationship(lazy="joined")


# --- Cultivos y tipos de labor ---


class CropKind(enum.StrEnum):
    FRUIT = "fruit"
    VEGETABLE = "vegetable"
    FOREST = "forest"


CROP_KIND_LABELS = {
    CropKind.FRUIT: "Fruta",
    CropKind.VEGETABLE: "Hortaliza",
    CropKind.FOREST: "Forestal",
}


class Crop(BaseModel):
    __tablename__ = "crops"
    __label__ = "Cultivo"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(120), unique=True, info={"label": "Nombre"})
    species: Mapped[str] = mapped_column(String(60), info={"label": "Especie"})
    variety: Mapped[str] = mapped_column(String(60), default="", info={"label": "Variedad"})
    kind: Mapped[CropKind] = mapped_column(
        _enum(CropKind, "crop_kind"), info={"label": "Tipo", "choices": CROP_KIND_LABELS}
    )
    harvest_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"), info={"label": "Producto que se cosecha"}
    )
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    harvest_product: Mapped[Product] = relationship(lazy="joined")


class OperationType(BaseModel):
    __tablename__ = "operation_types"
    __label__ = "Tipo de labor"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(60), unique=True, info={"label": "Nombre"})
    uses_inputs: Mapped[bool] = mapped_column(default=False, info={"label": "Lleva insumos"})
    uses_assets: Mapped[bool] = mapped_column(default=True, info={"label": "Lleva maquinaria"})
    is_harvest: Mapped[bool] = mapped_column(default=False, info={"label": "Es cosecha"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


# --- Temporadas y ciclos ---


class Season(BaseModel):
    __tablename__ = "seasons"
    __label__ = "Temporada"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(10), unique=True, info={"label": "Nombre"})
    start_date: Mapped[date] = mapped_column(Date, info={"label": "Desde"})
    end_date: Mapped[date] = mapped_column(Date, info={"label": "Hasta"})


class CycleStatus(enum.StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"


CYCLE_STATUS_LABELS = {CycleStatus.ACTIVE: "En curso", CycleStatus.FINISHED: "Finalizado"}


class CropCycle(BaseModel):
    __tablename__ = "crop_cycles"
    __label__ = "Ciclo productivo"
    __display__ = "name"

    # "Tomate perita · Lote 3 · 2026/27" (se arma solo al crear)
    name: Mapped[str] = mapped_column(String(200), info={"label": "Nombre"})
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), info={"label": "Lote"})
    crop_id: Mapped[UUID] = mapped_column(ForeignKey("crops.id"), info={"label": "Cultivo"})
    season_id: Mapped[UUID] = mapped_column(ForeignKey("seasons.id"), info={"label": "Temporada"})
    area_ha: Mapped[Decimal] = mapped_column(Numeric(12, 2), info={"label": "Superficie (ha)"})
    start_date: Mapped[date] = mapped_column(Date, info={"label": "Inicio"})
    expected_end_date: Mapped[date | None] = mapped_column(Date, info={"label": "Fin estimado"})
    end_date: Mapped[date | None] = mapped_column(Date, info={"label": "Fin"})
    status: Mapped[CycleStatus] = mapped_column(
        _enum(CycleStatus, "cycle_status"),
        default=CycleStatus.ACTIVE,
        info={"label": "Estado", "choices": CYCLE_STATUS_LABELS},
    )
    reopen_reason: Mapped[str] = mapped_column(
        Text, default="", info={"label": "Motivo de reapertura"}
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})

    plot: Mapped[Plot] = relationship(lazy="joined")
    crop: Mapped[Crop] = relationship(lazy="joined")
    season: Mapped[Season] = relationship(lazy="joined")

    @property
    def is_finished(self) -> bool:
        return self.status == CycleStatus.FINISHED


# --- Labores ---


class OperationStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class FieldOperation(BaseModel):
    __tablename__ = "field_operations"
    __label__ = "Labor"
    __display__ = "number"

    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    operation_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("operation_types.id"), info={"label": "Tipo de labor"}
    )
    status: Mapped[OperationStatus] = mapped_column(
        _enum(OperationStatus, "field_operation_status"),
        default=OperationStatus.ACTIVE,
        info={"label": "Estado", "choices": {"active": "Vigente", "cancelled": "Anulada"}},
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    # Superficie total trabajada (suma de los ciclos): base del reparto
    total_area_ha: Mapped[Decimal] = mapped_column(Numeric(12, 2), info={"audit": False})
    stock_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stock_documents.id"), info={"audit": False}
    )

    # Cosecha (solo si el tipo es cosecha)
    harvest_product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id"), info={"label": "Producto cosechado"}
    )
    harvest_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("units.id"), info={"label": "Unidad cosechada"}
    )
    harvest_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), info={"label": "Cantidad cosechada"}
    )
    harvest_warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén destino"}
    )
    is_final_harvest: Mapped[bool] = mapped_column(default=False, info={"label": "Cosecha final"})

    operation_type: Mapped[OperationType] = relationship(lazy="joined")
    harvest_product: Mapped[Product | None] = relationship(lazy="joined")
    harvest_unit: Mapped[Unit | None] = relationship(lazy="joined")
    harvest_warehouse: Mapped[Warehouse | None] = relationship(lazy="joined")
    cycles: Mapped[list["FieldOperationCycle"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Ciclos", "audit_key": "summary"},
    )
    inputs: Mapped[list["FieldOperationInput"]] = relationship(
        cascade="all, delete-orphan",
        order_by="FieldOperationInput.line_no",
        lazy="selectin",
        info={"label": "Insumos", "audit_key": "summary"},
    )
    assets: Mapped[list["FieldOperationAsset"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Maquinaria", "audit_key": "summary"},
    )

    @property
    def is_harvest(self) -> bool:
        return self.operation_type.is_harvest


class FieldOperationCycle(BaseModel):
    """Ciclo trabajado por la labor y su superficie (para repartir insumos y horas)."""

    __tablename__ = "field_operation_cycles"
    __audited__ = False

    field_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_operations.id", ondelete="CASCADE"), index=True
    )
    crop_cycle_id: Mapped[UUID] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    area_ha: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    crop_cycle: Mapped[CropCycle] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.crop_cycle.name} ({format_quantity(self.area_ha)} ha)"


class FieldOperationInput(BaseModel):
    __tablename__ = "field_operation_inputs"
    __audited__ = False

    field_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_operations.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int]
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))  # total de la labor
    dose_per_ha: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("warehouses.id"))

    product: Mapped[Product] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")
    warehouse: Mapped[Warehouse] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.product.name}: {format_quantity(self.quantity)} {self.unit.code}"


class FieldOperationAsset(BaseModel):
    __tablename__ = "field_operation_assets"
    __audited__ = False

    field_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_operations.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True)
    usage: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # horas o km
    # Tarifa del activo al momento de cargar (cambiarla después no altera labores pasadas)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    asset: Mapped[Asset] = relationship(lazy="joined")

    @property
    def cost(self) -> Decimal:
        return (self.usage * self.rate).quantize(Decimal("0.01"))

    @property
    def summary(self) -> str:
        unit = "h" if self.asset.meter == "hours" else "km"
        return (
            f"{self.asset.name}: {format_quantity(self.usage)} {unit} × {format_money(self.rate)}"
        )


class Batch(BaseModel):
    """Partida: producción con origen común (una cosecha de un ciclo). ADR-012."""

    __tablename__ = "batches"
    __label__ = "Partida"
    __display__ = "code"

    code: Mapped[str] = mapped_column(String(60), unique=True, info={"label": "Código"})
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), info={"label": "Producto"})
    crop_cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("crop_cycles.id"), index=True, info={"label": "Ciclo"}
    )
    field_operation_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_operations.id"), info={"label": "Cosecha"}
    )
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})


Index("ix_crop_cycles_plot_status", CropCycle.plot_id, CropCycle.status)
Index("ix_field_operations_date", FieldOperation.date)
