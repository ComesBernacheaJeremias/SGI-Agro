from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.db import DbSession
from app.core.errors import ForbiddenError
from app.core.pagination import Page, Pagination
from app.core.permissions import Permission
from app.modules.identity.authorization import effective_permissions, require
from app.modules.identity.models import User
from app.modules.inventory.models import (
    DOCUMENT_TYPE_LABELS,
    STATUS_LABELS,
    DocumentStatus,
    DocumentType,
    StockDocument,
)
from app.modules.inventory.permissions import (
    INVENTORY_ADJUST,
    INVENTORY_CANCEL,
    INVENTORY_READ,
    INVENTORY_WRITE,
)
from app.modules.inventory.queries import StockFilters, StockQueries
from app.modules.inventory.schemas import (
    BatchStockOut,
    DocumentIn,
    DocumentOut,
    DocumentSavedOut,
    DocumentSummaryOut,
    InventoryOptions,
    KardexOut,
    StockAlertOut,
    StockRowOut,
)
from app.modules.inventory.service import (
    DocumentFilters,
    StockDocumentService,
    search_documents,
    to_out,
    to_summary,
)
from app.modules.masterdata.schemas import Option

documents_router = APIRouter(prefix="/api/v1/stock-documents", tags=["inventory"])
stock_router = APIRouter(prefix="/api/v1/stock", tags=["inventory"])

Reader = Annotated[User, require(INVENTORY_READ)]
Writer = Annotated[User, require(INVENTORY_WRITE)]
Canceller = Annotated[User, require(INVENTORY_CANCEL)]


def _ensure_can_write_type(user: User, document_type: DocumentType) -> None:
    """Los ajustes necesitan un permiso aparte (ADR: tapan faltantes)."""
    needed: Permission = (
        INVENTORY_ADJUST if document_type == DocumentType.ADJUSTMENT else INVENTORY_WRITE
    )
    if needed.code not in effective_permissions(user.role):
        raise ForbiddenError(f"No tenés permiso para: {needed.group} → {needed.label}.")


def _saved(
    service: StockDocumentService, result: tuple[StockDocument, list[StockAlertOut]]
) -> DocumentSavedOut:
    document, alerts = result
    return DocumentSavedOut(document=to_out(document, service.moves_of(document.id)), alerts=alerts)


# --- Comprobantes ---


@documents_router.get("")
def list_documents(
    db: DbSession,
    _: Reader,
    page: Pagination,
    type: DocumentType | None = None,
    status_: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    warehouse_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
) -> Page[DocumentSummaryOut]:
    filters = DocumentFilters(type, status_, warehouse_id, date_from, date_to, q)
    items, total = search_documents(db, filters, page)
    return Page(
        items=[to_summary(d) for d in items], total=total, page=page.page, page_size=page.page_size
    )


@documents_router.get("/{id_}")
def get_document(id_: UUID, db: DbSession, _: Reader) -> DocumentOut:
    service = StockDocumentService(db)
    return to_out(service.get(id_), service.moves_of(id_))


@documents_router.post("", status_code=status.HTTP_201_CREATED)
def create_document(body: DocumentIn, db: DbSession, user: Writer) -> DocumentSavedOut:
    _ensure_can_write_type(user, body.type)
    service = StockDocumentService(db)
    return _saved(service, service.create(body))


@documents_router.put("/{id_}")
def update_document(id_: UUID, body: DocumentIn, db: DbSession, user: Writer) -> DocumentSavedOut:
    _ensure_can_write_type(user, body.type)
    service = StockDocumentService(db)
    return _saved(service, service.update(id_, body))


@documents_router.post("/{id_}/cancel")
def cancel_document(id_: UUID, db: DbSession, user: Canceller) -> DocumentSavedOut:
    service = StockDocumentService(db)
    _ensure_can_write_type(user, service.get(id_).type)
    return _saved(service, service.cancel(id_))


# --- Stock ---


@stock_router.get("")
def list_stock(
    db: DbSession,
    _: Reader,
    page: Pagination,
    at: date | None = None,
    q: str | None = None,
    category_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    by_warehouse: bool = False,
    below_min: bool = False,
    include_zero: bool = False,
) -> Page[StockRowOut]:
    filters = StockFilters(at, q, category_id, warehouse_id, by_warehouse, below_min, include_zero)
    items, total = StockQueries(db).stock(filters, page)
    return Page(items=items, total=total, page=page.page, page_size=page.page_size)


@stock_router.get("/alerts")
def stock_alerts(db: DbSession, _: Reader) -> list[StockAlertOut]:
    """Productos en su stock mínimo o por debajo ("Necesitás comprar")."""
    return StockQueries(db).alerts()


@stock_router.get("/kardex")
def kardex(
    db: DbSession,
    _: Reader,
    product_id: UUID,
    warehouse_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> KardexOut:
    return StockQueries(db).kardex(product_id, warehouse_id, date_from, date_to)


@stock_router.get("/batches")
def stock_batches(
    db: DbSession,
    _: Reader,
    product_id: UUID,
    warehouse_id: UUID,
    at: date | None = None,
    exclude_document_id: UUID | None = None,
    only_available: bool = True,
) -> list[BatchStockOut]:
    """Partidas del producto en el almacén, de la más vieja a la más nueva (para vender o
    devolver). `only_available=false` incluye las que ya no tienen stock."""
    return StockQueries(db).batch_balances(
        product_id, warehouse_id, at or date.today(), exclude_document_id, only_available
    )


@stock_router.get("/options")
def inventory_options(_: Reader) -> InventoryOptions:
    return InventoryOptions(
        document_types=[Option(value=str(k), label=v) for k, v in DOCUMENT_TYPE_LABELS.items()],
        statuses=[Option(value=str(k), label=v) for k, v in STATUS_LABELS.items()],
    )


routers = [documents_router, stock_router]
