"""Reglas de los maestros. Lo común (alta, edición, activación, únicos) viene de CrudService."""

from typing import Any
from uuid import UUID

from sqlalchemy import column, exists, inspect, select, table

from app.core.crud import CrudService
from app.core.errors import BusinessRuleError
from app.modules.masterdata.cuit import format_cuit, is_valid_cuit, normalize_cuit
from app.modules.masterdata.models import (
    Party,
    Product,
    ProductCategory,
    ProductType,
    ProductUnitConversion,
    Unit,
    Warehouse,
)
from app.modules.masterdata.repository import (
    CategoryRepository,
    PartyRepository,
    ProductRepository,
    UnitRepository,
    WarehouseRepository,
)
from app.modules.masterdata.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ConversionIn,
    PartyCreate,
    PartyUpdate,
    ProductCreate,
    ProductUpdate,
    UnitCreate,
    UnitUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)

# --- Unidades ---


class UnitService(CrudService[Unit, UnitCreate, UnitUpdate]):
    repository_class = UnitRepository
    unique_fields = {"code": "Ya existe la unidad '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró la unidad."


# --- Categorías ---


class CategoryService(CrudService[ProductCategory, CategoryCreate, CategoryUpdate]):
    repository_class = CategoryRepository
    not_found_message = "No se encontró la categoría."
    repo: CategoryRepository

    def validate(self, obj: ProductCategory) -> None:
        super().validate(obj)
        if obj.parent_id is not None:
            if self.session.get(ProductCategory, obj.parent_id) is None:
                raise BusinessRuleError("La categoría padre no existe.", code="NOT_FOUND")
            if obj.id is not None and obj.parent_id in self._self_and_descendants(obj.id):
                raise BusinessRuleError(
                    "Una categoría no puede estar dentro de sí misma ni de sus subcategorías.",
                    code="CATEGORY_CYCLE",
                )
        self._ensure_unique_name_in_parent(obj)

    def _self_and_descendants(self, id_: UUID) -> set[UUID]:
        found, pending = {id_}, [id_]
        while pending:
            for child in self.repo.children_ids(pending.pop()):
                if child not in found:
                    found.add(child)
                    pending.append(child)
        return found

    def _ensure_unique_name_in_parent(self, obj: ProductCategory) -> None:
        siblings = self.repo.siblings(obj.parent_id, exclude_id=obj.id)
        if any(s.name.lower() == obj.name.lower() for s in siblings):
            raise BusinessRuleError(
                f"Ya existe la categoría '{obj.name}' en ese nivel.", code="DUPLICATE"
            )


# --- Productos ---

# Prefijo del código automático según el tipo de producto
CODE_PREFIXES = {
    ProductType.INPUT: "INS",
    ProductType.SEMI_FINISHED: "SEM",
    ProductType.FINISHED: "TER",
    ProductType.OWN_PRODUCE: "PRO",
    ProductType.RESALE: "REV",
    ProductType.SERVICE: "SER",
}


class ProductService(CrudService[Product, ProductCreate, ProductUpdate]):
    repository_class = ProductRepository
    unique_fields = {"code": "Ya existe un producto con el código '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el producto."
    repo: ProductRepository

    def values_for_create(self, data: ProductCreate) -> dict[str, Any]:
        values = data.model_dump(exclude={"conversions"})
        values["code"] = (data.code or "").upper() or self.next_code(data.type)
        values["conversions"] = self._build_conversions(data.conversions)
        return values

    def values_for_update(self, data: ProductUpdate) -> dict[str, Any]:
        values = data.model_dump(exclude_unset=True, exclude={"conversions"})
        if values.get("code"):
            values["code"] = values["code"].upper()
        if data.conversions is not None:
            values["conversions"] = self._build_conversions(data.conversions)
        return values

    def next_code(self, product_type: ProductType) -> str:
        prefix = CODE_PREFIXES[product_type]
        numbers = [
            int(suffix)
            for code in self.repo.codes_with_prefix(prefix)
            if (suffix := code.removeprefix(f"{prefix}-")).isdigit()
        ]
        return f"{prefix}-{max(numbers, default=0) + 1:04d}"

    def validate(self, obj: Product) -> None:
        super().validate(obj)
        unit = self.session.get(Unit, obj.unit_id)
        if unit is None:
            raise BusinessRuleError("La unidad base no existe.", code="NOT_FOUND")
        if (
            obj.category_id is not None
            and self.session.get(ProductCategory, obj.category_id) is None
        ):
            raise BusinessRuleError("La categoría no existe.", code="NOT_FOUND")
        units = [c.unit_id for c in obj.conversions]
        if obj.unit_id in units:
            raise BusinessRuleError(
                f"No hace falta una conversión para la unidad base ({unit.code}).",
                code="INVALID_CONVERSION",
            )
        if len(units) != len(set(units)):
            raise BusinessRuleError(
                "Hay una unidad repetida en las conversiones.", code="INVALID_CONVERSION"
            )
        if self._base_unit_changed_with_moves(obj):
            raise BusinessRuleError(
                "No se puede cambiar la unidad base: el producto ya tiene movimientos de stock.",
                code="BASE_UNIT_LOCKED",
            )

    def _base_unit_changed_with_moves(self, obj: Product) -> bool:
        history = inspect(obj).attrs.unit_id.history
        if obj.id is None or not history.deleted:
            return False
        # Tabla de inventario referida por nombre: maestros no depende del módulo inventario
        stock_moves = table("stock_moves", column("product_id"))
        query = select(exists().where(stock_moves.c.product_id == obj.id))
        return bool(self.session.scalar(query))

    def _build_conversions(self, items: list[ConversionIn]) -> list[ProductUnitConversion]:
        conversions = []
        for item in items:
            unit = self.session.get(Unit, item.unit_id)
            if unit is None:
                raise BusinessRuleError(
                    "Una unidad de las conversiones no existe.", code="NOT_FOUND"
                )
            conversions.append(
                ProductUnitConversion(unit=unit, unit_id=unit.id, quantity=item.quantity)
            )
        return conversions


# --- Clientes y proveedores ---


class PartyService(CrudService[Party, PartyCreate, PartyUpdate]):
    repository_class = PartyRepository
    not_found_message = "No se encontró el cliente/proveedor."

    def values_for_create(self, data: PartyCreate) -> dict[str, Any]:
        values = data.model_dump()
        values["cuit"] = normalize_cuit(data.cuit) if data.cuit else None
        return values

    def values_for_update(self, data: PartyUpdate) -> dict[str, Any]:
        values = data.model_dump(exclude_unset=True)
        if "cuit" in values:
            values["cuit"] = normalize_cuit(values["cuit"]) if values["cuit"] else None
        return values

    def validate(self, obj: Party) -> None:
        super().validate(obj)
        if not obj.cuit:
            obj.cuit = None
        elif not is_valid_cuit(obj.cuit):
            raise BusinessRuleError(
                f"El CUIT {format_cuit(obj.cuit)} no es válido (revisá los números).",
                code="INVALID_CUIT",
            )
        elif self.repo.exists_with("cuit", obj.cuit, obj.id):
            raise BusinessRuleError(
                f"Ya existe un cliente/proveedor con CUIT {format_cuit(obj.cuit)}.",
                code="DUPLICATE",
            )
        if not (obj.is_customer or obj.is_supplier):
            raise BusinessRuleError(
                "Indicá si es cliente, proveedor o ambos.", code="PARTY_ROLE_REQUIRED"
            )


# --- Almacenes ---


class WarehouseService(CrudService[Warehouse, WarehouseCreate, WarehouseUpdate]):
    repository_class = WarehouseRepository
    unique_fields = {"name": "Ya existe el almacén '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró el almacén."
