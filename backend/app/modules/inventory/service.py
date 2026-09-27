"""Comprobantes de stock.

- Manuales (pantalla de Inventario): ingreso, egreso, transferencia, ajuste por conteo.
- De sistema (los arman otros módulos: labores, cosechas, elaboración): `save_system` /
  `cancel_system`. Se editan solo desde su origen.

Flujo común: validar → bloquear productos → cabecera + líneas (una entrada en el historial)
→ movimientos (unidad base, signo, costo, dimensiones) → recalcular desde la fecha afectada
→ devolver el comprobante + alertas de stock mínimo.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.core.sequences import next_number
from app.modules.inventory.engine import COST_PRECISION, StockEngine
from app.modules.inventory.models import (
    DOCUMENT_PREFIXES,
    MANUAL_TYPES,
    CostMode,
    DocumentStatus,
    DocumentType,
    StockDocument,
    StockDocumentLine,
    StockMove,
)
from app.modules.inventory.queries import StockQueries
from app.modules.inventory.schemas import (
    DocumentIn,
    DocumentOut,
    DocumentSummaryOut,
    LineOut,
    ProductRef,
    Ref,
    StockAlertOut,
    UnitCode,
)
from app.modules.masterdata.models import Party, Product, ProductType, Unit, Warehouse
from app.modules.masterdata.units import unit_factor

ZERO = Decimal(0)


@dataclass
class MoveSpec:
    """Un movimiento a generar (cantidad en unidad base, con signo)."""

    warehouse_id: UUID
    quantity: Decimal
    cost_mode: CostMode
    unit_cost: Decimal = ZERO  # por unidad base; solo para CostMode.OWN
    # Dimensiones: farm_id, plot_id, crop_cycle_id, field_operation_id, asset_id, batch_id
    dimensions: dict[str, UUID | None] = field(default_factory=dict)


@dataclass
class LineSpec:
    """Una línea tal como se cargó + los movimientos que genera."""

    product: Product
    unit: Unit
    quantity: Decimal
    factor: Decimal
    unit_cost: Decimal | None = None  # por unidad cargada (solo se muestra)
    moves: list[MoveSpec] = field(default_factory=list)

    @property
    def base_quantity(self) -> Decimal:
        return self.quantity * self.factor


class StockDocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.engine = StockEngine(session)
        self.queries = StockQueries(session)

    # --- Lectura ---

    def get(self, id_: UUID) -> StockDocument:
        document = self.session.get(StockDocument, id_)
        if document is None:
            raise NotFoundError("No se encontró el comprobante.")
        return document

    def moves_of(self, document_id: UUID) -> list[StockMove]:
        return list(
            self.session.scalars(
                select(StockMove)
                .where(StockMove.document_id == document_id)
                .order_by(StockMove.line_no, StockMove.sub_no)
            )
        )

    def line(self, product_id: UUID, unit_id: UUID, quantity: Decimal) -> LineSpec:
        """Valida producto y unidad y arma la línea (sin movimientos). Para otros módulos."""
        product = self.session.get(Product, product_id)
        unit = self.session.get(Unit, unit_id)
        if product is None or unit is None:
            raise NotFoundError("Un producto o unidad no existe.")
        if product.type == ProductType.SERVICE:
            raise BusinessRuleError(
                f"'{product.name}' es un servicio: no maneja stock.", code="SERVICE_PRODUCT"
            )
        if not product.is_active:
            raise BusinessRuleError(f"'{product.name}' está inactivo.", code="INACTIVE_PRODUCT")
        return LineSpec(product, unit, quantity, unit_factor(product, unit))

    def active_warehouse(self, id_: UUID) -> Warehouse:
        warehouse = self.session.get(Warehouse, id_)
        if warehouse is None or not warehouse.is_active:
            raise BusinessRuleError("El almacén no existe o está inactivo.", code="WAREHOUSE")
        return warehouse

    # --- Comprobantes manuales ---

    def create(self, data: DocumentIn) -> tuple[StockDocument, list[StockAlertOut]]:
        if data.id and (existing := self.session.get(StockDocument, data.id)):
            return existing, []  # reenvío desde la carga sin conexión
        self._validate(data)
        self.engine.lock_products(line.product_id for line in data.lines)
        document = self._new_document(data.type, data.id)
        self._set_header(document, data)
        products = self._write(document, self._manual_lines(document, data))
        self._recalculate(products, data.date)
        return document, self.queries.alerts(products)

    def update(self, id_: UUID, data: DocumentIn) -> tuple[StockDocument, list[StockAlertOut]]:
        document = self._editable(id_, manual=True)
        if data.type != document.type:
            raise BusinessRuleError(
                "No se puede cambiar el tipo de un comprobante.", code="TYPE_CHANGE"
            )
        self._validate(data)
        old_date, old_products = document.date, {line.product_id for line in document.lines}
        self.engine.lock_products(old_products | {line.product_id for line in data.lines})
        self._clear(document)
        self._set_header(document, data)
        products = self._write(document, self._manual_lines(document, data)) | old_products
        self._recalculate(products, min(old_date, data.date))
        return document, self.queries.alerts(products)

    def cancel(self, id_: UUID) -> tuple[StockDocument, list[StockAlertOut]]:
        return self._cancel(self._editable(id_, manual=True))

    # --- Comprobantes de sistema (los usan otros módulos) ---

    def save_system(
        self,
        *,
        document_id: UUID | None,
        type_: DocumentType,
        date_: date,
        warehouse_id: UUID,
        source_module: str,
        source_id: UUID,
        lines: list[LineSpec],
        notes: str = "",
    ) -> tuple[StockDocument, list[StockAlertOut]]:
        """Crea o reemplaza el comprobante de stock de un registro de otro módulo."""
        new_products = {spec.product.id for spec in lines}
        old_products: set[UUID] = set()
        old_date = date_
        if document_id is None:
            self.engine.lock_products(new_products)
            document = self._new_document(type_)
        else:
            document = self._editable(document_id, manual=False)
            old_date, old_products = document.date, {line.product_id for line in document.lines}
            self.engine.lock_products(old_products | new_products)
            self._clear(document)
        document.date = date_
        document.warehouse_id = warehouse_id
        document.notes = notes
        document.source_module = source_module
        document.source_id = source_id
        products = self._write(document, lines) | old_products
        self._recalculate(products, min(old_date, date_))
        return document, self.queries.alerts(products)

    def cancel_system(self, document_id: UUID) -> list[StockAlertOut]:
        return self._cancel(self._editable(document_id, manual=False))[1]

    # --- Internos comunes ---

    def _new_document(self, type_: DocumentType, id_: UUID | None = None) -> StockDocument:
        document = StockDocument(
            id=id_ or uuid7(),
            type=type_,
            number=next_number(self.session, DOCUMENT_PREFIXES[type_]),
        )
        self.session.add(document)
        return document

    def _editable(self, id_: UUID, *, manual: bool) -> StockDocument:
        document = self.get(id_)
        if manual and not document.is_manual:
            raise BusinessRuleError(
                "Este comprobante lo generó otro módulo: se modifica desde su origen.",
                code="NOT_MANUAL",
            )
        if document.status == DocumentStatus.CANCELLED:
            raise BusinessRuleError("El comprobante está anulado.", code="CANCELLED")
        return document

    def _clear(self, document: StockDocument) -> None:
        self.session.execute(delete(StockMove).where(StockMove.document_id == document.id))
        document.lines.clear()

    def _cancel(self, document: StockDocument) -> tuple[StockDocument, list[StockAlertOut]]:
        products = {line.product_id for line in document.lines}
        self.engine.lock_products(products)
        document.status = DocumentStatus.CANCELLED
        self.session.execute(
            update(StockMove).where(StockMove.document_id == document.id).values(cancelled=True)
        )
        self._recalculate(products, document.date)
        return document, self.queries.alerts(products)

    def _write(self, document: StockDocument, lines: list[LineSpec]) -> set[UUID]:
        """Guarda líneas y movimientos; devuelve los productos afectados.

        Cabecera y líneas en un solo flush (una entrada en el historial); después los
        movimientos (derivados, sin historial propio).
        """
        moves: list[StockMove] = []
        for line_no, spec in enumerate(lines, start=1):
            document.lines.append(
                StockDocumentLine(
                    line_no=line_no,
                    product=spec.product,
                    product_id=spec.product.id,
                    unit=spec.unit,
                    unit_id=spec.unit.id,
                    quantity=spec.quantity,
                    factor=spec.factor,
                    unit_cost=spec.unit_cost,
                )
            )
            moves += [
                StockMove(
                    document_id=document.id,
                    line_no=line_no,
                    sub_no=sub_no,
                    date=document.date,
                    product_id=spec.product.id,
                    warehouse_id=move.warehouse_id,
                    quantity=move.quantity,
                    cost_mode=move.cost_mode,
                    unit_cost=move.unit_cost,
                    **move.dimensions,
                )
                for sub_no, move in enumerate(spec.moves)
            ]
        self.session.flush()
        self.session.add_all(moves)
        self.session.flush()
        return {spec.product.id for spec in lines}

    def _recalculate(self, product_ids: set[UUID], from_date: date) -> None:
        self.engine.lock_products(product_ids)
        self.engine.recalculate_many(product_ids, from_date)
        self.session.flush()

    # --- Validación y armado de comprobantes manuales ---

    def _validate(self, data: DocumentIn) -> None:
        if data.type not in MANUAL_TYPES:
            raise BusinessRuleError(
                "Este tipo de comprobante lo genera otro módulo.", code="NOT_MANUAL"
            )
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        self.active_warehouse(data.warehouse_id)
        if data.type == DocumentType.TRANSFER:
            if data.target_warehouse_id is None:
                raise BusinessRuleError("Elegí el almacén de destino.", code="TARGET_REQUIRED")
            if data.target_warehouse_id == data.warehouse_id:
                raise BusinessRuleError(
                    "El almacén de destino tiene que ser distinto del de origen.",
                    code="SAME_WAREHOUSE",
                )
            self.active_warehouse(data.target_warehouse_id)
        if data.party_id is not None and self.session.get(Party, data.party_id) is None:
            raise NotFoundError("No se encontró el proveedor/cliente.")
        if data.type == DocumentType.ADJUSTMENT:
            if not data.reason:
                raise BusinessRuleError("Indicá el motivo del ajuste.", code="REASON_REQUIRED")
            products = [line.product_id for line in data.lines]
            if len(products) != len(set(products)):
                raise BusinessRuleError(
                    "Un producto no puede repetirse en el mismo ajuste.", code="DUPLICATE_LINE"
                )
        for line in data.lines:
            if data.type != DocumentType.ADJUSTMENT and line.quantity <= 0:
                raise BusinessRuleError(
                    "Las cantidades tienen que ser mayores a 0.", code="QUANTITY"
                )
            if data.type == DocumentType.MANUAL_IN and line.unit_cost is None:
                raise BusinessRuleError(
                    "Cargá el costo unitario de cada línea (puede ser 0).", code="COST_REQUIRED"
                )

    @staticmethod
    def _set_header(document: StockDocument, data: DocumentIn) -> None:
        document.date = data.date
        document.warehouse_id = data.warehouse_id
        is_transfer = data.type == DocumentType.TRANSFER
        document.target_warehouse_id = data.target_warehouse_id if is_transfer else None
        document.party_id = data.party_id
        document.reference = data.reference
        document.reason = data.reason
        document.notes = data.notes

    def _manual_lines(self, document: StockDocument, data: DocumentIn) -> list[LineSpec]:
        lines = []
        for item in data.lines:
            spec = self.line(item.product_id, item.unit_id, item.quantity)
            base = spec.base_quantity
            match data.type:
                case DocumentType.MANUAL_IN:
                    spec.unit_cost = item.unit_cost
                    cost = ((item.unit_cost or ZERO) / spec.factor).quantize(COST_PRECISION)
                    spec.moves = [MoveSpec(data.warehouse_id, base, CostMode.OWN, cost)]
                case DocumentType.MANUAL_OUT:
                    spec.moves = [MoveSpec(data.warehouse_id, -base, CostMode.AVERAGE)]
                case DocumentType.TRANSFER:
                    target = data.target_warehouse_id or data.warehouse_id  # validado antes
                    spec.moves = [
                        MoveSpec(data.warehouse_id, -base, CostMode.AVERAGE),
                        MoveSpec(target, base, CostMode.AVERAGE),
                    ]
                case DocumentType.ADJUSTMENT:
                    current = self.queries.quantity(
                        spec.product.id,
                        data.warehouse_id,
                        at=data.date,
                        exclude_document_id=document.id,
                    )
                    difference = base - current
                    if difference != 0:
                        spec.moves = [MoveSpec(data.warehouse_id, difference, CostMode.AVERAGE)]
            lines.append(spec)
        return lines


# --- Presentación y listado ---


def to_summary(document: StockDocument) -> DocumentSummaryOut:
    return DocumentSummaryOut(
        id=document.id,
        type=document.type,
        number=document.number,
        date=document.date,
        status=document.status,
        warehouse=Ref(id=document.warehouse.id, name=document.warehouse.name),
        target_warehouse=(
            Ref(id=document.target_warehouse.id, name=document.target_warehouse.name)
            if document.target_warehouse
            else None
        ),
        party=Ref(id=document.party.id, name=document.party.name) if document.party else None,
        reference=document.reference,
        is_manual=document.is_manual,
        line_count=len(document.lines),
    )


def to_out(document: StockDocument, moves: list[StockMove]) -> DocumentOut:
    """Comprobante completo; por línea: lo cargado, lo que movió el stock y su costo."""
    by_line: dict[int, list[StockMove]] = {}
    for move in moves:
        by_line.setdefault(move.line_no, []).append(move)
    lines = []
    for line in document.lines:
        line_moves = by_line.get(line.line_no, [])
        # En transferencias la línea tiene salida y entrada: se informa la entrada
        effective = [m for m in line_moves if m.quantity > 0] or line_moves
        lines.append(
            LineOut(
                line_no=line.line_no,
                product=ProductRef(
                    id=line.product.id, code=line.product.code, name=line.product.name
                ),
                unit=UnitCode(id=line.unit.id, code=line.unit.code),
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                base_unit=line.product.unit.code,
                base_quantity=line.quantity * line.factor,
                moved_quantity=sum((m.quantity for m in effective), Decimal(0)),
                total_cost=abs(sum((m.total_cost for m in effective), Decimal(0))),
            )
        )
    return DocumentOut(
        **to_summary(document).model_dump(),
        reason=document.reason,
        notes=document.notes,
        lines=lines,
    )


@dataclass(frozen=True)
class DocumentFilters:
    type: DocumentType | None = None
    status: DocumentStatus | None = None
    warehouse_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None


def search_documents(
    session: Session, f: DocumentFilters, page: PageParams
) -> tuple[list[StockDocument], int]:
    query = select(StockDocument).order_by(StockDocument.date.desc(), StockDocument.id.desc())
    if f.type:
        query = query.where(StockDocument.type == f.type)
    if f.status:
        query = query.where(StockDocument.status == f.status)
    if f.warehouse_id:
        query = query.where(
            or_(
                StockDocument.warehouse_id == f.warehouse_id,
                StockDocument.target_warehouse_id == f.warehouse_id,
            )
        )
    if f.date_from:
        query = query.where(StockDocument.date >= f.date_from)
    if f.date_to:
        query = query.where(StockDocument.date <= f.date_to)
    if f.q:
        pattern = f"%{f.q.strip()}%"
        query = query.where(
            or_(StockDocument.number.ilike(pattern), StockDocument.reference.ilike(pattern))
        )
    return paginate(session, query, page)
