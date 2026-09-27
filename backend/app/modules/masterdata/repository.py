from typing import Any
from uuid import UUID

from sqlalchemy import Select, select

from app.core.crud import CrudRepository
from app.modules.masterdata.models import Party, Product, ProductCategory, Unit, Warehouse


class UnitRepository(CrudRepository[Unit]):
    model = Unit
    search_fields = ("code", "name")


class CategoryRepository(CrudRepository[ProductCategory]):
    model = ProductCategory
    search_fields = ("name",)

    def siblings(self, parent_id: UUID | None, exclude_id: UUID | None) -> list[ProductCategory]:
        """Categorías del mismo nivel (misma categoría padre)."""
        query = select(ProductCategory).where(
            ProductCategory.parent_id.is_(None)
            if parent_id is None
            else ProductCategory.parent_id == parent_id
        )
        if exclude_id is not None:
            query = query.where(ProductCategory.id != exclude_id)
        return list(self.session.scalars(query))

    def children_ids(self, parent_id: UUID) -> list[UUID]:
        return list(
            self.session.scalars(
                select(ProductCategory.id).where(ProductCategory.parent_id == parent_id)
            )
        )


class ProductRepository(CrudRepository[Product]):
    model = Product
    search_fields = ("code", "name")

    def codes_with_prefix(self, prefix: str) -> list[str]:
        return list(
            self.session.scalars(select(Product.code).where(Product.code.like(f"{prefix}-%")))
        )


class PartyRepository(CrudRepository[Party]):
    model = Party
    search_fields = ("name", "trade_name", "cuit")

    def apply_filters(self, query: Select[Party], filters: dict[str, Any]) -> Select[Party]:
        role = filters.get("role")
        if role == "customer":
            query = query.where(Party.is_customer.is_(True))
        elif role == "supplier":
            query = query.where(Party.is_supplier.is_(True))
        return query


class WarehouseRepository(CrudRepository[Warehouse]):
    model = Warehouse
    search_fields = ("name", "location")
