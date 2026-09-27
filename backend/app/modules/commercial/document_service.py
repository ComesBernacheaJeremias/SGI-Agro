"""Comprobantes de compra y venta.

Stock (comprobante de sistema, ADR-016):
  - Compra (factura/ND): entrada al costo del precio neto · NC de compra: devolución (salida).
  - Venta (factura/ND): salida a costo promedio · NC de venta: devolución (entrada).
  - Venta de producción propia: sale por partida (la elegida o, si no, las más antiguas
    primero) → permite la rentabilidad por ciclo (ADR-012).
Gastos: líneas con categoría y destino opcional; cuentan como costo del destino (F5).
Editar/anular: si el total baja de lo ya cobrado/pagado, se desimputa el excedente
(queda como anticipo en el cobro/pago).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import ScalarSelect, and_, func, or_, select
from sqlalchemy.orm import Session, aliased
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.formatting import format_money
from app.core.pagination import PageParams, paginate
from app.core.sequences import next_number
from app.modules.commercial.destinations import (
    DIMENSIONS,
    ensure_destination_open,
    resolve_destination,
)
from app.modules.commercial.ledger import credited_by_document, default_due_date
from app.modules.commercial.models import (
    Allocation,
    CommercialDocument,
    CommercialLine,
    Direction,
    DocumentKind,
    ExpenseCategory,
    LineKind,
    Payment,
    Status,
)
from app.modules.commercial.schemas import CommercialDocumentIn, CommercialLineIn
from app.modules.inventory.models import CostMode, DocumentType
from app.modules.inventory.queries import StockQueries
from app.modules.inventory.schemas import StockAlertOut
from app.modules.inventory.service import LineSpec, MoveSpec, StockDocumentService
from app.modules.masterdata.models import Party, ProductType
from app.modules.production.models import Batch

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")
ZERO = Decimal(0)
SOURCE = "commercial"
PREFIX = {Direction.PURCHASE: "CPR", Direction.SALE: "VTA"}


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _applied_subquery() -> ScalarSelect[Decimal]:
    """Cobrado/pagado + NC asociadas de cada comprobante (para filtrar pendientes)."""
    credit = aliased(CommercialDocument)
    allocated = (
        select(func.coalesce(func.sum(Allocation.amount), 0))
        .join(Payment, Payment.id == Allocation.payment_id)
        .where(Allocation.document_id == CommercialDocument.id, Payment.status == Status.ACTIVE)
        .correlate(CommercialDocument)
        .scalar_subquery()
    )
    credited = (
        select(func.coalesce(func.sum(credit.total), 0))
        .where(
            credit.related_document_id == CommercialDocument.id,
            credit.kind == DocumentKind.CREDIT_NOTE,
            credit.status == Status.ACTIVE,
        )
        .correlate(CommercialDocument)
        .scalar_subquery()
    )
    return (allocated + credited).label("applied")  # type: ignore[return-value]


@dataclass(frozen=True)
class DocumentFilters:
    direction: Direction
    party_id: UUID | None = None
    status: Status | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    only_pending: bool = False


class CommercialDocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.stock = StockDocumentService(session)

    def get(self, id_: UUID) -> CommercialDocument:
        document = self.session.get(CommercialDocument, id_)
        if document is None:
            raise NotFoundError("No se encontró el comprobante.")
        return document

    def search(self, f: DocumentFilters, page: PageParams) -> tuple[list[CommercialDocument], int]:
        query = (
            select(CommercialDocument)
            .where(CommercialDocument.direction == f.direction)
            .order_by(CommercialDocument.date.desc(), CommercialDocument.internal_number.desc())
        )
        if f.party_id:
            query = query.where(CommercialDocument.party_id == f.party_id)
        if f.status:
            query = query.where(CommercialDocument.status == f.status)
        if f.date_from:
            query = query.where(CommercialDocument.date >= f.date_from)
        if f.date_to:
            query = query.where(CommercialDocument.date <= f.date_to)
        if f.q:
            pattern = f"%{f.q.strip()}%"
            query = query.join(Party).where(
                or_(
                    CommercialDocument.internal_number.ilike(pattern),
                    CommercialDocument.number.ilike(pattern),
                    Party.name.ilike(pattern),
                )
            )
        if f.only_pending:
            query = query.where(
                CommercialDocument.status == Status.ACTIVE,
                CommercialDocument.kind != DocumentKind.CREDIT_NOTE,
                CommercialDocument.total > _applied_subquery(),
            )
        return paginate(self.session, query, page)

    # --- Alta / edición / anulación ---

    def create(self, data: CommercialDocumentIn) -> tuple[CommercialDocument, list[StockAlertOut]]:
        party = self._validate(data, document_id=None)
        document = CommercialDocument(
            id=uuid7(),
            direction=data.direction,
            internal_number=next_number(self.session, PREFIX[data.direction]),
        )
        self.session.add(document)
        self._fill(document, data, party)
        self.session.flush()
        self._apply_credit(document)
        return document, self._sync_stock(document)

    def create_opening(
        self,
        *,
        direction: Direction,
        party: Party,
        day: date,
        due_date: date | None,
        reference: str,
        amount: Decimal,
    ) -> CommercialDocument:
        """Saldo inicial de cuenta corriente (importación): una línea sin IVA ni stock.
        Importe negativo = saldo a favor del tercero (nota de crédito)."""
        document = CommercialDocument(
            id=uuid7(),
            direction=direction,
            kind=DocumentKind.CREDIT_NOTE if amount < 0 else DocumentKind.INVOICE,
            internal_number=next_number(self.session, PREFIX[direction]),
            is_opening_balance=True,
            has_invoice=False,
            party_id=party.id,
            party=party,
            date=day,
            due_date=due_date or default_due_date(party, day),
            notes=reference,
            net_total=abs(amount),
            vat_total=ZERO,
            other_taxes=ZERO,
            total=abs(amount),
        )
        document.lines.append(
            CommercialLine(
                line_no=1,
                kind=LineKind.EXPENSE,
                description="Saldo inicial",
                quantity=Decimal(1),
                unit_price=abs(amount),
                vat_rate=ZERO,
                net_amount=abs(amount),
                vat_amount=ZERO,
            )
        )
        self.session.add(document)
        self.session.flush()
        return document

    def update(
        self, id_: UUID, data: CommercialDocumentIn
    ) -> tuple[CommercialDocument, list[StockAlertOut]]:
        document = self._editable(id_)
        if document.is_opening_balance:
            raise BusinessRuleError(
                "Un saldo inicial no se edita: anulalo y cargalo de nuevo.", code="OPENING_BALANCE"
            )
        if data.direction != document.direction:
            raise BusinessRuleError(
                "No se puede cambiar una compra por una venta.", code="DIRECTION"
            )
        party = self._validate(data, document_id=document.id)
        if data.party_id != document.party_id and self._allocations(document.id):
            raise BusinessRuleError(
                "El comprobante tiene cobros/pagos imputados: no se puede cambiar el tercero.",
                code="HAS_ALLOCATIONS",
            )
        document.lines.clear()
        self._fill(document, data, party)
        self.session.flush()
        self._trim_allocations(document, document.total - self._credited(document.id))
        self._apply_credit(document)
        return document, self._sync_stock(document)

    def cancel(self, id_: UUID) -> tuple[CommercialDocument, list[StockAlertOut]]:
        document = self._editable(id_)
        if self._credited(document.id):
            raise BusinessRuleError(
                "Tiene notas de crédito asociadas: anulalas primero.", code="HAS_CREDIT_NOTES"
            )
        document.status = Status.CANCELLED
        self._trim_allocations(document, ZERO)
        self.session.flush()
        alerts = (
            self.stock.cancel_system(document.stock_document_id)
            if document.stock_document_id
            else []
        )
        return document, alerts

    # --- Validación ---

    def _editable(self, id_: UUID) -> CommercialDocument:
        document = self.get(id_)
        if document.status == Status.CANCELLED:
            raise BusinessRuleError("El comprobante está anulado.", code="CANCELLED")
        for line in document.lines:
            ensure_destination_open(self.session, line)
        return document

    def _validate(self, data: CommercialDocumentIn, document_id: UUID | None) -> Party:
        party = self.session.get(Party, data.party_id)
        if party is None or not party.is_active:
            raise BusinessRuleError("El cliente/proveedor no existe o está inactivo.", code="PARTY")
        if data.direction == Direction.SALE and not party.is_customer:
            raise BusinessRuleError(
                f"'{party.name}' no está marcado como cliente.", code="PARTY_ROLE"
            )
        if data.direction == Direction.PURCHASE and not party.is_supplier:
            raise BusinessRuleError(
                f"'{party.name}' no está marcado como proveedor.", code="PARTY_ROLE"
            )
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        if data.has_invoice:
            self._validate_invoice_number(data, document_id)
        if data.related_document_id:
            self._validate_related(data, document_id)
        has_products = any(line.kind == LineKind.PRODUCT for line in data.lines)
        if has_products and data.warehouse_id is None:
            raise BusinessRuleError(
                "Elegí el almacén para los productos.", code="WAREHOUSE_REQUIRED"
            )
        if has_products and data.kind == DocumentKind.DEBIT_NOTE:
            raise BusinessRuleError(
                "Una nota de débito no mueve mercadería: cargá conceptos de gasto o ajuste.",
                code="DEBIT_NOTE_PRODUCTS",
            )
        for line in data.lines:
            if line.kind == LineKind.PRODUCT and (line.product_id is None or line.unit_id is None):
                raise BusinessRuleError(
                    "Elegí producto y unidad en cada línea.", code="LINE_PRODUCT"
                )
            if (
                line.kind == LineKind.EXPENSE
                and data.direction == Direction.SALE
                and not line.description
            ):
                raise BusinessRuleError(
                    "Describí el concepto de la línea.", code="LINE_DESCRIPTION"
                )
            if line.kind == LineKind.EXPENSE and data.direction == Direction.PURCHASE:
                category = (
                    self.session.get(ExpenseCategory, line.expense_category_id)
                    if line.expense_category_id
                    else None
                )
                if category is None:
                    raise BusinessRuleError(
                        "Elegí la categoría de cada gasto.", code="EXPENSE_CATEGORY"
                    )
        return party

    def _validate_invoice_number(
        self, data: CommercialDocumentIn, document_id: UUID | None
    ) -> None:
        if data.letter not in ("A", "B", "C", "M", "E") or not data.pos_number or not data.number:
            raise BusinessRuleError(
                "Completá letra (A, B, C, M o E), punto de venta y número de la factura.",
                code="INVOICE_NUMBER",
            )
        conditions = [
            CommercialDocument.direction == data.direction,
            CommercialDocument.kind == data.kind,
            CommercialDocument.letter == data.letter,
            CommercialDocument.pos_number == data.pos_number.zfill(5),
            CommercialDocument.number == data.number.zfill(8),
            CommercialDocument.status == Status.ACTIVE,
        ]
        if data.direction == Direction.PURCHASE:  # el número es único por proveedor
            conditions.append(CommercialDocument.party_id == data.party_id)
        if document_id:
            conditions.append(CommercialDocument.id != document_id)
        if self.session.scalar(select(CommercialDocument.id).where(and_(*conditions))):
            raise BusinessRuleError("Ese comprobante ya está cargado.", code="DUPLICATE")

    def _validate_related(self, data: CommercialDocumentIn, document_id: UUID | None) -> None:
        related = self.session.get(CommercialDocument, data.related_document_id)
        if data.kind == DocumentKind.INVOICE:
            raise BusinessRuleError(
                "Solo una nota de crédito o débito lleva comprobante asociado.", code="RELATED"
            )
        if (
            related is None
            or related.id == document_id
            or related.status != Status.ACTIVE
            or related.party_id != data.party_id
            or related.direction != data.direction
            or related.kind == DocumentKind.CREDIT_NOTE
        ):
            raise BusinessRuleError(
                "El comprobante asociado tiene que ser una factura o nota de débito vigente "
                "del mismo cliente/proveedor.",
                code="RELATED",
            )

    def _credited(self, document_id: UUID, exclude_id: UUID | None = None) -> Decimal:
        credited = credited_by_document(self.session, [document_id]).get(document_id, ZERO)
        if exclude_id:
            other = self.session.get(CommercialDocument, exclude_id)
            if other and other.related_document_id == document_id and other.status == Status.ACTIVE:
                credited -= other.total
        return credited

    def _apply_credit(self, document: CommercialDocument) -> None:
        """NC asociada: no puede superar lo que queda del comprobante sin otras NC; si ya
        estaba cobrado/pagado, se desimputa el excedente (queda como anticipo)."""
        if document.kind != DocumentKind.CREDIT_NOTE or document.related_document_id is None:
            return
        related = self.get(document.related_document_id)
        available = related.total - self._credited(related.id, exclude_id=document.id)
        if document.total > available:
            raise BusinessRuleError(
                f"La nota de crédito supera lo que queda de {related.invoice_label} "
                f"({format_money(available)}).",
                code="CREDIT_EXCEEDS",
            )
        self._trim_allocations(related, related.total - self._credited(related.id))

    # --- Armado ---

    def _fill(self, document: CommercialDocument, data: CommercialDocumentIn, party: Party) -> None:
        document.kind = data.kind
        document.has_invoice = data.has_invoice
        document.letter = data.letter if data.has_invoice else ""
        document.pos_number = data.pos_number.zfill(5) if data.has_invoice else ""
        document.number = data.number.zfill(8) if data.has_invoice else ""
        document.party_id = party.id
        document.party = party
        document.date = data.date
        document.due_date = data.due_date or default_due_date(party, data.date)
        document.warehouse_id = data.warehouse_id
        document.related_document_id = data.related_document_id
        document.other_taxes = data.other_taxes
        document.notes = data.notes
        net = vat = ZERO
        for line_no, item in enumerate(data.lines, start=1):
            line = self._line(line_no, item, data)
            document.lines.append(line)
            net += line.net_amount
            vat += line.vat_amount
        document.net_total, document.vat_total = net, vat
        document.total = net + vat + data.other_taxes

    def _line(
        self, line_no: int, item: CommercialLineIn, data: CommercialDocumentIn
    ) -> CommercialLine:
        net = _money(item.quantity * item.unit_price)
        line = CommercialLine(
            line_no=line_no,
            kind=item.kind,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            vat_rate=item.vat_rate,
            net_amount=net,
            vat_amount=_money(net * item.vat_rate / 100),
        )
        if item.kind == LineKind.PRODUCT:
            spec = self.stock.line(item.product_id, item.unit_id, item.quantity)  # type: ignore[arg-type]
            line.product, line.product_id = spec.product, spec.product.id
            line.unit, line.unit_id = spec.unit, spec.unit.id
            line.batch_id = item.batch_id if data.direction == Direction.SALE else None
        else:
            category = (
                self.session.get(ExpenseCategory, item.expense_category_id)
                if item.expense_category_id
                else None
            )
            line.expense_category = category
            line.expense_category_id = category.id if category else None
            if data.direction == Direction.PURCHASE:
                for field, value in resolve_destination(self.session, item).items():
                    setattr(line, field, value)
        return line

    # --- Stock ---

    def _sync_stock(self, document: CommercialDocument) -> list[StockAlertOut]:
        lines = [
            self._stock_line(document, line)
            for line in document.lines
            if line.kind == LineKind.PRODUCT
        ]
        if not lines:
            if document.stock_document_id:
                alerts = self.stock.cancel_system(document.stock_document_id)
                document.stock_document_id = None
                return alerts
            return []
        assert document.warehouse_id is not None  # noqa: S101 (validado)
        is_sale = document.direction == Direction.SALE
        label = "Venta" if is_sale else "Compra"
        stock_doc, alerts = self.stock.save_system(
            document_id=document.stock_document_id,
            type_=DocumentType.SALE if is_sale else DocumentType.PURCHASE,
            date_=document.date,
            warehouse_id=document.warehouse_id,
            source_module=SOURCE,
            source_id=document.id,
            lines=lines,
            notes=f"{label} {document.internal_number} · {document.party.name}",
        )
        document.stock_document_id = stock_doc.id
        self.session.flush()
        return alerts

    def _stock_line(self, document: CommercialDocument, line: CommercialLine) -> LineSpec:
        assert line.product_id and line.unit_id and document.warehouse_id  # noqa: S101
        spec = self.stock.line(line.product_id, line.unit_id, line.quantity)
        base = spec.base_quantity
        warehouse = document.warehouse_id
        returning = document.kind == DocumentKind.CREDIT_NOTE
        if document.direction == Direction.PURCHASE:
            if returning:  # devolución al proveedor
                spec.moves = [MoveSpec(warehouse, -base, CostMode.AVERAGE)]
            else:
                cost = (line.unit_price / spec.factor).quantize(Decimal("0.000001"))
                spec.unit_cost = line.unit_price
                spec.moves = [MoveSpec(warehouse, base, CostMode.OWN, cost)]
        elif returning:  # devolución del cliente (a su partida, si se indicó)
            dims: dict[str, UUID | None] = (
                {"batch_id": self._batch_of(line)} if line.batch_id else {}
            )
            spec.moves = [MoveSpec(warehouse, base, CostMode.AVERAGE, dimensions=dims)]
        else:
            spec.moves = self._sale_moves(document, line, base)
        return spec

    def _sale_moves(
        self, document: CommercialDocument, line: CommercialLine, base: Decimal
    ) -> list[MoveSpec]:
        """Salida de venta; producción propia: por partida (la elegida o las más antiguas)."""
        warehouse = document.warehouse_id
        assert warehouse is not None and line.product is not None  # noqa: S101
        if line.product.type != ProductType.OWN_PRODUCE:
            return [MoveSpec(warehouse, -base, CostMode.AVERAGE)]
        balances = StockQueries(self.session).batch_balances(
            line.product.id,
            warehouse,
            document.date,
            exclude_document_id=document.stock_document_id,
        )
        batches = [(b.id, b.quantity) for b in balances]
        if line.batch_id:
            available = dict(batches).get(line.batch_id, ZERO)
            if available < base:
                raise BusinessRuleError(
                    f"La partida elegida de {line.product.name} no tiene stock suficiente.",
                    code="BATCH_STOCK",
                )
            batches = [(line.batch_id, available)]
        moves, remaining = [], base
        for batch_id, available in batches:
            if remaining <= 0:
                break
            taken = min(available, remaining)
            moves.append(
                MoveSpec(warehouse, -taken, CostMode.AVERAGE, dimensions={"batch_id": batch_id})
            )
            remaining -= taken
        if remaining > 0:  # producción sin partida (ej. stock inicial cargado a mano)
            moves.append(MoveSpec(warehouse, -remaining, CostMode.AVERAGE))
        return moves

    def _batch_of(self, line: CommercialLine) -> UUID:
        batch = self.session.get(Batch, line.batch_id)
        if batch is None or batch.product_id != line.product_id:
            raise BusinessRuleError("La partida no corresponde al producto.", code="BATCH")
        return batch.id

    # --- Imputaciones ---

    def _allocations(self, document_id: UUID) -> list[Allocation]:
        return list(
            self.session.scalars(
                select(Allocation)
                .join(Payment)
                .where(Allocation.document_id == document_id, Payment.status == Status.ACTIVE)
                .order_by(Payment.date.desc(), Payment.number.desc())
            )
        )

    def _trim_allocations(self, document: CommercialDocument, limit: Decimal) -> None:
        """Si lo imputado supera `limit`, se desimputa desde el cobro/pago más reciente."""
        excess = sum((a.amount for a in self._allocations(document.id)), ZERO) - max(limit, ZERO)
        for allocation in self._allocations(document.id):
            if excess <= 0:
                break
            reduce = min(allocation.amount, excess)
            allocation.amount -= reduce
            excess -= reduce
            if allocation.amount == 0:
                self.session.delete(allocation)
        self.session.flush()


def line_dimensions(line: CommercialLine) -> dict[str, UUID | None]:
    return {field: getattr(line, field) for field in DIMENSIONS}
