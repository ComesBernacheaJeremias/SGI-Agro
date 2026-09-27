"""Endpoints de Comercial (compras, ventas, cobros, pagos, cuentas corrientes) y Caja."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy.orm import Session

from app.core.crud import CrudRepository, CrudService
from app.core.crud_router import CrudPermissions, crud_router
from app.core.db import DbSession
from app.core.pagination import Page, PageParams, Pagination
from app.core.schemas import Schema
from app.modules.commercial.cash_service import CashMovementService, CashQueries, MovementFilters
from app.modules.commercial.destinations import destination_out
from app.modules.commercial.document_service import CommercialDocumentService, DocumentFilters
from app.modules.commercial.ledger import (
    LedgerQueries,
    allocated_by_document,
    credited_by_document,
    pending_of,
)
from app.modules.commercial.models import (
    CASH_ACCOUNT_KIND_LABELS,
    CASH_MOVEMENT_KIND_LABELS,
    DOCUMENT_KIND_LABELS,
    PAYMENT_METHOD_LABELS,
    STATUS_LABELS,
    CashAccount,
    CashMovement,
    CashMovementKind,
    CommercialDocument,
    Direction,
    ExpenseCategory,
    Payment,
    Status,
)
from app.modules.commercial.payment_service import PaymentFilters, PaymentService
from app.modules.commercial.permissions import (
    CASH_READ,
    CASH_WRITE,
    COMMERCIAL_CANCEL,
    COMMERCIAL_READ,
    COMMERCIAL_WRITE,
)
from app.modules.commercial.schemas import (
    AllocationOut,
    BalanceOut,
    CashAccountIn,
    CashAccountOut,
    CashAccountUpdate,
    CashBalanceOut,
    CashMovementIn,
    CashMovementOut,
    CashStatementOut,
    CodeRef,
    CommercialDocumentIn,
    CommercialDocumentOut,
    CommercialDocumentSavedOut,
    CommercialDocumentSummaryOut,
    CommercialLineOut,
    ExpenseCategoryIn,
    ExpenseCategoryOut,
    ExpenseCategoryUpdate,
    LedgerOut,
    PaymentIn,
    PaymentLineOut,
    PaymentOut,
    Ref,
)
from app.modules.identity.authorization import require
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User
from app.modules.inventory.schemas import StockAlertOut
from app.modules.masterdata.schemas import Option

Reader = Annotated[User, require(COMMERCIAL_READ)]
Writer = Annotated[User, require(COMMERCIAL_WRITE)]
Canceller = Annotated[User, require(COMMERCIAL_CANCEL)]
CashReader = Annotated[User, require(CASH_READ)]
CashWriter = Annotated[User, require(CASH_WRITE)]
ZERO = Decimal(0)


# --- Configuración (piezas CRUD) ---


class ExpenseCategoryRepository(CrudRepository[ExpenseCategory]):
    model = ExpenseCategory
    search_fields = ("name",)


class ExpenseCategoryService(
    CrudService[ExpenseCategory, ExpenseCategoryIn, ExpenseCategoryUpdate]
):
    repository_class = ExpenseCategoryRepository
    unique_fields = {"name": "Ya existe la categoría '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró la categoría."


class CashAccountRepository(CrudRepository[CashAccount]):
    model = CashAccount
    search_fields = ("name",)


class CashAccountService(CrudService[CashAccount, CashAccountIn, CashAccountUpdate]):
    repository_class = CashAccountRepository
    unique_fields = {"name": "Ya existe la cuenta '{value}'."}  # noqa: RUF012
    not_found_message = "No se encontró la cuenta."


class CommercialOptions(Schema):
    document_kinds: list[Option]
    statuses: list[Option]
    payment_methods: list[Option]
    movement_kinds: list[Option]
    cash_account_kinds: list[Option]


def _options(labels: dict[Any, str]) -> list[Option]:
    return [Option(value=str(value), label=label) for value, label in labels.items()]


# --- Presentación ---


def _page[R](items: list[R], total: int, page: PageParams) -> Page[R]:
    return Page(items=items, total=total, page=page.page, page_size=page.page_size)


def document_summaries(
    db: Session, documents: list[CommercialDocument]
) -> list[CommercialDocumentSummaryOut]:
    ids = [d.id for d in documents]
    allocated = allocated_by_document(db, ids)
    credited = credited_by_document(db, ids)
    return [
        CommercialDocumentSummaryOut(
            **_summary_fields(d, allocated.get(d.id, ZERO), credited.get(d.id, ZERO))
        )
        for d in documents
    ]


def _summary_fields(d: CommercialDocument, allocated: Decimal, credited: Decimal) -> dict[str, Any]:
    return {
        "id": d.id,
        "direction": d.direction,
        "kind": d.kind,
        "internal_number": d.internal_number,
        "invoice_label": d.invoice_label,
        "has_invoice": d.has_invoice,
        "party": Ref(id=d.party.id, name=d.party.name),
        "date": d.date,
        "due_date": d.due_date,
        "status": d.status,
        "total": d.total,
        "allocated": allocated,
        "credited": credited,
        "pending": pending_of(d, allocated, credited),
    }


def document_out(db: Session, d: CommercialDocument) -> CommercialDocumentOut:
    allocated = allocated_by_document(db, [d.id]).get(d.id, ZERO)
    credited = credited_by_document(db, [d.id]).get(d.id, ZERO)
    related = d.related_document
    return CommercialDocumentOut(
        **_summary_fields(d, allocated, credited),
        related_document=Ref(id=related.id, name=related.invoice_label) if related else None,
        letter=d.letter,
        pos_number=d.pos_number,
        number=d.number,
        warehouse=Ref(id=d.warehouse.id, name=d.warehouse.name) if d.warehouse else None,
        net_total=d.net_total,
        vat_total=d.vat_total,
        other_taxes=d.other_taxes,
        notes=d.notes,
        stock_document_id=d.stock_document_id,
        lines=[
            CommercialLineOut(
                line_no=line.line_no,
                kind=line.kind,
                description=line.description,
                product=CodeRef(id=line.product.id, code=line.product.code, name=line.product.name)
                if line.product
                else None,
                unit=Ref(id=line.unit.id, name=line.unit.code) if line.unit else None,
                quantity=line.quantity,
                batch_id=line.batch_id,
                expense_category=Ref(id=line.expense_category.id, name=line.expense_category.name)
                if line.expense_category
                else None,
                destination=destination_out(db, line),
                unit_price=line.unit_price,
                vat_rate=line.vat_rate,
                net_amount=line.net_amount,
                vat_amount=line.vat_amount,
            )
            for line in d.lines
        ],
    )


def _saved(
    db: Session, document: CommercialDocument, alerts: list[StockAlertOut]
) -> CommercialDocumentSavedOut:
    return CommercialDocumentSavedOut(document=document_out(db, document), alerts=alerts)


def payment_out(p: Payment) -> PaymentOut:
    allocated = sum((a.amount for a in p.allocations), ZERO)
    return PaymentOut(
        id=p.id,
        direction=p.direction,
        number=p.number,
        party=Ref(id=p.party.id, name=p.party.name),
        date=p.date,
        total=p.total,
        allocated=allocated,
        unallocated=p.total - allocated,
        status=p.status,
        notes=p.notes,
        lines=[
            PaymentLineOut(
                method=line.method,
                cash_account=Ref(id=line.cash_account.id, name=line.cash_account.name),
                amount=line.amount,
                reference=line.reference,
            )
            for line in p.lines
        ],
        allocations=[
            AllocationOut(
                document_id=a.document_id, invoice_label=a.document.invoice_label, amount=a.amount
            )
            for a in p.allocations
        ],
    )


def movement_out(db: Session, m: CashMovement) -> CashMovementOut:
    return CashMovementOut(
        id=m.id,
        number=m.number,
        date=m.date,
        kind=m.kind,
        cash_account=Ref(id=m.cash_account.id, name=m.cash_account.name),
        target_account=Ref(id=m.target_account.id, name=m.target_account.name)
        if m.target_account
        else None,
        amount=m.amount,
        description=m.description,
        expense_category=Ref(id=m.expense_category.id, name=m.expense_category.name)
        if m.expense_category
        else None,
        destination=destination_out(db, m),
        status=m.status,
    )


# --- Opciones ---

options_router = APIRouter(prefix="/api/v1/commercial-options", tags=["commercial"])


@options_router.get("")
def commercial_options(_: CurrentUser) -> CommercialOptions:
    return CommercialOptions(
        document_kinds=_options(DOCUMENT_KIND_LABELS),
        statuses=_options(STATUS_LABELS),
        payment_methods=_options(PAYMENT_METHOD_LABELS),
        movement_kinds=_options(CASH_MOVEMENT_KIND_LABELS),
        cash_account_kinds=_options(CASH_ACCOUNT_KIND_LABELS),
    )


# --- Comprobantes ---

documents_router = APIRouter(prefix="/api/v1/commercial-documents", tags=["commercial"])


@documents_router.get("")
def list_documents(
    db: DbSession,
    _: Reader,
    page: Pagination,
    direction: Direction,
    party_id: UUID | None = None,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    only_pending: bool = False,
) -> Page[CommercialDocumentSummaryOut]:
    filters = DocumentFilters(direction, party_id, status_, date_from, date_to, q, only_pending)
    items, total = CommercialDocumentService(db).search(filters, page)
    return _page(document_summaries(db, items), total, page)


@documents_router.get("/{id_}")
def get_document(id_: UUID, db: DbSession, _: Reader) -> CommercialDocumentOut:
    return document_out(db, CommercialDocumentService(db).get(id_))


@documents_router.post("", status_code=status.HTTP_201_CREATED)
def create_document(
    body: CommercialDocumentIn, db: DbSession, _: Writer
) -> CommercialDocumentSavedOut:
    return _saved(db, *CommercialDocumentService(db).create(body))


@documents_router.put("/{id_}")
def update_document(
    id_: UUID, body: CommercialDocumentIn, db: DbSession, _: Writer
) -> CommercialDocumentSavedOut:
    return _saved(db, *CommercialDocumentService(db).update(id_, body))


@documents_router.post("/{id_}/cancel")
def cancel_document(id_: UUID, db: DbSession, _: Canceller) -> CommercialDocumentSavedOut:
    return _saved(db, *CommercialDocumentService(db).cancel(id_))


# --- Cobros y pagos ---

payments_router = APIRouter(prefix="/api/v1/payments", tags=["commercial"])


@payments_router.get("")
def list_payments(
    db: DbSession,
    _: Reader,
    page: Pagination,
    direction: Direction,
    party_id: UUID | None = None,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[PaymentOut]:
    filters = PaymentFilters(direction, party_id, status_, date_from, date_to)
    items, total = PaymentService(db).search(filters, page)
    return _page([payment_out(p) for p in items], total, page)


@payments_router.get("/{id_}")
def get_payment(id_: UUID, db: DbSession, _: Reader) -> PaymentOut:
    return payment_out(PaymentService(db).get(id_))


@payments_router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: DbSession, _: Writer) -> PaymentOut:
    return payment_out(PaymentService(db).create(body))


@payments_router.put("/{id_}")
def update_payment(id_: UUID, body: PaymentIn, db: DbSession, _: Writer) -> PaymentOut:
    return payment_out(PaymentService(db).update(id_, body))


@payments_router.post("/{id_}/cancel")
def cancel_payment(id_: UUID, db: DbSession, _: Canceller) -> PaymentOut:
    return payment_out(PaymentService(db).cancel(id_))


# --- Cuentas corrientes ---

accounts_router = APIRouter(prefix="/api/v1/current-accounts", tags=["commercial"])


@accounts_router.get("")
def list_balances(db: DbSession, _: Reader, direction: Direction) -> list[BalanceOut]:
    return LedgerQueries(db).balances(direction)


@accounts_router.get("/{party_id}")
def get_ledger(
    party_id: UUID,
    db: DbSession,
    _: Reader,
    direction: Direction,
    date_from: date | None = None,
    date_to: date | None = None,
) -> LedgerOut:
    return LedgerQueries(db).ledger(party_id, direction, date_from, date_to)


# --- Caja y bancos ---

cash_router = APIRouter(prefix="/api/v1/cash", tags=["cash"])


@cash_router.get("/balances")
def cash_balances(db: DbSession, _: CashReader, at: date | None = None) -> list[CashBalanceOut]:
    return CashQueries(db).balances(at)


@cash_router.get("/accounts/{id_}/statement")
def cash_statement(
    id_: UUID,
    db: DbSession,
    _: CashReader,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CashStatementOut:
    return CashQueries(db).statement(id_, date_from, date_to)


@cash_router.get("/movements")
def list_movements(
    db: DbSession,
    _: CashReader,
    page: Pagination,
    cash_account_id: UUID | None = None,
    kind: CashMovementKind | None = None,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[CashMovementOut]:
    filters = MovementFilters(cash_account_id, kind, status_, date_from, date_to)
    items, total = CashMovementService(db).search(filters, page)
    return _page([movement_out(db, m) for m in items], total, page)


@cash_router.get("/movements/{id_}")
def get_movement(id_: UUID, db: DbSession, _: CashReader) -> CashMovementOut:
    return movement_out(db, CashMovementService(db).get(id_))


@cash_router.post("/movements", status_code=status.HTTP_201_CREATED)
def create_movement(body: CashMovementIn, db: DbSession, _: CashWriter) -> CashMovementOut:
    return movement_out(db, CashMovementService(db).create(body))


@cash_router.put("/movements/{id_}")
def update_movement(
    id_: UUID, body: CashMovementIn, db: DbSession, _: CashWriter
) -> CashMovementOut:
    return movement_out(db, CashMovementService(db).update(id_, body))


@cash_router.post("/movements/{id_}/cancel")
def cancel_movement(id_: UUID, db: DbSession, _: CashWriter) -> CashMovementOut:
    return movement_out(db, CashMovementService(db).cancel(id_))


routers = [
    options_router,
    documents_router,
    payments_router,
    accounts_router,
    cash_router,
    crud_router(
        prefix="/api/v1/expense-categories",
        tag="commercial",
        service=ExpenseCategoryService,
        out=ExpenseCategoryOut,
        create=ExpenseCategoryIn,
        update=ExpenseCategoryUpdate,
        permissions=CrudPermissions(
            read=COMMERCIAL_READ, write=COMMERCIAL_WRITE, deactivate=COMMERCIAL_WRITE
        ),
    ),
    crud_router(
        prefix="/api/v1/cash-accounts",
        tag="cash",
        service=CashAccountService,
        out=CashAccountOut,
        create=CashAccountIn,
        update=CashAccountUpdate,
        permissions=CrudPermissions(read=CASH_READ, write=CASH_WRITE, deactivate=CASH_WRITE),
    ),
]
