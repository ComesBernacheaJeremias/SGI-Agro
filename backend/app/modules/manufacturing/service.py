"""Recetas y preparaciones.

Preparación → comprobante de stock "Elaboración":
  - salida de cada componente del almacén de componentes (costo promedio),
  - entrada del producto al almacén destino con costo DERIVADO (= lo consumido). Si después
    cambia el costo de un componente, el motor recalcula el elaborado en cascada.
"Preparar lo que falta": si falta un semielaborado con receta, antes se crea su preparación
(por la cantidad faltante, en forma recursiva), todo en la misma transacción.
"""

from datetime import date
from decimal import ROUND_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.crud import CrudRepository, CrudService
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.sequences import next_number
from app.modules.inventory.models import CostMode, DocumentType
from app.modules.inventory.queries import StockQueries
from app.modules.inventory.schemas import StockAlertOut
from app.modules.inventory.service import LineSpec, MoveSpec, StockDocumentService
from app.modules.manufacturing.models import (
    OrderStatus,
    ProductionOrder,
    ProductionOrderLine,
    Recipe,
    RecipeComponent,
)
from app.modules.manufacturing.schemas import (
    ComponentCheckOut,
    ComponentIn,
    OrderCheckIn,
    OrderIn,
    OrderLineIn,
    ProductRef,
    RecipeCreate,
    RecipeUpdate,
)
from app.modules.masterdata.models import Product, ProductType, Unit
from app.modules.masterdata.units import unit_factor

QTY = Decimal("0.0001")
SOURCE = "manufacturing"
ELABORATED = {ProductType.SEMI_FINISHED, ProductType.FINISHED}


# --- Recetas ---


class RecipeRepository(CrudRepository[Recipe]):
    model = Recipe
    search_fields = ("name",)

    def for_product(self, product_id: UUID) -> Recipe | None:
        return self.session.scalar(
            select(Recipe).where(Recipe.product_id == product_id, Recipe.is_active.is_(True))
        )


class RecipeService(CrudService[Recipe, RecipeCreate, RecipeUpdate]):
    repository_class = RecipeRepository
    not_found_message = "No se encontró la receta."
    repo: RecipeRepository

    def values_for_create(self, data: RecipeCreate) -> dict[str, Any]:
        product = self._product(data.product_id)
        if product.type not in ELABORATED:
            raise BusinessRuleError(
                "El producto de una receta tiene que ser semielaborado o producto terminado.",
                code="RECIPE_PRODUCT",
            )
        if self.repo.for_product(product.id):
            raise BusinessRuleError(
                f"'{product.name}' ya tiene una receta: editala.", code="DUPLICATE"
            )
        values = data.model_dump(exclude={"components"})
        values["name"] = product.name
        values["components"] = self._components(data.components)
        return values

    def values_for_update(self, data: RecipeUpdate) -> dict[str, Any]:
        values = data.model_dump(exclude_unset=True, exclude={"components"})
        if data.components is not None:
            values["components"] = self._components(data.components)
        return values

    def validate(self, obj: Recipe) -> None:
        super().validate(obj)
        product = self._product(obj.product_id)
        yield_unit = self.session.get(Unit, obj.yield_unit_id)
        if yield_unit is None:
            raise NotFoundError("No se encontró la unidad de rinde.")
        unit_factor(product, yield_unit)  # la unidad de rinde tiene que ser convertible
        seen = set()
        for component in obj.components:
            if component.product_id == obj.product_id:
                raise BusinessRuleError(
                    "Un producto no puede ser componente de su propia receta.", code="RECIPE_CYCLE"
                )
            if component.product_id in seen:
                raise BusinessRuleError(
                    f"'{component.product.name}' está repetido en la receta.", code="DUPLICATE_LINE"
                )
            seen.add(component.product_id)
        self._check_cycles(obj.product_id, [c.product_id for c in obj.components])

    def _product(self, product_id: UUID) -> Product:
        product = self.session.get(Product, product_id)
        if product is None:
            raise NotFoundError("No se encontró el producto.")
        return product

    def _components(self, items: list[ComponentIn]) -> list[RecipeComponent]:
        components = []
        for line_no, item in enumerate(items, start=1):
            product = self._product(item.product_id)
            unit = self.session.get(Unit, item.unit_id)
            if unit is None:
                raise NotFoundError("No se encontró una unidad de los componentes.")
            if product.type == ProductType.SERVICE:
                raise BusinessRuleError(
                    f"'{product.name}' es un servicio: no puede ser componente.",
                    code="SERVICE_PRODUCT",
                )
            unit_factor(product, unit)
            components.append(
                RecipeComponent(
                    line_no=line_no,
                    product=product,
                    product_id=product.id,
                    unit=unit,
                    unit_id=unit.id,
                    quantity=item.quantity,
                )
            )
        return components

    def _check_cycles(self, root: UUID, components: list[UUID]) -> None:
        """Recorre las recetas de los componentes: ninguna puede volver a usar `root`."""
        pending, visited = list(components), set()
        while pending:
            product_id = pending.pop()
            if product_id == root:
                raise BusinessRuleError(
                    "La receta es circular: un componente termina usando el mismo producto.",
                    code="RECIPE_CYCLE",
                )
            if product_id in visited:
                continue
            visited.add(product_id)
            recipe = self.repo.for_product(product_id)
            if recipe:
                pending += [c.product_id for c in recipe.components]

    def estimated_cost(self, recipe: Recipe, depth: int = 0) -> Decimal:
        """Costo por unidad de rinde con los costos promedio actuales."""
        queries = StockQueries(self.session)
        total = Decimal(0)
        for component in recipe.components:
            base = component.quantity * unit_factor(component.product, component.unit)
            cost = queries.average_cost(component.product_id)
            sub = self.repo.for_product(component.product_id)
            if cost == 0 and sub and depth < 10:
                sub_base = sub.yield_quantity * unit_factor(sub.product, sub.yield_unit)
                cost = self.estimated_cost(sub, depth + 1) * sub.yield_quantity / sub_base
            total += base * cost
        return (total / recipe.yield_quantity).quantize(Decimal("0.01"))


