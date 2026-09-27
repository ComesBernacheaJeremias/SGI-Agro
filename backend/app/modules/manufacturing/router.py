from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.core.crud import ListQuery
from app.core.db import DbSession
from app.core.pagination import Page, Pagination, paginate
from app.modules.identity.authorization import require
from app.modules.identity.models import User
from app.modules.inventory.schemas import StockAlertOut
from app.modules.inventory.service import StockDocumentService
from app.modules.manufacturing.models import OrderStatus, ProductionOrder, Recipe
from app.modules.manufacturing.permissions import MANUFACTURING_READ, MANUFACTURING_WRITE
from app.modules.manufacturing.schemas import (
    ComponentCheckOut,
    ComponentOut,
    OrderCheckIn,
    OrderIn,
    OrderLineOut,
    OrderOut,
    OrderSavedOut,
    ProductRef,
    RecipeCreate,
    RecipeOut,
    RecipeUpdate,
    Ref,
    UnitRef,
)
from app.modules.manufacturing.service import (
    ProductionOrderService,
    RecipeRepository,
    RecipeService,
)

Reader = Annotated[User, require(MANUFACTURING_READ)]
Writer = Annotated[User, require(MANUFACTURING_WRITE)]

recipes_router = APIRouter(prefix="/api/v1/recipes", tags=["manufacturing"])
orders_router = APIRouter(prefix="/api/v1/production-orders", tags=["manufacturing"])


# --- Presentación ---


def recipe_out(service: RecipeService, recipe: Recipe) -> RecipeOut:
    repo = RecipeRepository(service.session)
    return RecipeOut(
        id=recipe.id,
        name=recipe.name,
        product=ProductRef(
            id=recipe.product.id, code=recipe.product.code, name=recipe.product.name
        ),
        yield_quantity=recipe.yield_quantity,
        yield_unit=UnitRef(id=recipe.yield_unit.id, code=recipe.yield_unit.code),
        instructions=recipe.instructions,
        components=[
            ComponentOut(
                product=ProductRef(id=c.product.id, code=c.product.code, name=c.product.name),
                product_type=c.product.type,
                unit=UnitRef(id=c.unit.id, code=c.unit.code),
                quantity=c.quantity,
                has_recipe=repo.for_product(c.product_id) is not None,
            )
            for c in recipe.components
        ],
        estimated_cost=service.estimated_cost(recipe),
        is_active=recipe.is_active,
    )


def order_out(db: DbSession, order: ProductionOrder) -> OrderOut:
    moves = (
        StockDocumentService(db).moves_of(order.stock_document_id)
        if order.stock_document_id
        else []
    )
    consumed = {m.line_no: -m.total_cost for m in moves if m.quantity < 0}
    produced = next((m for m in moves if m.quantity > 0), None)
    total = produced.total_cost if produced else Decimal(0)
    recipe = order.recipe
    return OrderOut(
        id=order.id,
        number=order.number,
        date=order.date,
        recipe=Ref(id=recipe.id, name=recipe.name),
        product=ProductRef(
            id=recipe.product.id, code=recipe.product.code, name=recipe.product.name
        ),
        quantity=order.quantity,
        unit=UnitRef(id=recipe.yield_unit.id, code=recipe.yield_unit.code),
        components_warehouse=Ref(
            id=order.components_warehouse.id, name=order.components_warehouse.name
        ),
        target_warehouse=Ref(id=order.target_warehouse.id, name=order.target_warehouse.name),
        status=order.status,
        notes=order.notes,
        lines=[
            OrderLineOut(
                product=ProductRef(
                    id=line.product.id, code=line.product.code, name=line.product.name
                ),
                unit=UnitRef(id=line.unit.id, code=line.unit.code),
                quantity=line.quantity,
                cost=consumed.get(line.line_no, Decimal(0)),
            )
            for line in order.lines
        ],
        total_cost=total,
        unit_cost=(total / order.quantity).quantize(Decimal("0.01"))
        if order.quantity
        else Decimal(0),
        parent_id=order.parent_id,
        stock_document_id=order.stock_document_id,
    )


