"""Caja y bancos: movimientos sin tercero y saldos (siempre calculados).

Saldo de una cuenta = saldo inicial + cobros − pagos + ingresos − gastos − retiros
± transferencias entre cuentas.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.core.sequences import next_number
from app.modules.commercial.destinations import ensure_destination_open, resolve_destination
from app.modules.commercial.models import (
    CASH_MOVEMENT_KIND_LABELS,
    CashAccount,
    CashMovement,
    CashMovementKind,
    Direction,
    ExpenseCategory,
    Payment,
    PaymentLine,
    Status,
)
from app.modules.commercial.payment_service import active_cash_account, ensure_after_opening
from app.modules.commercial.schemas import (
    CashBalanceOut,
    CashMovementIn,
    CashStatementOut,
    CashStatementRowOut,
    Ref,
)

ZERO = Decimal(0)
OUTFLOWS = {CashMovementKind.EXPENSE, CashMovementKind.WITHDRAWAL, CashMovementKind.TRANSFER}
PAYMENT_LABEL = {Direction.SALE: "Cobro", Direction.PURCHASE: "Pago"}


@dataclass(frozen=True)
class MovementFilters:
    cash_account_id: UUID | None = None
    kind: CashMovementKind | None = None
    status: Status | None = None
    date_from: date | None = None
    date_to: date | None = None


class CashMovementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id_: UUID) -> CashMovement:
        movement = self.session.get(CashMovement, id_)
        if movement is None:
            raise NotFoundError("No se encontró el movimiento.")
        return movement

    def search(self, f: MovementFilters, page: PageParams) -> tuple[list[CashMovement], int]:
        query = select(CashMovement).order_by(CashMovement.date.desc(), CashMovement.number.desc())
        if f.cash_account_id:
            query = query.where(
                or_(
                    CashMovement.cash_account_id == f.cash_account_id,
                    CashMovement.target_account_id == f.cash_account_id,
                )
            )
        if f.kind:
            query = query.where(CashMovement.kind == f.kind)
        if f.status:
            query = query.where(CashMovement.status == f.status)
        if f.date_from:
            query = query.where(CashMovement.date >= f.date_from)
        if f.date_to:
            query = query.where(CashMovement.date <= f.date_to)
        return paginate(self.session, query, page)

    def create(self, data: CashMovementIn) -> CashMovement:
        movement = CashMovement(id=uuid7(), number=next_number(self.session, "MOV"))
        self.session.add(movement)
        self._fill(movement, data)
        self.session.flush()
        return movement

    def update(self, id_: UUID, data: CashMovementIn) -> CashMovement:
        movement = self._editable(id_)
        self._fill(movement, data)
        self.session.flush()
        return movement

    def cancel(self, id_: UUID) -> CashMovement:
        movement = self._editable(id_)
        movement.status = Status.CANCELLED
        self.session.flush()
        return movement

    def _editable(self, id_: UUID) -> CashMovement:
        movement = self.get(id_)
        if movement.status == Status.CANCELLED:
            raise BusinessRuleError("El movimiento está anulado.", code="CANCELLED")
        ensure_destination_open(self.session, movement)
        return movement

    def _fill(self, movement: CashMovement, data: CashMovementIn) -> None:
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        account = active_cash_account(self.session, data.cash_account_id)
        ensure_after_opening(account, data.date)
        target = None
        if data.kind == CashMovementKind.TRANSFER:
            if data.target_account_id is None or data.target_account_id == account.id:
                raise BusinessRuleError(
                    "Elegí una cuenta destino distinta de la de origen.", code="TARGET"
                )
            target = active_cash_account(self.session, data.target_account_id)
            ensure_after_opening(target, data.date)
        category = None
        dimensions: dict[str, UUID | None] = dict.fromkeys(
            ("farm_id", "plot_id", "crop_cycle_id", "asset_id")
        )
        if data.kind == CashMovementKind.EXPENSE:
            category = (
                self.session.get(ExpenseCategory, data.expense_category_id)
                if data.expense_category_id
                else None
            )
            if category is None:
                raise BusinessRuleError("Elegí la categoría del gasto.", code="EXPENSE_CATEGORY")
            dimensions = resolve_destination(self.session, data)
        elif data.kind != CashMovementKind.TRANSFER and not data.description:
            raise BusinessRuleError("Completá la descripción.", code="DESCRIPTION")
        movement.date = data.date
        movement.kind = data.kind
        movement.cash_account, movement.cash_account_id = account, account.id
        movement.target_account = target
        movement.target_account_id = target.id if target else None
        movement.amount = data.amount
        movement.description = data.description
        movement.expense_category = category
        movement.expense_category_id = category.id if category else None
        for field, value in dimensions.items():
            setattr(movement, field, value)


class CashQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _entries(self, account: CashAccount) -> list[tuple[date, str, UUID, str, Decimal]]:
        """Lo que movió la cuenta: (fecha, origen, id, detalle, ±importe)."""
        entries: list[tuple[date, str, UUID, str, Decimal]] = []
        payments = self.session.execute(
            select(Payment, PaymentLine.amount)
            .join(PaymentLine, PaymentLine.payment_id == Payment.id)
            .where(PaymentLine.cash_account_id == account.id, Payment.status == Status.ACTIVE)
        ).all()
        for payment, amount in payments:
            sign = 1 if payment.direction == Direction.SALE else -1
            label = f"{PAYMENT_LABEL[payment.direction]} {payment.number} · {payment.party.name}"
            entries.append((payment.date, "payment", payment.id, label, sign * amount))
        movements = self.session.scalars(
            select(CashMovement).where(
                CashMovement.status == Status.ACTIVE,
                or_(
                    CashMovement.cash_account_id == account.id,
                    CashMovement.target_account_id == account.id,
                ),
            )
        )
        for m in movements:
            incoming = m.target_account_id == account.id or m.kind not in OUTFLOWS
            detail = m.description or (m.expense_category.name if m.expense_category else "")
            if m.kind == CashMovementKind.TRANSFER:
                other = m.cash_account if incoming else m.target_account
                detail = f"{'desde' if incoming else 'a'} {other.name if other else ''}"
            label = f"{CASH_MOVEMENT_KIND_LABELS[m.kind]} {m.number} · {detail}".rstrip(" ·")
            entries.append((m.date, "movement", m.id, label, m.amount if incoming else -m.amount))
        entries.sort(key=lambda e: e[0])
        return entries

    def balances(self, at: date | None = None) -> list[CashBalanceOut]:
        accounts = self.session.scalars(
            select(CashAccount).where(CashAccount.is_active.is_(True)).order_by(CashAccount.name)
        )
        return [
            CashBalanceOut(
                account=Ref(id=a.id, name=a.name),
                kind=a.kind,
                balance=a.opening_balance
                + sum((e[4] for e in self._entries(a) if at is None or e[0] <= at), ZERO),
            )
            for a in accounts
        ]

    def statement(
        self, account_id: UUID, date_from: date | None, date_to: date | None
    ) -> CashStatementOut:
        account = self.session.get(CashAccount, account_id)
        if account is None:
            raise NotFoundError("No se encontró la cuenta.")
        entries = self._entries(account)
        opening = account.opening_balance + sum(
            (e[4] for e in entries if date_from and e[0] < date_from), ZERO
        )
        balance, rows = opening, []
        for day, source, id_, label, amount in entries:
            if (date_from and day < date_from) or (date_to and day > date_to):
                continue
            balance += amount
            rows.append(
                CashStatementRowOut(
                    date=day, source=source, id=id_, label=label, amount=amount, balance=balance
                )
            )
        return CashStatementOut(
            account=Ref(id=account.id, name=account.name),
            opening_balance=opening,
            rows=rows,
            closing_balance=balance,
        )
