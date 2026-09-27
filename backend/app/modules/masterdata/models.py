import enum
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.core.models import BaseModel


def _enum(enum_class: type[enum.Enum], name: str) -> Enum:
    """Enum de PostgreSQL guardando el valor (ej. 'input'), no el nombre de Python."""
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


# --- Unidades ---


class UnitKind(enum.StrEnum):
    MASS = "mass"  # base: kg
    VOLUME = "volume"  # base: L
    COUNT = "count"  # base: unidad
    TIME = "time"  # base: h
    DISTANCE = "distance"  # base: km
    AREA = "area"  # base: ha
    PACKAGE = "package"  # envases (cajón, bin, bidón): se convierten por producto


UNIT_KIND_LABELS = {
    UnitKind.MASS: "Masa",
    UnitKind.VOLUME: "Volumen",
    UnitKind.COUNT: "Cantidad",
    UnitKind.TIME: "Tiempo",
    UnitKind.DISTANCE: "Distancia",
    UnitKind.AREA: "Superficie",
    UnitKind.PACKAGE: "Envase",
}


class Unit(BaseModel):
    __tablename__ = "units"
    __label__ = "Unidad"
    __display__ = "code"

    code: Mapped[str] = mapped_column(String(10), unique=True, info={"label": "Abreviatura"})
    name: Mapped[str] = mapped_column(String(40), info={"label": "Nombre"})
    kind: Mapped[UnitKind] = mapped_column(
        _enum(UnitKind, "unit_kind"), info={"label": "Tipo", "choices": UNIT_KIND_LABELS}
    )
    # Cuántas unidades base de su tipo equivale (kg=1, g=0,001, tn=1000). Envases: 1.
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1, info={"label": "Factor"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


# --- Categorías ---


class ProductCategory(BaseModel):
    __tablename__ = "product_categories"
    __label__ = "Categoría"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(80), info={"label": "Nombre"})
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_categories.id"), info={"label": "Categoría padre"}
    )
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    parent: Mapped["ProductCategory | None"] = relationship(remote_side="ProductCategory.id")

    @property
    def path(self) -> str:
        """Ruta completa: "Insumos > Agroquímicos > Insecticidas"."""
        names: list[str] = []
        seen: set[UUID] = set()
        node: ProductCategory | None = self
        while node is not None and node.id not in seen:  # `seen` evita bucles por datos corruptos
            seen.add(node.id)
            names.append(node.name)
            node = node.parent
        return " > ".join(reversed(names))


# --- Productos ---


class ProductType(enum.StrEnum):
    INPUT = "input"  # insumo
    SEMI_FINISHED = "semi_finished"  # semielaborado
    FINISHED = "finished"  # producto terminado
    OWN_PRODUCE = "own_produce"  # producción propia (cosecha)
    RESALE = "resale"  # mercadería de reventa
    SERVICE = "service"  # servicio (sin stock)


PRODUCT_TYPE_LABELS = {
    ProductType.INPUT: "Insumo",
    ProductType.SEMI_FINISHED: "Semielaborado",
    ProductType.FINISHED: "Producto terminado",
    ProductType.OWN_PRODUCE: "Producción propia",
    ProductType.RESALE: "Reventa",
    ProductType.SERVICE: "Servicio",
}


class Product(BaseModel):
    __tablename__ = "products"
    __label__ = "Producto"
    __display__ = "name"

    code: Mapped[str] = mapped_column(String(20), unique=True, info={"label": "Código"})
    name: Mapped[str] = mapped_column(String(120), info={"label": "Nombre"})
    type: Mapped[ProductType] = mapped_column(
        _enum(ProductType, "product_type"), info={"label": "Tipo", "choices": PRODUCT_TYPE_LABELS}
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_categories.id"), info={"label": "Categoría"}
    )
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), info={"label": "Unidad base"})
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=21, info={"label": "IVA %"})
    min_stock: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), info={"label": "Stock mínimo"}
    )
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})

    category: Mapped[ProductCategory | None] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")
    conversions: Mapped[list["ProductUnitConversion"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        info={"label": "Conversiones", "audit_key": "summary"},
    )


class ProductUnitConversion(BaseModel):
    """Equivalencia propia del producto, tal como se carga:
    1 <unidad del producto> = <quantity> <unit>   (ej. 1 cajón = 18 kg).
    """

    __tablename__ = "product_unit_conversions"
    __audited__ = False  # se registra dentro del historial del producto

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))

    unit: Mapped[Unit] = relationship(lazy="joined")
    product: Mapped["Product"] = relationship(back_populates="conversions")

    @property
    def base_per_unit(self) -> Decimal:
        """Unidades del producto por cada `unit` (1 kg = 1/18 cajón)."""
        return Decimal(1) / self.quantity

    @property
    def summary(self) -> str:
        # Recién creada o recién quitada, la relación puede no estar en memoria: se busca por id
        session = object_session(self)
        product = self.product or (session.get(Product, self.product_id) if session else None)
        base = None
        if product is not None:
            base = product.unit or (session.get(Unit, product.unit_id) if session else None)
        base_code = base.code if base else ""
        return f"1 {base_code} = {self.quantity.normalize():f} {self.unit.code}"


