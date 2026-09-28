"""Consultas de stock: saldo por almacén, stock a una fecha, kardex y alertas de mínimo.

El stock siempre se calcula sumando movimientos no anulados (no hay saldos guardados).
El costo promedio de un producto a una fecha es el `avg_cost_after` de su último movimiento.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.pagination import PageParams
from app.modules.inventory.engine import CHRONOLOGICAL
from app.modules.inventory.models import StockDocument, StockMove
from app.modules.inventory.schemas import (
    BatchStockOut,
    KardexOut,
    KardexRowOut,
    ProductRef,
    Ref,
    StockAlertOut,
    StockRowOut,
)
from app.modules.masterdata.models import Product, ProductType, Unit, Warehouse

ACTIVE_MOVE = StockMove.cancelled.is_(False)


@dataclass(frozen=True)
class StockFilters:
    at: date | None = None  # None = hoy (todos los movimientos)
    q: str | None = None
    category_id: UUID | None = None
    warehouse_id: UUID | None = None
    by_warehouse: bool = False
    below_min: bool = False
    include_zero: bool = False
    product_id: UUID | None = None


def _normalized(column: Any) -> Any:
    return func.lower(func.unaccent(column))


class StockQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Saldos puntuales ---

    def quantity(
        self,
        product_id: UUID,
        warehouse_id: UUID | None = None,
        at: date | None = None,
        exclude_document_id: UUID | None = None,
    ) -> Decimal:
        query = select(func.coalesce(func.sum(StockMove.quantity), 0)).where(
            StockMove.product_id == product_id, ACTIVE_MOVE
        )
        if warehouse_id:
            query = query.where(StockMove.warehouse_id == warehouse_id)
        if at:
            query = query.where(StockMove.date <= at)
        if exclude_document_id:
            query = query.where(StockMove.document_id != exclude_document_id)
        return Decimal(self.session.scalar(query) or 0)

    def batch_balances(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        at: date,
        exclude_document_id: UUID | None = None,
        only_available: bool = True,
    ) -> list[BatchStockOut]:
        """Partidas con stock de un producto en un almacén, de la más vieja a la más nueva."""
        from app.modules.production.models import Batch  # import local: evita ciclo de módulos

        query = (
            select(StockMove.batch_id, Batch.code, Batch.date, func.sum(StockMove.quantity))
            .join(Batch, Batch.id == StockMove.batch_id)
            .where(
                StockMove.product_id == product_id,
                StockMove.warehouse_id == warehouse_id,
                StockMove.date <= at,
                ACTIVE_MOVE,
            )
            .group_by(StockMove.batch_id, Batch.date, Batch.code)
            .order_by(Batch.date, Batch.code)
        )
        if only_available:
            query = query.having(func.sum(StockMove.quantity) > 0)
        if exclude_document_id:
            query = query.where(StockMove.document_id != exclude_document_id)
        return [
            BatchStockOut(id=row[0], code=row[1], date=row[2], quantity=Decimal(row[3]))
            for row in self.session.execute(query).all()
        ]

    def average_cost(self, product_id: UUID) -> Decimal:
        """Costo promedio vigente (el del último movimiento del producto)."""
        value = self.session.scalar(
            select(StockMove.avg_cost_after)
            .where(StockMove.product_id == product_id, ACTIVE_MOVE)
            .order_by(*(c.desc() for c in CHRONOLOGICAL))
            .limit(1)
        )
        return Decimal(value or 0)

    # --- Stock (listado) ---

    def _totals(self, f: StockFilters, by_warehouse: bool) -> Any:
        columns = [StockMove.product_id.label("product_id")]
        if by_warehouse:
            columns.append(StockMove.warehouse_id.label("warehouse_id"))
        query = select(*columns, func.sum(StockMove.quantity).label("quantity")).where(ACTIVE_MOVE)
        if f.at:
            query = query.where(StockMove.date <= f.at)
        if f.warehouse_id:
            query = query.where(StockMove.warehouse_id == f.warehouse_id)
        return query.group_by(*columns).subquery()

    def _averages(self, at: date | None) -> Any:
        ranked = select(
            StockMove.product_id,
            StockMove.avg_cost_after,
            func.row_number()
            .over(partition_by=StockMove.product_id, order_by=[c.desc() for c in CHRONOLOGICAL])
            .label("rn"),
        ).where(ACTIVE_MOVE)
        if at:
            ranked = ranked.where(StockMove.date <= at)
        sub = ranked.subquery()
        return select(sub.c.product_id, sub.c.avg_cost_after).where(sub.c.rn == 1).subquery()

    def stock(self, f: StockFilters, page: PageParams) -> tuple[list[StockRowOut], int]:
        by_warehouse = f.by_warehouse or f.warehouse_id is not None
        totals = self._totals(f, by_warehouse)
        product_totals = self._totals(StockFilters(at=f.at), by_warehouse=False)
        averages = self._averages(f.at)

        quantity = func.coalesce(totals.c.quantity, 0)
        total_quantity = func.coalesce(product_totals.c.quantity, 0)
        below_min = and_(Product.min_stock > 0, total_quantity <= Product.min_stock)

        query: Select[Any] = (
            select(
                Product,
                Unit.code,
                quantity.label("quantity"),
                func.coalesce(averages.c.avg_cost_after, 0).label("avg_cost"),
                below_min.label("below_min"),
                *([Warehouse.id, Warehouse.name] if by_warehouse else []),
            )
            .join(Unit, Unit.id == Product.unit_id)
            .outerjoin(totals, totals.c.product_id == Product.id)
            .outerjoin(product_totals, product_totals.c.product_id == Product.id)
            .outerjoin(averages, averages.c.product_id == Product.id)
            .where(Product.type != ProductType.SERVICE)
        )
        if by_warehouse:
            query = query.join(Warehouse, Warehouse.id == totals.c.warehouse_id)
        if f.q:
            pattern = _normalized(f"%{f.q.strip()}%")
            query = query.where(
                or_(
                    _normalized(Product.name).like(pattern), _normalized(Product.code).like(pattern)
                )
            )
        if f.category_id:
            query = query.where(Product.category_id == f.category_id)
        if f.product_id:
            query = query.where(Product.id == f.product_id)
        if f.below_min:
            query = query.where(below_min)
        elif not f.include_zero:
            query = query.where(quantity != 0)
        if not f.include_zero and not f.below_min:
            query = query.where(or_(Product.is_active.is_(True), quantity != 0))

        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        order = [Product.name, *([Warehouse.name] if by_warehouse else [])]
        rows = self.session.execute(
            query.order_by(*order).offset(page.offset).limit(page.page_size)
        ).all()
        return [self._stock_row(row, by_warehouse) for row in rows], total

    @staticmethod
    def _stock_row(row: Any, by_warehouse: bool) -> StockRowOut:
        product: Product = row[0]
        quantity = Decimal(row.quantity)
        avg_cost = Decimal(row.avg_cost)
        return StockRowOut(
            product=ProductRef(id=product.id, code=product.code, name=product.name),
            unit=row.code,
            warehouse=Ref(id=row.id, name=row.name) if by_warehouse else None,
            quantity=quantity,
            avg_cost=avg_cost,
            value=(quantity * avg_cost).quantize(Decimal("0.01")),
            min_stock=product.min_stock,
            below_min=bool(row.below_min),
        )

    # --- Alertas de mínimo ("Necesitás comprar") ---

    def alerts(self, product_ids: set[UUID] | None = None) -> list[StockAlertOut]:
        totals = self._totals(StockFilters(), by_warehouse=False)
        quantity = func.coalesce(totals.c.quantity, 0)
        query = (
            select(Product, Unit.code, quantity.label("quantity"))
            .join(Unit, Unit.id == Product.unit_id)
            .outerjoin(totals, totals.c.product_id == Product.id)
            .where(
                Product.is_active.is_(True), Product.min_stock > 0, quantity <= Product.min_stock
            )
            .order_by(Product.name)
        )
        if product_ids is not None:
            query = query.where(Product.id.in_(product_ids))
        result = []
        for product, unit_code, qty in self.session.execute(query).all():
            minimum = Decimal(product.min_stock)
            result.append(
                StockAlertOut(
                    product=ProductRef(id=product.id, code=product.code, name=product.name),
                    unit=unit_code,
                    quantity=Decimal(qty),
                    min_stock=minimum,
                    missing=minimum - Decimal(qty),
                )
            )
        return result

    # --- Kardex ---

    def kardex(
        self,
        product_id: UUID,
        warehouse_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> KardexOut:
        product = self.session.get(Product, product_id)
        if product is None:
            raise NotFoundError("No se encontró el producto.")
        opening = (
            self.quantity(product_id, warehouse_id, at=date_from - timedelta(days=1))
            if date_from
            else Decimal(0)
        )
        query = (
            select(StockMove, StockDocument, Warehouse)
            .join(StockDocument, StockDocument.id == StockMove.document_id)
            .join(Warehouse, Warehouse.id == StockMove.warehouse_id)
            .where(StockMove.product_id == product_id, ACTIVE_MOVE)
            .order_by(*CHRONOLOGICAL)
        )
        if warehouse_id:
            query = query.where(StockMove.warehouse_id == warehouse_id)
        if date_from:
            query = query.where(StockMove.date >= date_from)
        if date_to:
            query = query.where(StockMove.date <= date_to)

        balance = opening
        rows = []
        for move, document, warehouse in self.session.execute(query).all():
            balance += move.quantity
            rows.append(
                KardexRowOut(
                    date=move.date,
                    document_id=document.id,
                    document_type=document.type,
                    document_number=document.number,
                    warehouse=Ref(id=warehouse.id, name=warehouse.name),
                    quantity=move.quantity,
                    unit_cost=move.unit_cost,
                    total_cost=move.total_cost,
                    balance=balance,
                    avg_cost_after=move.avg_cost_after,
                )
            )
        return KardexOut(
            product=ProductRef(id=product.id, code=product.code, name=product.name),
            unit=product.unit.code,
            opening_balance=opening,
            rows=rows,
            closing_balance=balance,
        )
