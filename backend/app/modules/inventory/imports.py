"""Importación del stock inicial: un ingreso por almacén y fecha (ver app/imports.py)."""

from collections import defaultdict
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.imports import (
    ImportColumn,
    ImportDef,
    RowError,
    cell_date,
    cell_decimal,
    cell_text,
    define_import,
    normalize,
    required,
)
from app.modules.inventory.models import DocumentType
from app.modules.inventory.permissions import INVENTORY_WRITE
from app.modules.inventory.schemas import DocumentIn, LineIn
from app.modules.inventory.service import StockDocumentService
from app.modules.masterdata.models import Product, Unit, Warehouse

REFERENCE = "Stock inicial"


def _index(
    session: Session,
    context: dict[str, Any],
    model: type[Product] | type[Unit] | type[Warehouse],
    *fields: str,
) -> dict[str, Any]:
    """Índice por texto normalizado de los campos dados (se arma una vez por importación)."""
    key = f"index_{model.__tablename__}"
    if key not in context:
        index: dict[str, Any] = {}
        for obj in session.scalars(select(model)):
            for f in fields:
                index.setdefault(normalize(str(getattr(obj, f))), obj)
        context[key] = index
    return context[key]  # type: ignore[no-any-return]


def _row(session: Session, row: dict[str, Any], context: dict[str, Any]) -> None:
    warehouse_name = required(cell_text(row.get("warehouse")), "Almacén")
    warehouse = _index(session, context, Warehouse, "name").get(normalize(warehouse_name))
    if warehouse is None or not warehouse.is_active:
        raise RowError(f"Almacén: no existe '{warehouse_name}'.")
    product_key = required(cell_text(row.get("product")), "Producto")
    product = _index(session, context, Product, "code", "name").get(normalize(product_key))
    if product is None:
        raise RowError(f"Producto: no existe '{product_key}' (código o nombre).")
    unit_code = cell_text(row.get("unit"))
    unit = (
        _index(session, context, Unit, "code").get(normalize(unit_code))
        if unit_code
        else product.unit
    )
    if unit is None:
        raise RowError(f"Unidad: no existe '{unit_code}'.")
    quantity = required(cell_decimal(row.get("quantity"), "Cantidad"), "Cantidad")
    cost = required(cell_decimal(row.get("unit_cost"), "Costo unitario"), "Costo unitario")
    day = cell_date(row.get("date"), "Fecha") or date.today()
    StockDocumentService(session).line(product.id, unit.id, quantity)  # valida producto y unidad
    line = LineIn(product_id=product.id, unit_id=unit.id, quantity=quantity, unit_cost=cost)
    groups: dict[tuple[UUID, date], list[tuple[int, LineIn]]] = context.setdefault(
        "groups", defaultdict(list)
    )
    groups[(warehouse.id, day)].append((row["_row"], line))


def _finish(session: Session, context: dict[str, Any]) -> None:
    service = StockDocumentService(session)
    for (warehouse_id, day), lines in context.get("groups", {}).items():
        context["_failed_row"] = lines[0][0]
        service.create(
            DocumentIn(
                type=DocumentType.MANUAL_IN,
                date=day,
                warehouse_id=warehouse_id,
                reference=REFERENCE,
                lines=[line for _, line in lines],
            )
        )


define_import(
    ImportDef(
        key="opening_stock",
        title="Stock inicial",
        description="Existencias al arrancar, con su costo: un ingreso por almacén y fecha.",
        permission=INVENTORY_WRITE,
        columns=[
            ImportColumn(
                "warehouse",
                "Almacén",
                required=True,
                help="Nombre (debe existir).",
                example="Galpón",
            ),
            ImportColumn(
                "product", "Producto", required=True, help="Código o nombre.", example="INS-0001"
            ),
            ImportColumn("quantity", "Cantidad", required=True, example="120"),
            ImportColumn("unit", "Unidad", help="Vacío = unidad base del producto.", example="L"),
            ImportColumn(
                "unit_cost",
                "Costo unitario",
                required=True,
                help="Por la unidad indicada, sin IVA.",
                example="3500",
            ),
            ImportColumn("date", "Fecha", help="dd/mm/aaaa; vacío = hoy.", example="01/10/2026"),
        ],
        handle_row=_row,
        finish=_finish,
        notes=["La producción propia puede ir con costo 0 (su costo está en los ciclos)."],
    )
)
