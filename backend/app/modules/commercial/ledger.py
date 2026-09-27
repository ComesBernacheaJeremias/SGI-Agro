"""Cuentas corrientes (siempre calculadas): pendiente por comprobante, resumen de un tercero
y saldos con antigüedad.

Convención de signos del saldo, por dirección:
  - sale (clientes): saldo > 0 = el cliente nos debe.
  - purchase (proveedores): saldo > 0 = le debemos al proveedor.
Factura y nota de débito suman; nota de crédito y cobro/pago restan.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.commercial.models import (
    Allocation,
    CommercialDocument,
    Direction,
    DocumentKind,
    Payment,
    Status,
)
from app.modules.commercial.schemas import BalanceOut, LedgerOut, LedgerRowOut, Ref
from app.modules.masterdata.models import Party

ZERO = Decimal(0)
PAYMENT_LABEL = {Direction.SALE: "Cobro", Direction.PURCHASE: "Pago"}


def allocated_by_document(session: Session, document_ids: list[UUID]) -> dict[UUID, Decimal]:
    """Imputado a cada comprobante por cobros/pagos vigentes."""
    if not document_ids:
        return {}
    rows = session.execute(
        select(Allocation.document_id, func.sum(Allocation.amount))
        .join(Payment, Payment.id == Allocation.payment_id)
        .where(Allocation.document_id.in_(document_ids), Payment.status == Status.ACTIVE)
        .group_by(Allocation.document_id)
    ).all()
    return {row[0]: Decimal(row[1]) for row in rows}


def credited_by_document(session: Session, document_ids: list[UUID]) -> dict[UUID, Decimal]:
    """Notas de crédito vigentes asociadas a cada comprobante."""
    if not document_ids:
        return {}
    rows = session.execute(
        select(CommercialDocument.related_document_id, func.sum(CommercialDocument.total))
        .where(
            CommercialDocument.related_document_id.in_(document_ids),
            CommercialDocument.kind == DocumentKind.CREDIT_NOTE,
            CommercialDocument.status == Status.ACTIVE,
        )
        .group_by(CommercialDocument.related_document_id)
    ).all()
    return {row[0]: Decimal(row[1]) for row in rows if row[0]}


def pending_of(
    document: CommercialDocument, allocated: Decimal, credited: Decimal = ZERO
) -> Decimal:
    """Saldo pendiente: total − cobrado/pagado − NC asociadas (una NC no tiene pendiente)."""
    if document.status == Status.CANCELLED or document.kind == DocumentKind.CREDIT_NOTE:
        return ZERO
    return document.total - allocated - credited


class LedgerQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _documents(self, party_id: UUID | None, direction: Direction) -> list[CommercialDocument]:
        query = select(CommercialDocument).where(
            CommercialDocument.direction == direction,
            CommercialDocument.status == Status.ACTIVE,
        )
        if party_id:
            query = query.where(CommercialDocument.party_id == party_id)
        return list(self.session.scalars(query.order_by(CommercialDocument.date)))

    def _payments(self, party_id: UUID | None, direction: Direction) -> list[Payment]:
        query = select(Payment).where(
            Payment.direction == direction, Payment.status == Status.ACTIVE
        )
        if party_id:
            query = query.where(Payment.party_id == party_id)
        return list(self.session.scalars(query.order_by(Payment.date)))

    def ledger(
        self, party_id: UUID, direction: Direction, date_from: date | None, date_to: date | None
    ) -> LedgerOut:
        party = self.session.get(Party, party_id)
        if party is None:
            raise NotFoundError("No se encontró el cliente/proveedor.")
        entries: list[tuple[date, str, UUID, str, Decimal, Decimal]] = []
        for doc in self._documents(party_id, direction):
            debit, credit = (doc.total, ZERO) if doc.sign > 0 else (ZERO, doc.total)
            entries.append((doc.date, "document", doc.id, doc.invoice_label, debit, credit))
        for pay in self._payments(party_id, direction):
            entries.append(
                (
                    pay.date,
                    "payment",
                    pay.id,
                    f"{PAYMENT_LABEL[direction]} {pay.number}",
                    ZERO,
                    pay.total,
                )
            )
        entries.sort(key=lambda e: (e[0], e[1] != "document"))

        opening = sum(
            (d - c for day, _, _, _, d, c in entries if date_from and day < date_from), ZERO
        )
        balance, rows = opening, []
        for day, kind, id_, label, debit, credit in entries:
            if (date_from and day < date_from) or (date_to and day > date_to):
                continue
            balance += debit - credit
            rows.append(
                LedgerRowOut(
                    date=day,
                    kind=kind,
                    id=id_,
                    label=label,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                )
            )
        return LedgerOut(
            party=Ref(id=party.id, name=party.name),
            direction=direction,
            opening_balance=opening,
            rows=rows,
            closing_balance=balance,
        )

    def balances(self, direction: Direction, today: date | None = None) -> list[BalanceOut]:
        today = today or date.today()
        documents = self._documents(None, direction)
        payments = self._payments(None, direction)
        ids = [d.id for d in documents]
        allocated = allocated_by_document(self.session, ids)
        credited = credited_by_document(self.session, ids)

        result: dict[UUID, BalanceOut] = {}

        def row(party: Party) -> BalanceOut:
            if party.id not in result:
                result[party.id] = BalanceOut(
                    party=Ref(id=party.id, name=party.name),
                    direction=direction,
                    balance=ZERO,
                    overdue=ZERO,
                    days_0_30=ZERO,
                    days_31_60=ZERO,
                    days_61_90=ZERO,
                    days_over_90=ZERO,
                    advances=ZERO,
                )
            return result[party.id]

        for doc in documents:
            r = row(doc.party)
            r.balance += doc.sign * doc.total
            if doc.kind == DocumentKind.CREDIT_NOTE and doc.related_document_id is None:
                r.advances += doc.total  # NC sin comprobante asociado: saldo a favor
            pending = pending_of(doc, allocated.get(doc.id, ZERO), credited.get(doc.id, ZERO))
            if pending <= 0 or doc.due_date >= today:
                continue
            late: int = (today - doc.due_date).days
            r.overdue += pending
            if late <= 30:
                r.days_0_30 += pending
            elif late <= 60:
                r.days_31_60 += pending
            elif late <= 90:
                r.days_61_90 += pending
            else:
                r.days_over_90 += pending
        for pay in payments:
            r = row(pay.party)
            r.balance -= pay.total
            r.advances += pay.total - sum((a.amount for a in pay.allocations), ZERO)
        return sorted(
            (r for r in result.values() if r.balance != 0 or r.advances != 0),
            key=lambda r: r.party.name,
        )


def default_due_date(party: Party, day: date) -> date:
    return day + timedelta(days=party.payment_days)
