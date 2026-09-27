"""Importación de productos y clientes/proveedores (registro: app/imports.py)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.imports import (
    ImportColumn,
    ImportDef,
    RowError,
    cell_bool,
    cell_decimal,
    cell_text,
    choice,
    define_import,
    normalize,
    required,
)
from app.modules.masterdata.models import (
    PRODUCT_TYPE_LABELS,
    VAT_CONDITION_LABELS,
    ProductCategory,
    Unit,
)
from app.modules.masterdata.permissions import MASTERDATA_WRITE
from app.modules.masterdata.schemas import ConversionIn, PartyCreate, ProductCreate
from app.modules.masterdata.service import PartyService, ProductService

# --- Productos ---


def _units(session: Session, context: dict[str, Any]) -> dict[str, Unit]:
    if "units" not in context:
        context["units"] = {normalize(u.code): u for u in session.scalars(select(Unit))}
    return context["units"]  # type: ignore[no-any-return]


def _unit(session: Session, context: dict[str, Any], code: str, label: str) -> Unit:
    unit = _units(session, context).get(normalize(code))
    if unit is None:
        raise RowError(f"{label}: no existe la unidad '{code}'.")
    return unit


def _category(session: Session, context: dict[str, Any], text: str) -> ProductCategory:
    if "categories" not in context:
        categories = list(
            session.scalars(select(ProductCategory).where(ProductCategory.is_active.is_(True)))
        )
        by_path = {normalize(c.path): c for c in categories}
        names: dict[str, list[ProductCategory]] = {}
        for c in categories:
            names.setdefault(normalize(c.name), []).append(c)
        context["categories"] = (by_path, names)
    by_path, names = context["categories"]
    key = normalize(text)
    if key in by_path:
        return by_path[key]  # type: ignore[no-any-return]
    matches = names.get(key, [])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RowError(
            f"Categoría: '{text}' está repetida; usá la ruta (ej. 'Insumos > Agroquímicos')."
        )
    raise RowError(f"Categoría: no existe '{text}'.")


def _conversions(session: Session, context: dict[str, Any], text: str) -> list[ConversionIn]:
    """ "18 kg; 0,5 bin" → 1 unidad del producto = 18 kg, = 0,5 bin."""
    result = []
    for part in filter(None, (p.strip() for p in text.split(";"))):
        quantity, _, code = part.partition(" ")
        amount = cell_decimal(quantity, "Equivalencias")
        if amount is None or not code.strip():
            raise RowError(f"Equivalencias: '{part}' tiene que ser 'cantidad unidad' (ej. 18 kg).")
        unit = _unit(session, context, code.strip(), "Equivalencias")
        result.append(ConversionIn(unit_id=unit.id, quantity=amount))
    return result


def _product_row(session: Session, row: dict[str, Any], context: dict[str, Any]) -> None:
    unit = _unit(session, context, required(cell_text(row.get("unit")), "Unidad"), "Unidad")
    category = cell_text(row.get("category"))
    data = ProductCreate(
        code=cell_text(row.get("code")) or None,
        name=required(cell_text(row.get("name")), "Nombre"),
        type=choice(required(row.get("type"), "Tipo"), "Tipo", PRODUCT_TYPE_LABELS),
        unit_id=unit.id,
        category_id=_category(session, context, category).id if category else None,
        vat_rate=cell_decimal(row.get("vat_rate"), "IVA %") or 21,
        min_stock=cell_decimal(row.get("min_stock"), "Stock mínimo"),
        notes=cell_text(row.get("notes")),
        conversions=_conversions(session, context, cell_text(row.get("conversions"))),
    )
    ProductService(session).create(data)


define_import(
    ImportDef(
        key="products",
        title="Productos",
        description="Insumos, semielaborados, terminados, producción propia, reventa y servicios.",
        permission=MASTERDATA_WRITE,
        columns=[
            ImportColumn(
                "code", "Código", help="Vacío = se genera solo (INS-0001…).", example="INS-0001"
            ),
            ImportColumn("name", "Nombre", required=True, example="Glifosato 48 %"),
            ImportColumn(
                "type",
                "Tipo",
                required=True,
                help=", ".join(PRODUCT_TYPE_LABELS.values()) + ".",
                example="Insumo",
            ),
            ImportColumn(
                "unit",
                "Unidad",
                required=True,
                help="Código de la unidad base (kg, L, un, cajón…).",
                example="L",
            ),
            ImportColumn(
                "category",
                "Categoría",
                help="Nombre o ruta de la categoría (debe existir).",
                example="Insumos > Agroquímicos",
            ),
            ImportColumn("vat_rate", "IVA %", help="Vacío = 21.", example="21"),
            ImportColumn(
                "min_stock",
                "Stock mínimo",
                help="En la unidad base; vacío = sin aviso.",
                example="20",
            ),
            ImportColumn(
                "conversions",
                "Equivalencias",
                help="1 unidad del producto = cantidad otra unidad; varias separadas por ';'.",
                example="20 kg; 0,02 tn",
            ),
            ImportColumn("notes", "Observaciones"),
        ],
        handle_row=_product_row,
    )
)


# --- Clientes y proveedores ---


def _party_row(session: Session, row: dict[str, Any], context: dict[str, Any]) -> None:
    payment_days = cell_decimal(row.get("payment_days"), "Días de pago")
    data = PartyCreate(
        name=required(cell_text(row.get("name")), "Razón social"),
        trade_name=cell_text(row.get("trade_name")),
        cuit=cell_text(row.get("cuit")) or None,
        vat_condition=choice(
            required(row.get("vat_condition"), "Condición IVA"),
            "Condición IVA",
            VAT_CONDITION_LABELS,
        ),
        is_customer=cell_bool(row.get("is_customer")),
        is_supplier=cell_bool(row.get("is_supplier")),
        address=cell_text(row.get("address")),
        city=cell_text(row.get("city")),
        province=cell_text(row.get("province")),
        phone=cell_text(row.get("phone")),
        email=cell_text(row.get("email")),
        payment_days=int(payment_days or 0),
        notes=cell_text(row.get("notes")),
    )
    PartyService(session).create(data)


define_import(
    ImportDef(
        key="parties",
        title="Clientes y proveedores",
        description="Terceros con su CUIT, condición de IVA y días de pago.",
        permission=MASTERDATA_WRITE,
        columns=[
            ImportColumn("name", "Razón social", required=True, example="Agroinsumos del Valle SA"),
            ImportColumn("trade_name", "Nombre de fantasía"),
            ImportColumn(
                "cuit", "CUIT", help="Con o sin guiones; se valida.", example="30-71234567-8"
            ),
            ImportColumn(
                "vat_condition",
                "Condición IVA",
                required=True,
                help=", ".join(VAT_CONDITION_LABELS.values()) + ".",
                example="Responsable Inscripto",
            ),
            ImportColumn("is_customer", "Es cliente", help="Sí / No.", example="No"),
            ImportColumn(
                "is_supplier",
                "Es proveedor",
                help="Sí / No (al menos uno de los dos).",
                example="Sí",
            ),
            ImportColumn("address", "Dirección"),
            ImportColumn("city", "Localidad"),
            ImportColumn("province", "Provincia"),
            ImportColumn("phone", "Teléfono"),
            ImportColumn("email", "Email"),
            ImportColumn(
                "payment_days",
                "Días de pago",
                help="Para el vencimiento por defecto.",
                example="30",
            ),
            ImportColumn("notes", "Observaciones"),
        ],
        handle_row=_party_row,
    )
)
