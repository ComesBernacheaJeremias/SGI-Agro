"""Ventas desglosadas por movimiento de stock (ADR-012).

Cada línea de producto de una venta se reparte entre sus movimientos (una venta de producción
propia puede salir de varias partidas): ingreso neto proporcional a la cantidad, costo de lo
vendido = costo del movimiento. La partida da el ciclo. La NC resta (ingreso y costo).
Las líneas de concepto (sin producto) son ingreso sin costo ni ciclo.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.commercial.models import (
    CommercialDocument,
    Direction,
    DocumentKind,
    LineKind,
    Status,
)
from app.modules.inventory.models import StockMove
from app.modules.masterdata.models import Product
from app.modules.production.models import Batch

ZERO = Decimal(0)


@dataclass(frozen=True)
class SaleFact:
    date: date
    document_id: UUID
    document_label: str
    party_id: UUID
    party_name: str
    product: Product | None  # None = concepto
    description: str
    batch_id: UUID | None
    crop_cycle_id: UUID | None
    quantity: Decimal  # unidad base; + vendido, − devuelto
    revenue: Decimal  # neto de IVA, con signo
    cost: Decimal  # costo de lo vendido, con signo


def sale_facts(
    session: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    cycle_ids: list[UUID] | None = None,
) -> list[SaleFact]:
    query = select(CommercialDocument).where(
        CommercialDocument.direction == Direction.SALE,
        CommercialDocument.status == Status.ACTIVE,
        CommercialDocument.is_opening_balance.is_(False),
    )
    if date_from:
        query = query.where(CommercialDocument.date >= date_from)
    if date_to:
        query = query.where(CommercialDocument.date <= date_to)
    if cycle_ids is not None:
        sold_from_cycles = (
            select(StockMove.document_id)
            .join(Batch, Batch.id == StockMove.batch_id)
            .where(Batch.crop_cycle_id.in_(cycle_ids))
        )
        query = query.where(CommercialDocument.stock_document_id.in_(sold_from_cycles))
    documents = list(session.scalars(query.order_by(CommercialDocument.date)))

    stock_ids = [d.stock_document_id for d in documents if d.stock_document_id]
    moves: dict[tuple[UUID, int], list[StockMove]] = defaultdict(list)
    for move in session.scalars(
        select(StockMove)
        .where(StockMove.document_id.in_(stock_ids), StockMove.cancelled.is_(False))
        .order_by(StockMove.line_no, StockMove.sub_no)
    ):
        moves[(move.document_id, move.line_no)].append(move)
    batch_ids = {m.batch_id for ms in moves.values() for m in ms if m.batch_id}
    cycle_of = dict(
        session.execute(select(Batch.id, Batch.crop_cycle_id).where(Batch.id.in_(batch_ids))).all()
    )

    facts: list[SaleFact] = []
    for doc in documents:
        sign = -1 if doc.kind == DocumentKind.CREDIT_NOTE else 1
        head = (doc.date, doc.id, doc.invoice_label, doc.party_id, doc.party.name)
        product_no = 0
        for line in doc.lines:
            if line.kind != LineKind.PRODUCT:
                facts.append(
                    SaleFact(
                        *head,
                        product=None,
                        description=line.description,
                        batch_id=None,
                        crop_cycle_id=None,
                        quantity=ZERO,
                        revenue=line.net_amount * sign,
                        cost=ZERO,
                    )
                )
                continue
            product_no += 1  # las líneas de stock numeran solo los productos
            line_moves = (
                moves.get((doc.stock_document_id, product_no), []) if doc.stock_document_id else []
            )
            total = sum((abs(m.quantity) for m in line_moves), ZERO)
            for move in line_moves:
                facts.append(
                    SaleFact(
                        *head,
                        product=line.product,
                        description=line.description,
                        batch_id=move.batch_id,
                        crop_cycle_id=cycle_of.get(move.batch_id) if move.batch_id else None,
                        quantity=-move.quantity,
                        revenue=line.net_amount * abs(move.quantity) / total * sign,
                        cost=-move.total_cost,
                    )
                )
    if cycle_ids is not None:
        wanted = set(cycle_ids)
        facts = [f for f in facts if f.crop_cycle_id in wanted]
    return facts