# --- Preparaciones ---


class ProductionOrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.stock = StockDocumentService(session)
        self.queries = StockQueries(session)
        self.recipes = RecipeRepository(session)

    def get(self, id_: UUID) -> ProductionOrder:
        order = self.session.get(ProductionOrder, id_)
        if order is None:
            raise NotFoundError("No se encontró la preparación.")
        return order

    def _recipe(self, id_: UUID) -> Recipe:
        recipe = self.session.get(Recipe, id_)
        if recipe is None or not recipe.is_active:
            raise BusinessRuleError("La receta no existe o está inactiva.", code="RECIPE")
        return recipe

    # --- Verificación de faltantes ---

    def check(self, data: OrderCheckIn) -> list[ComponentCheckOut]:
        recipe = self._recipe(data.recipe_id)
        result = []
        for line in self._scaled_lines(recipe, data.quantity):
            product = self.session.get(Product, line.product_id)
            unit = self.session.get(Unit, line.unit_id)
            assert product is not None and unit is not None  # noqa: S101
            required = line.quantity * unit_factor(product, unit)
            available = self.queries.quantity(
                product.id, data.components_warehouse_id, at=data.date
            )
            result.append(
                ComponentCheckOut(
                    product=ProductRef(id=product.id, code=product.code, name=product.name),
                    unit=product.unit.code,
                    required=required.quantize(QTY),
                    available=available,
                    missing=max(required - available, Decimal(0)).quantize(QTY),
                    can_prepare=self.recipes.for_product(product.id) is not None,
                )
            )
        return result

    # --- Alta / edición / anulación ---

    def create(
        self, data: OrderIn, parent_id: UUID | None = None
    ) -> tuple[ProductionOrder, list[ProductionOrder], list[StockAlertOut]]:
        if data.id and (existing := self.session.get(ProductionOrder, data.id)):
            return existing, [], []  # reintento del mismo guardado
        recipe = self._recipe(data.recipe_id)
        self._validate(data)
        lines = data.lines or self._scaled_lines(recipe, data.quantity)
        order = ProductionOrder(
            id=data.id or uuid7(),
            number=next_number(self.session, "ELA"),
            recipe=recipe,
            recipe_id=recipe.id,
            parent_id=parent_id,
        )
        self.session.add(order)
        self._fill(order, data, lines)
        self.session.flush()
        # Primero los semielaborados que falten: sus comprobantes quedan antes en el orden
        # cronológico del motor, así su stock está disponible para esta preparación.
        prepared = self._prepare_missing(data, lines, order.id) if data.prepare_missing else []
        alerts = self._sync_stock(order)
        return order, prepared, alerts

    def update(self, id_: UUID, data: OrderIn) -> tuple[ProductionOrder, list[StockAlertOut]]:
        order = self._editable(id_)
        if data.recipe_id != order.recipe_id:
            raise BusinessRuleError(
                "No se puede cambiar la receta de una preparación.", code="RECIPE"
            )
        self._validate(data)
        order.lines.clear()
        self._fill(order, data, data.lines or self._scaled_lines(order.recipe, data.quantity))
        self.session.flush()
        return order, self._sync_stock(order)

    def cancel(self, id_: UUID) -> tuple[ProductionOrder, list[StockAlertOut]]:
        order = self._editable(id_)
        order.status = OrderStatus.CANCELLED
        self.session.flush()
        alerts = (
            self.stock.cancel_system(order.stock_document_id) if order.stock_document_id else []
        )
        return order, alerts

    # --- Internos ---

    def _editable(self, id_: UUID) -> ProductionOrder:
        order = self.get(id_)
        if order.status == OrderStatus.CANCELLED:
            raise BusinessRuleError("La preparación está anulada.", code="CANCELLED")
        return order

    def _validate(self, data: OrderIn) -> None:
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        self.stock.active_warehouse(data.components_warehouse_id)
        self.stock.active_warehouse(data.target_warehouse_id)

    @staticmethod
    def _scaled_lines(recipe: Recipe, quantity: Decimal) -> list[OrderLineIn]:
        scale = quantity / recipe.yield_quantity
        return [
            OrderLineIn(
                product_id=c.product_id,
                unit_id=c.unit_id,
                quantity=(c.quantity * scale).quantize(QTY),
            )
            for c in recipe.components
        ]

    def _fill(self, order: ProductionOrder, data: OrderIn, lines: list[OrderLineIn]) -> None:
        order.date = data.date
        order.quantity = data.quantity
        order.components_warehouse_id = data.components_warehouse_id
        order.target_warehouse_id = data.target_warehouse_id
        order.notes = data.notes
        for line_no, item in enumerate(lines, start=1):
            spec = self.stock.line(item.product_id, item.unit_id, item.quantity)  # valida
            order.lines.append(
                ProductionOrderLine(
                    line_no=line_no,
                    product=spec.product,
                    product_id=spec.product.id,
                    unit=spec.unit,
                    unit_id=spec.unit.id,
                    quantity=item.quantity,
                )
            )

    def _prepare_missing(
        self, data: OrderIn, lines: list[OrderLineIn], parent_id: UUID
    ) -> list[ProductionOrder]:
        """Crea antes las preparaciones de los semielaborados que falten (recursivo)."""
        prepared: list[ProductionOrder] = []
        for line in lines:
            sub_recipe = self.recipes.for_product(line.product_id)
            if sub_recipe is None:
                continue
            product = sub_recipe.product
            unit = self.session.get(Unit, line.unit_id)
            assert unit is not None  # noqa: S101
            required = line.quantity * unit_factor(product, unit)
            available = self.queries.quantity(
                product.id, data.components_warehouse_id, at=data.date
            )
            missing = required - available
            if missing <= 0:
                continue
            yield_factor = unit_factor(product, sub_recipe.yield_unit)
            quantity = (missing / yield_factor).quantize(QTY, rounding=ROUND_UP)
            sub_data = OrderIn(
                date=data.date,
                recipe_id=sub_recipe.id,
                quantity=quantity,
                components_warehouse_id=data.components_warehouse_id,
                target_warehouse_id=data.components_warehouse_id,  # queda disponible para usar
                prepare_missing=True,
                notes=f"Preparado automáticamente para {self._recipe(data.recipe_id).name}",
            )
            order, sub_prepared, _ = self.create(sub_data, parent_id=parent_id)
            prepared += [*sub_prepared, order]
        return prepared

    def _sync_stock(self, order: ProductionOrder) -> list[StockAlertOut]:
        lines: list[LineSpec] = []
        for item in order.lines:
            spec = self.stock.line(item.product_id, item.unit_id, item.quantity)
            spec.moves = [
                MoveSpec(order.components_warehouse_id, -spec.base_quantity, CostMode.AVERAGE)
            ]
            lines.append(spec)
        recipe = order.recipe
        result = self.stock.line(recipe.product_id, recipe.yield_unit_id, order.quantity)
        result.moves = [MoveSpec(order.target_warehouse_id, result.base_quantity, CostMode.DERIVED)]
        lines.append(result)
        document, alerts = self.stock.save_system(
            document_id=order.stock_document_id,
            type_=DocumentType.PRODUCTION,
            date_=order.date,
            warehouse_id=order.target_warehouse_id,
            source_module=SOURCE,
            source_id=order.id,
            lines=lines,
            notes=f"Preparación {order.number}: {recipe.name}",
        )
        order.stock_document_id = document.id
        self.session.flush()
        return alerts
