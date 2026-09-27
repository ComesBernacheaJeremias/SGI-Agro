"""Cobros (a clientes) y pagos (a proveedores).

Un cobro/pago tiene medios (efectivo/transferencia, cada uno contra una cuenta de dinero)
y se imputa a comprobantes del mismo tercero. Lo no imputado queda como anticipo y se
puede imputar después (editando el cobro/pago).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.formatting import format_money
from app.core.pagination import PageParams, paginate
from app.core.sequences import next_number
from app.modules.commercial.ledger import allocated_by_document, credited_by_document, pending_of
from app.modules.commercial.models import (
    Allocation,
    CashAccount,
    CommercialDocument,
    Direction,
    Payment,
    PaymentLine,
    Status,
)
from app.modules.commercial.schemas import PaymentIn
from app.modules.masterdata.models import Party

ZERO = Decimal(0)
PREFIX = {Direction.SALE: "REC", Direction.PURCHASE: "OP"}


@dataclass(frozen=True)
class PaymentFilters:
    direction: Direction
    party_id: UUID | None = None
    status: Status | None = None
    date_from: date | None = None
    date_to: date | None = None


def active_cash_account(session: Session, id_: UUID) -> CashAccount:
    account = session.get(CashAccount, id_)
    if account is None or not account.is_active:
        raise BusinessRuleError(
            "La cuenta de dinero no existe o está inactiva.", code="CASH_ACCOUNT"
        )
    return account


def ensure_after_opening(account: CashAccount, day: date) -> None:
    if day < account.opening_date:
        raise BusinessRuleError(
            f"La fecha es anterior al saldo inicial de '{account.name}'.", code="BEFORE_OPENING"
        )


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id_: UUID) -> Payment:
        payment = self.session.get(Payment, id_)
        if payment is None:
            raise NotFoundError("No se encontró el cobro/pago.")
        return payment

    def search(self, f: PaymentFilters, page: PageParams) -> tuple[list[Payment], int]:
        query = (
            select(Payment)
            .where(Payment.direction == f.direction)
            .order_by(Payment.date.desc(), Payment.number.desc())
        )
        if f.party_id:
            query = query.where(Payment.party_id == f.party_id)
        if f.status:
            query = query.where(Payment.status == f.status)
        if f.date_from:
            query = query.where(Payment.date >= f.date_from)
        if f.date_to:
            query = query.where(Payment.date <= f.date_to)
        return paginate(self.session, query, page)

    def create(self, data: PaymentIn) -> Payment:
        party = self._party(data)
        payment = Payment(
            id=uuid7(),
            direction=data.direction,
            number=next_number(self.session, PREFIX[data.direction]),
        )
        self.session.add(payment)
        self._fill(payment, data, party)
        self.session.flush()
        return payment

    def update(self, id_: UUID, data: PaymentIn) -> Payment:
        payment = self._editable(id_)
        if data.direction != payment.direction:
            raise BusinessRuleError("No se puede cambiar un cobro por un pago.", code="DIRECTION")
        party = self._party(data)
        payment.lines.clear()
        payment.allocations.clear()
        self.session.flush()  # libera lo imputado antes de validar lo nuevo
        self._fill(payment, data, party)
        self.session.flush()
        return payment

    def cancel(self, id_: UUID) -> Payment:
        payment = self._editable(id_)
        payment.status = Status.CANCELLED
        payment.allocations.clear()
        self.session.flush()
        return payment

    def allocated(self, payment: Payment) -> Decimal:
        return sum((a.amount for a in payment.allocations), ZERO)

    # --- Internos ---

    def _editable(self, id_: UUID) -> Payment:
        payment = self.get(id_)
        if payment.status == Status.CANCELLED:
            raise BusinessRuleError("El cobro/pago está anulado.", code="CANCELLED")
        return payment

    def _party(self, data: PaymentIn) -> Party:
        party = self.session.get(Party, data.party_id)
        if party is None:
            raise NotFoundError("No se encontró el cliente/proveedor.")
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        return party

    def _fill(self, payment: Payment, data: PaymentIn, party: Party) -> None:
        payment.party_id, payment.party = party.id, party
        payment.date = data.date
        payment.notes = data.notes
        total = ZERO
        for item in data.lines:
            account = active_cash_account(self.session, item.cash_account_id)
            ensure_after_opening(account, data.date)
            payment.lines.append(
                PaymentLine(
                    method=item.method,
                    cash_account=account,
                    cash_account_id=account.id,
                    amount=item.amount,
                    reference=item.reference,
                )
            )
            total += item.amount
        payment.total = total
        self._allocate(payment, data)

    def _allocate(self, payment: Payment, data: PaymentIn) -> None:
        ids = [a.document_id for a in data.allocations]
        if len(ids) != len(set(ids)):
            raise BusinessRuleError(
                "Un comprobante está imputado dos veces.", code="DUPLICATE_ALLOCATION"
            )
        allocated = allocated_by_document(self.session, ids)
        credited = credited_by_document(self.session, ids)
        total_allocated = ZERO
        for item in data.allocations:
            document = self.session.get(CommercialDocument, item.document_id)
            if (
                document is None
                or document.party_id != payment.party_id
                or document.direction != payment.direction
            ):
                raise BusinessRuleError(
                    "Solo se imputan comprobantes del mismo cliente/proveedor.",
                    code="ALLOCATION_PARTY",
                )
            pending = pending_of(
                document, allocated.get(document.id, ZERO), credited.get(document.id, ZERO)
            )
            if item.amount > pending:
                raise BusinessRuleError(
                    f"A {document.invoice_label} le quedan pendientes {format_money(pending)}: "
                    "no se puede imputar más.",
                    code="ALLOCATION_EXCEEDS",
                )
            payment.allocations.append(
                Allocation(document=document, document_id=document.id, amount=item.amount)
            )
            total_allocated += item.amount
        if total_allocated > payment.total:
            raise BusinessRuleError(
                "Lo imputado supera el total del cobro/pago.", code="ALLOCATION_OVER_TOTAL"
            )
