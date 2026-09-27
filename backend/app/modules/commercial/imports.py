"""Importación de saldos iniciales de cuentas corrientes (ver app/imports.py)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.imports import (
    ImportColumn,
    ImportDef,
    RowError,
    cell_date,
    cell_decimal,
    cell_text,
    choice,
    define_import,
    normalize,
    required,
)
from app.modules.commercial.document_service import CommercialDocumentService
from app.modules.commercial.models import Direction
from app.modules.commercial.permissions import COMMERCIAL_WRITE
from app.modules.masterdata.cuit import normalize_cuit
from app.modules.masterdata.models import Party

KINDS = {Direction.SALE: "Cliente", Direction.PURCHASE: "Proveedor"}


def _party(session: Session, context: dict[str, Any], text: str) -> Party:
    if "parties" not in context:
        index: dict[str, Party] = {}
        for p in session.scalars(select(Party).where(Party.is_active.is_(True))):
            index[normalize(p.name)] = p
            if p.cuit:
                index[p.cuit] = p
        context["parties"] = index
    digits = normalize_cuit(text)
    party = context["parties"].get(digits if len(digits) == 11 else normalize(text))
    if party is None:
        raise RowError(f"Cliente/proveedor: no existe '{text}' (CUIT o razón social).")
    return party  # type: ignore[no-any-return]


def _row(session: Session, row: dict[str, Any], context: dict[str, Any]) -> None:
    direction = choice(required(row.get("kind"), "Tipo"), "Tipo", KINDS)
    party = _party(session, context, required(cell_text(row.get("party")), "Cliente/proveedor"))
    if direction == Direction.SALE and not party.is_customer:
        raise RowError(f"'{party.name}' no está marcado como cliente.")
    if direction == Direction.PURCHASE and not party.is_supplier:
        raise RowError(f"'{party.name}' no está marcado como proveedor.")
    amount = required(cell_decimal(row.get("amount"), "Importe"), "Importe")
    if amount == 0:
        raise RowError("Importe: no puede ser 0.")
    CommercialDocumentService(session).create_opening(
        direction=direction,
        party=party,
        day=required(cell_date(row.get("date"), "Fecha"), "Fecha"),
        due_date=cell_date(row.get("due_date"), "Vencimiento"),
        reference=cell_text(row.get("reference")),
        amount=amount,
    )


define_import(
    ImportDef(
        key="opening_balances",
        title="Saldos iniciales de cuentas corrientes",
        description=(
            "Lo que cada cliente debe y lo que se le debe a cada proveedor al arrancar, "
            "comprobante por comprobante. No cuentan como ventas ni gastos."
        ),
        permission=COMMERCIAL_WRITE,
        columns=[
            ImportColumn(
                "kind", "Tipo", required=True, help="Cliente o Proveedor.", example="Cliente"
            ),
            ImportColumn(
                "party",
                "Cliente/proveedor",
                required=True,
                help="CUIT o razón social (debe existir).",
                example="20-12345678-6",
            ),
            ImportColumn(
                "date",
                "Fecha",
                required=True,
                help="Del comprobante, dd/mm/aaaa.",
                example="15/08/2026",
            ),
            ImportColumn(
                "due_date",
                "Vencimiento",
                help="Vacío = fecha + días de pago.",
                example="15/09/2026",
            ),
            ImportColumn(
                "reference", "Comprobante", help="Para identificarlo.", example="FC A 0001-00001234"
            ),
            ImportColumn(
                "amount",
                "Importe",
                required=True,
                help="Saldo pendiente con IVA. Negativo = saldo a favor del tercero.",
                example="150000",
            ),
        ],
        handle_row=_row,
    )
)