def _saved(
    db: DbSession,
    order: ProductionOrder,
    prepared: list[ProductionOrder],
    alerts: list[StockAlertOut],
) -> OrderSavedOut:
    return OrderSavedOut(
        order=order_out(db, order), prepared=[order_out(db, o) for o in prepared], alerts=alerts
    )


# --- Recetas ---


@recipes_router.get("")
def list_recipes(db: DbSession, _: Reader, params: ListQuery, page: Pagination) -> Page[RecipeOut]:
    service = RecipeService(db)
    items, total = service.search(params, page)
    return Page(
        items=[recipe_out(service, r) for r in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


@recipes_router.get("/{id_}")
def get_recipe(id_: UUID, db: DbSession, _: Reader) -> RecipeOut:
    service = RecipeService(db)
    return recipe_out(service, service.get(id_))


@recipes_router.post("", status_code=status.HTTP_201_CREATED)
def create_recipe(body: RecipeCreate, db: DbSession, _: Writer) -> RecipeOut:
    service = RecipeService(db)
    return recipe_out(service, service.create(body))


@recipes_router.patch("/{id_}")
def update_recipe(id_: UUID, body: RecipeUpdate, db: DbSession, _: Writer) -> RecipeOut:
    service = RecipeService(db)
    return recipe_out(service, service.update(id_, body))


@recipes_router.post("/{id_}/deactivate")
def deactivate_recipe(id_: UUID, db: DbSession, _: Writer) -> RecipeOut:
    service = RecipeService(db)
    return recipe_out(service, service.set_active(id_, active=False))


@recipes_router.post("/{id_}/activate")
def activate_recipe(id_: UUID, db: DbSession, _: Writer) -> RecipeOut:
    service = RecipeService(db)
    return recipe_out(service, service.set_active(id_, active=True))


# --- Preparaciones ---


@orders_router.get("")
def list_orders(
    db: DbSession,
    _: Reader,
    page: Pagination,
    recipe_id: UUID | None = None,
    status_: Annotated[OrderStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[OrderOut]:
    query = select(ProductionOrder).order_by(
        ProductionOrder.date.desc(), ProductionOrder.number.desc()
    )
    if recipe_id:
        query = query.where(ProductionOrder.recipe_id == recipe_id)
    if status_:
        query = query.where(ProductionOrder.status == status_)
    if date_from:
        query = query.where(ProductionOrder.date >= date_from)
    if date_to:
        query = query.where(ProductionOrder.date <= date_to)
    items, total = paginate(db, query, page)
    return Page(
        items=[order_out(db, o) for o in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


@orders_router.post("/check")
def check_order(body: OrderCheckIn, db: DbSession, _: Reader) -> list[ComponentCheckOut]:
    """Componentes necesarios, disponibles y faltantes (antes de preparar)."""
    return ProductionOrderService(db).check(body)


@orders_router.get("/{id_}")
def get_order(id_: UUID, db: DbSession, _: Reader) -> OrderOut:
    return order_out(db, ProductionOrderService(db).get(id_))


@orders_router.post("", status_code=status.HTTP_201_CREATED)
def create_order(body: OrderIn, db: DbSession, _: Writer) -> OrderSavedOut:
    order, prepared, alerts = ProductionOrderService(db).create(body)
    return _saved(db, order, prepared, alerts)


@orders_router.put("/{id_}")
def update_order(id_: UUID, body: OrderIn, db: DbSession, _: Writer) -> OrderSavedOut:
    order, alerts = ProductionOrderService(db).update(id_, body)
    return _saved(db, order, [], alerts)


@orders_router.post("/{id_}/cancel")
def cancel_order(id_: UUID, db: DbSession, _: Writer) -> OrderSavedOut:
    order, alerts = ProductionOrderService(db).cancel(id_)
    return _saved(db, order, [], alerts)


routers = [recipes_router, orders_router]
