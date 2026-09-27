"""Reportes comerciales y de caja (se registran al importar el módulo — ver app/reports.py)."""

from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.formatting import format_quantity
from app.core.reports import (
    ReportColumn,
    ReportFilter,
    ReportLink,
    ReportParams,
    ReportRow,
    TableReport,
    choice,
    define_report,
    percent,
    period_text,
    require_value,
    sum_rows,
)
from app.modules.commercial.cash_service import CashQueries
from app.modules.commercial.ledger import LedgerQueries
from app.modules.commercial.models import (
    DOCUMENT_KIND_LABELS,
    CommercialDocument,
    CommercialLine,
    Direction,
    DocumentKind,
    LineKind,
    Status,
)
from app.modules.commercial.permissions import CASH_READ, COMMERCIAL_READ
from app.modules.commercial.sales import sale_facts
from app.modules.masterdata.cuit import format_cuit
from app.modules.masterdata.models import VAT_CONDITION_LABELS
from app.modules.production.catalog import report_period

GROUP = "Comercial y caja"
ZERO = Decimal(0)
PERIOD = ReportFilter(kind="period", label="Período")
DIRECTIONS = {"sale": "Ventas", "purchase": "Compras"}


def _col(key: str, label: str, kind: str = "money") -> ReportColumn:
    return ReportColumn(key=key, label=label, kind=kind)


def _documents(
    db: Session, direction: Direction, p: ReportParams
) -> tuple[str, list[CommercialDocument]]:
    date_from, date_to = report_period(db, p.date_from, p.date_to, p.season_id)
    query = (
        select(CommercialDocument)
        .where(
            CommercialDocument.direction == direction,
            CommercialDocument.status == Status.ACTIVE,
            CommercialDocument.is_opening_balance.is_(False),
        )
        .order_by(CommercialDocument.date, CommercialDocument.internal_number)
    )
    if date_from:
        query = query.where(CommercialDocument.date >= date_from)
    if date_to:
        query = query.where(CommercialDocument.date <= date_to)
    if p.party_id:
        query = query.where(CommercialDocument.party_id == p.party_id)
    if p.product_id:
        query = query.where(
            CommercialDocument.id.in_(
                select(CommercialLine.document_id).where(CommercialLine.product_id == p.product_id)
            )
        )
    return period_text(date_from, date_to), list(db.scalars(query))


def _sign(doc: CommercialDocument) -> int:
    return -1 if doc.kind == DocumentKind.CREDIT_NOTE else 1


def _document_rows(
    documents: list[CommercialDocument],
) -> tuple[list[ReportColumn], list[ReportRow]]:
    rows = [
        ReportRow(
            cells={
                "date": d.date,
                "label": d.invoice_label
                if d.has_invoice
                else f"{DOCUMENT_KIND_LABELS[d.kind]} {d.internal_number}",
                "party": d.party.name,
                "net": d.net_total * _sign(d),
                "vat": d.vat_total * _sign(d),
                "other": d.other_taxes * _sign(d),
                "total": d.total * _sign(d),
            },
            link=ReportLink(kind="commercial_document", id=d.id),
        )
        for d in documents
    ]
    columns = [
        _col("date", "Fecha", "date"),
        _col("label", "Comprobante", "text"),
        _col("party", "Tercero", "text"),
        _col("net", "Neto"),
        _col("vat", "IVA"),
        _col("other", "Otros impuestos"),
        _col("total", "Total"),
    ]
    return columns, rows


def _grouped(
    items: dict[str, Decimal], label: str, total_label: str = "Neto", *, by_month: bool = False
) -> tuple[list[ReportColumn], list[ReportRow]]:
    total = sum(items.values(), ZERO)
    order = (
        sorted(items.items(), key=lambda i: i[0][3:] + i[0][:2])
        if by_month
        else sorted(items.items(), key=lambda i: -i[1])
    )
    rows = [
        ReportRow(cells={"name": name, "amount": amount, "pct": percent(amount, total)})
        for name, amount in order
    ]
    return [
        _col("name", label, "text"),
        _col("amount", total_label),
        _col("pct", "% del total", "percent"),
    ], rows


# --- Ventas ---

SALE_GROUPS = {"document": "Comprobante", "party": "Cliente", "product": "Producto", "month": "Mes"}