# --- Clientes y proveedores ---


class VatCondition(enum.StrEnum):
    REGISTERED = "registered"  # Responsable Inscripto
    MONOTAX = "monotax"  # Monotributista
    EXEMPT = "exempt"  # Exento
    FINAL_CONSUMER = "final_consumer"  # Consumidor Final
    NOT_REGISTERED = "not_registered"  # No categorizado


VAT_CONDITION_LABELS = {
    VatCondition.REGISTERED: "Responsable Inscripto",
    VatCondition.MONOTAX: "Monotributista",
    VatCondition.EXEMPT: "Exento",
    VatCondition.FINAL_CONSUMER: "Consumidor Final",
    VatCondition.NOT_REGISTERED: "No categorizado",
}


class Party(BaseModel):
    __tablename__ = "parties"
    __label__ = "Cliente/Proveedor"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(150), info={"label": "Razón social"})
    trade_name: Mapped[str] = mapped_column(
        String(150), default="", info={"label": "Nombre de fantasía"}
    )
    cuit: Mapped[str | None] = mapped_column(String(11), unique=True, info={"label": "CUIT"})
    vat_condition: Mapped[VatCondition] = mapped_column(
        _enum(VatCondition, "vat_condition"),
        info={"label": "Condición IVA", "choices": VAT_CONDITION_LABELS},
    )
    is_customer: Mapped[bool] = mapped_column(default=False, info={"label": "Es cliente"})
    is_supplier: Mapped[bool] = mapped_column(default=False, info={"label": "Es proveedor"})
    address: Mapped[str] = mapped_column(String(200), default="", info={"label": "Domicilio"})
    city: Mapped[str] = mapped_column(String(80), default="", info={"label": "Localidad"})
    province: Mapped[str] = mapped_column(String(60), default="", info={"label": "Provincia"})
    phone: Mapped[str] = mapped_column(String(50), default="", info={"label": "Teléfono"})
    email: Mapped[str] = mapped_column(String(120), default="", info={"label": "Email"})
    payment_days: Mapped[int] = mapped_column(default=0, info={"label": "Días de pago"})
    notes: Mapped[str] = mapped_column(Text, default="", info={"label": "Observaciones"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})


# --- Almacenes ---


class WarehouseKind(enum.StrEnum):
    DEPOT = "depot"  # depósito
    COLD_STORAGE = "cold_storage"  # cámara de frío
    SHED = "shed"  # galpón
    AGROCHEMICALS = "agrochemicals"  # depósito de agroquímicos
    OTHER = "other"


WAREHOUSE_KIND_LABELS = {
    WarehouseKind.DEPOT: "Depósito",
    WarehouseKind.COLD_STORAGE: "Cámara de frío",
    WarehouseKind.SHED: "Galpón",
    WarehouseKind.AGROCHEMICALS: "Depósito de agroquímicos",
    WarehouseKind.OTHER: "Otro",
}


class Warehouse(BaseModel):
    __tablename__ = "warehouses"
    __label__ = "Almacén"
    __display__ = "name"

    name: Mapped[str] = mapped_column(String(80), unique=True, info={"label": "Nombre"})
    kind: Mapped[WarehouseKind] = mapped_column(
        _enum(WarehouseKind, "warehouse_kind"),
        info={"label": "Tipo", "choices": WAREHOUSE_KIND_LABELS},
    )
    location: Mapped[str] = mapped_column(String(200), default="", info={"label": "Ubicación"})
    is_active: Mapped[bool] = mapped_column(default=True, info={"label": "Activo"})
