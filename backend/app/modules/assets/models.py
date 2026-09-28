"""Activos (M07): máquinas, vehículos y herramientas; lecturas del medidor, planes de
mantenimiento y mantenimientos (con repuestos que salen del stock)."""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.formatting import format_quantity
from app.core.models import BaseModel
from app.modules.masterdata.models import Product, Unit, Warehouse

if TYPE_CHECKING:
    from app.modules.commercial.models import CommercialDocument


def _enum(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


class AssetKind(enum.StrEnum):
    MACHINERY = "machinery"  # tractor, pulverizadora…
    VEHICLE = "vehicle"  # camioneta
    TOOL = "tool"  # herramienta


ASSET_KIND_LABELS = {
    AssetKind.MACHINERY: "Maquinaria",
    AssetKind.VEHICLE: "Vehículo",
    AssetKind.TOOL: "Herramienta",
}


class AssetMeter(enum.StrEnum):
    HOURS = "hours"
    KM = "km"


ASSET_METER_LABELS = {AssetMeter.HOURS: "Horas", AssetMeter.KM: "Kilómetros"}
# Unidad que se muestra junto a una cantidad ("250 horas", "12.000 km")
METER_UNITS = {AssetMeter.HOURS: "horas", AssetMeter.KM: "km"}


def meter_unit(meter: str) -> str:
    return METER_UNITS[AssetMeter(meter)]


class AssetStatus(enum.StrEnum):
    OPERATIONAL = "operational"
    IN_REPAIR = "in_repair"


ASSET_STATUS_LABELS = {AssetStatus.OPERATIONAL: "Operativo", AssetStatus.IN_REPAIR: "En reparación"}


class Asset(BaseModel):
    __tablename__ = "assets"
    __label__ = "Activo"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(100), unique=True, info={"label": "Nombre"})
    kind: Mapped[AssetKind] = mapped_column(
        _enum(AssetKind, "asset_kind"), info={"label": "Tipo", "choices": ASSET_KIND_LABELS}
    )
    brand: Mapped[str] = mapped_column(String(60), default="", info={"label": "Marca"})
    model: Mapped[str] = mapped_column(String(60), default="", info={"label": "Modelo"})
    year: Mapped[int | None] = mapped_column(info={"label": "Año"})
    identifier: Mapped[str] = mapped_column(
        String(40), default="", info={"label": "Patente / N° de serie"}
    )
    meter: Mapped[AssetMeter] = mapped_column(
        _enum(AssetMeter, "asset_meter"), info={"label": "Medidor", "choices": ASSET_METER_LABELS}
    )
    # Costo por hora (maquinaria) o por km (vehículos) que se imputa a las labores
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, info={"label": "Tarifa"})
    status: Mapped[AssetStatus] = mapped_column(
        _enum(AssetStatus, "asset_status"),
        default=AssetStatus.OPERATIONAL,
        info={"label": "Estado", "choices": ASSET_STATUS_LABELS},
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


# --- Uso y mantenimiento (F6) ---


class MeterReading(BaseModel):
    """Lectura del horómetro u odómetro en una fecha."""

    __tablename__ = "asset_meter_readings"
    __label__ = "Lectura de medidor"
    __display__ = "summary"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id"), index=True, info={"label": "Activo"}
    )
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    value: Mapped[Decimal] = mapped_column(Numeric(12, 1), info={"label": "Lectura"})
    notes: Mapped[str] = mapped_column(String(200), default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    asset: Mapped[Asset] = relationship(lazy="joined")

    @property
    def summary(self) -> str:
        return f"{self.asset.name}: {format_quantity(self.value)}"


class MaintenancePlan(BaseModel):
    """Mantenimiento periódico: cada tanto uso y/o cada tantos meses (lo que llegue primero)."""

    __tablename__ = "maintenance_plans"
    __label__ = "Plan de mantenimiento"
    __display__ = "name"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id"), index=True, info={"label": "Activo"}
    )
    name: Mapped[str] = mapped_column(String(100), info={"label": "Nombre"})
    every_usage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 1), info={"label": "Cada (horas/km)"}
    )
    every_months: Mapped[int | None] = mapped_column(info={"label": "Cada (meses)"})
    # Punto de partida hasta el primer mantenimiento registrado con este plan
    start_date: Mapped[date] = mapped_column(Date, info={"label": "Desde"})
    start_reading: Mapped[Decimal] = mapped_column(
        Numeric(12, 1), default=0, info={"label": "Lectura inicial"}
    )
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    asset: Mapped[Asset] = relationship(lazy="joined")


class MaintenanceKind(enum.StrEnum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"


MAINTENANCE_KIND_LABELS = {
    MaintenanceKind.PREVENTIVE: "Preventivo",
    MaintenanceKind.CORRECTIVE: "Correctivo",
}


class MaintenanceStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


MAINTENANCE_STATUS_LABELS = {
    MaintenanceStatus.ACTIVE: "Vigente",
    MaintenanceStatus.CANCELLED: "Anulado",
}


class Maintenance(BaseModel):
    """Mantenimiento realizado. Los repuestos salen del stock (costo del activo); el servicio
    externo es una compra con destino = activo, que se vincula acá (no se carga dos veces)."""

    __tablename__ = "maintenances"
    __label__ = "Mantenimiento"
    __display__ = "number"

    number: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Número"})
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id"), index=True, info={"label": "Activo"}
    )
    date: Mapped[date] = mapped_column(Date, info={"label": "Fecha"})
    kind: Mapped[MaintenanceKind] = mapped_column(
        _enum(MaintenanceKind, "maintenance_kind"),
        info={"label": "Tipo", "choices": MAINTENANCE_KIND_LABELS},
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("maintenance_plans.id"), index=True, info={"label": "Plan"}
    )
    description: Mapped[str] = mapped_column(Text, default="", info={"label": "Descripción"})
    meter_reading: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 1), info={"label": "Lectura del medidor"}
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), info={"label": "Almacén de repuestos"}
    )
    purchase_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("commercial_documents.id"), info={"label": "Compra del servicio"}
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        _enum(MaintenanceStatus, "maintenance_status"),
        default=MaintenanceStatus.ACTIVE,
        info={"label": "Estado", "choices": MAINTENANCE_STATUS_LABELS},
    )
    stock_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stock_documents.id"), info={"audit": False}
    )

    asset: Mapped[Asset] = relationship(lazy="joined")
    plan: Mapped[MaintenancePlan | None] = relationship(lazy="joined")
    warehouse: Mapped[Warehouse | None] = relationship(lazy="joined")
    purchase_document: Mapped["CommercialDocument | None"] = relationship(lazy="joined")
    parts: Mapped[list["MaintenancePart"]] = relationship(
        cascade="all, delete-orphan",
        order_by="MaintenancePart.line_no",
        lazy="selectin",
        info={"label": "Repuestos", "audit_key": "summary"},
    )


class MaintenancePart(BaseModel):
    __tablename__ = "maintenance_parts"
    __audited__ = False  # se registra en el historial del mantenimiento

    maintenance_id: Mapped[UUID] = mapped_column(
        ForeignKey("maintenances.id", ondelete="CASCADE"), index=True
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