@define_report(
    key="sales",
    title="Ventas",
    group=GROUP,
    description="Ventas por comprobante, cliente, producto o mes.",
    permission=COMMERCIAL_READ,
    filters=[
        PERIOD,
        choice("group_by", "Ver por", SALE_GROUPS, "document"),
        ReportFilter(kind="party", label="Cliente"),
        ReportFilter(kind="product", label="Producto"),
    ],
)
def sales(db: Session, p: ReportParams) -> TableReport:
    group_by = p.group_by if p.group_by in SALE_GROUPS else "document"
    subtitle, documents = _documents(db, Direction.SALE, p)
    if group_by == "document":
        columns, rows = _document_rows(documents)
        keys = ["net", "vat", "other", "total"]
    elif group_by == "product":
        ids = {d.id for d in documents}
        facts = [
            f
            for f in sale_facts(db, *report_period(db, p.date_from, p.date_to, p.season_id))
            if f.document_id in ids
        ]
        if p.product_id:
            facts = [f for f in facts if f.product and f.product.id == p.product_id]
        grouped: dict[str, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        units: dict[str, str] = {}
        for f in facts:
            name = f.product.name if f.product else f"Concepto: {f.description}"
            units[name] = f.product.unit.code if f.product else ""
            grouped[name][0] += f.quantity
            grouped[name][1] += f.revenue
        rows = [
            ReportRow(
                cells={
                    "name": name,
                    "quantity": f"{format_quantity(q)} {units[name]}".strip()
                    if units[name]
                    else "",
                    "amount": r.quantize(Decimal("0.01")),
                }
            )
            for name, (q, r) in sorted(grouped.items(), key=lambda i: -i[1][1])
        ]
        columns = [
            _col("name", "Producto", "text"),
            _col("quantity", "Cantidad", "text"),
            _col("amount", "Neto"),
        ]
        keys = ["amount"]
    else:
        key: Callable[[CommercialDocument], str] = (
            (lambda d: d.party.name)
            if group_by == "party"
            else (lambda d: d.date.strftime("%m/%Y"))
        )
        totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for d in documents:
            totals[key(d)] += d.net_total * _sign(d)
        columns, rows = _grouped(totals, SALE_GROUPS[group_by], by_month=group_by == "month")
        keys = ["amount"]
    return TableReport(
        key="sales",
        title=f"Ventas por {SALE_GROUPS[group_by].lower()}",
        subtitle=subtitle,
        columns=columns,
        rows=rows,
        totals=sum_rows(rows, keys),
        notes=["Las notas de crédito restan."],
    )


# --- Compras y gastos ---

PURCHASE_GROUPS = {
    "document": "Comprobante",
    "party": "Proveedor",
    "category": "Categoría",
    "month": "Mes",
}


@define_report(
    key="purchases",
    title="Compras y gastos",
    group=GROUP,
    description="Compras por comprobante, proveedor, categoría o mes.",
    permission=COMMERCIAL_READ,
    filters=[
        PERIOD,
        choice("group_by", "Ver por", PURCHASE_GROUPS, "document"),
        ReportFilter(kind="party", label="Proveedor"),
    ],
)
def purchases(db: Session, p: ReportParams) -> TableReport:
    group_by = p.group_by if p.group_by in PURCHASE_GROUPS else "document"
    subtitle, documents = _documents(db, Direction.PURCHASE, p)
    keys = ["amount"]
    if group_by == "document":
        columns, rows = _document_rows(documents)
        keys = ["net", "vat", "other", "total"]
    else:
        totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for d in documents:
            if group_by == "category":
                for line in d.lines:
                    name = (
                        "Mercadería e insumos (stock)"
                        if line.kind == LineKind.PRODUCT
                        else (
                            line.expense_category.name if line.expense_category else "Sin categoría"
                        )
                    )
                    totals[name] += line.net_amount * _sign(d)
            else:
                name = d.party.name if group_by == "party" else d.date.strftime("%m/%Y")
                totals[name] += d.net_total * _sign(d)
        columns, rows = _grouped(totals, PURCHASE_GROUPS[group_by], by_month=group_by == "month")
    return TableReport(
        key="purchases",
        title=f"Compras y gastos por {PURCHASE_GROUPS[group_by].lower()}",
        subtitle=subtitle,
        columns=columns,
        rows=rows,
        totals=sum_rows(rows, keys),
        notes=[
            "Las notas de crédito restan. Los gastos pagados por caja están en el reporte Gastos."
        ],
    )


# --- Para el contador ---

RATES = (Decimal(21), Decimal("10.5"), Decimal(27))


@define_report(
    key="accountant",
    title="Libro de compras / ventas (contador)",
    group=GROUP,
    description="Comprobantes con neto e IVA por alícuota, CUIT y condición de IVA.",
    permission=COMMERCIAL_READ,
    filters=[
        PERIOD,
        choice("direction", "Libro", DIRECTIONS, "sale"),
        choice("scope", "Comprobantes", {"invoice": "Solo con factura", "all": "Todos"}, "invoice"),
    ],
)
def accountant(db: Session, p: ReportParams) -> TableReport:
    direction = Direction.PURCHASE if p.direction == "purchase" else Direction.SALE
    subtitle, documents = _documents(db, direction, p)
    if p.scope != "all":
        documents = [d for d in documents if d.has_invoice]
    rows = []
    for d in documents:
        sign = _sign(d)
        cells: dict[str, object] = {
            "date": d.date,
            "kind": DOCUMENT_KIND_LABELS[d.kind],
            "number": f"{d.letter} {d.pos_number}-{d.number}"
            if d.has_invoice
            else d.internal_number,
            "party": d.party.name,
            "cuit": format_cuit(d.party.cuit) if d.party.cuit else "",
            "vat_condition": VAT_CONDITION_LABELS[d.party.vat_condition],
            "other": d.other_taxes * sign,
            "total": d.total * sign,
        }
        amounts: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for line in d.lines:
            rate = line.vat_rate.normalize()
            if rate in RATES:
                amounts[f"net_{rate}"] += line.net_amount * sign
                amounts[f"vat_{rate}"] += line.vat_amount * sign
            else:
                amounts["exempt"] += line.net_amount * sign
        cells.update(amounts)
        rows.append(ReportRow(cells=cells, link=ReportLink(kind="commercial_document", id=d.id)))
    money_keys = (
        [f"net_{r}" for r in RATES] + ["exempt"] + [f"vat_{r}" for r in RATES] + ["other", "total"]
    )
    labels = {
        "net_21": "Neto 21 %",
        "net_10.5": "Neto 10,5 %",
        "net_27": "Neto 27 %",
        "exempt": "No gravado / exento",
        "vat_21": "IVA 21 %",
        "vat_10.5": "IVA 10,5 %",
        "vat_27": "IVA 27 %",
        "other": "Percepciones y otros",
        "total": "Total",
    }
    return TableReport(
        key="accountant",
        title=f"Libro de {DIRECTIONS[direction.value].lower()}",
        subtitle=subtitle,
        columns=[
            _col("date", "Fecha", "date"),
            _col("kind", "Tipo", "text"),
            _col("number", "Número", "text"),
            _col("party", "Razón social", "text"),
            _col("cuit", "CUIT", "text"),
            _col("vat_condition", "Condición IVA", "text"),
            *(_col(k, labels[k]) for k in money_keys),
        ],
        rows=rows,
        totals=sum_rows(rows, money_keys),
        notes=["Las notas de crédito figuran en negativo."],
    )


# --- Saldos ---


@define_report(
    key="balances",
    title="Saldos de cuentas corrientes",
    group=GROUP,
    description="Lo que deben los clientes o se les debe a los proveedores, con antigüedad.",
    permission=COMMERCIAL_READ,
    filters=[
        choice("direction", "Cuentas", {"sale": "Clientes", "purchase": "Proveedores"}, "sale")
    ],
)
def balances(db: Session, p: ReportParams) -> TableReport:
    direction = Direction.PURCHASE if p.direction == "purchase" else Direction.SALE
    columns = [
        _col("party", "Proveedor" if direction == Direction.PURCHASE else "Cliente", "text"),
        _col("balance", "Le debemos" if direction == Direction.PURCHASE else "Nos debe"),
        _col("overdue", "Vencido"),
        _col("days_0_30", "1-30 días"),
        _col("days_31_60", "31-60 días"),
        _col("days_61_90", "61-90 días"),
        _col("days_over_90", "+90 días"),
        _col("advances", "Anticipos y NC sin aplicar"),
    ]
    rows = [
        ReportRow(
            cells={"party": b.party.name, **b.model_dump(include={c.key for c in columns[1:]})}
        )
        for b in LedgerQueries(db).balances(direction)
    ]
    return TableReport(
        key="balances",
        title=f"Saldos de {'proveedores' if direction == Direction.PURCHASE else 'clientes'}",
        subtitle="Al día de hoy",
        columns=columns,
        rows=rows,
        totals=sum_rows(rows, [c.key for c in columns[1:]]),
    )


# --- Caja ---


@define_report(
    key="cash_statement",
    title="Movimientos de una caja o banco",
    group=GROUP,
    description="Entradas, salidas y saldo de una cuenta en un período.",
    permission=CASH_READ,
    filters=[ReportFilter(kind="cash_account", label="Cuenta", required=True), PERIOD],
)
def cash_statement(db: Session, p: ReportParams) -> TableReport:
    account_id = require_value(p.cash_account_id, "Elegí la caja o el banco.")
    date_from, date_to = report_period(db, p.date_from, p.date_to, p.season_id)
    statement = CashQueries(db).statement(account_id, date_from, date_to)
    rows = [
        ReportRow(
            cells={
                "date": r.date,
                "label": r.label,
                "income": r.amount if r.amount > 0 else None,
                "outcome": -r.amount if r.amount < 0 else None,
                "balance": r.balance,
            },
            link=ReportLink(kind="payment" if r.source == "payment" else "cash_movement", id=r.id),
        )
        for r in statement.rows
    ]
    opening = ReportRow(
        cells={"label": "Saldo anterior", "balance": statement.opening_balance}, style="subtotal"
    )
    return TableReport(
        key="cash_statement",
        title=f"Movimientos · {statement.account.name}",
        subtitle=period_text(date_from, date_to),
        columns=[
            _col("date", "Fecha", "date"),
            _col("label", "Detalle", "text"),
            _col("income", "Entra"),
            _col("outcome", "Sale"),
            _col("balance", "Saldo"),
        ],
        rows=[opening, *rows],
        totals={
            "income": sum_rows(rows, ["income"])["income"],
            "outcome": sum_rows(rows, ["outcome"])["outcome"],
            "balance": statement.closing_balance,
        },
    )
