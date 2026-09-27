"""Reportes de costos y rentabilidad (se registran al importar el módulo — ver app/reports.py)."""

from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

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
    sum_rows,
)
from app.modules.assets.models import Asset
from app.modules.commercial.sales import sale_facts
from app.modules.costs.facts import (
    ExpenseFact,
    ExpenseScope,
    Scope,
    expense_facts,
    input_facts,
    machinery_facts,
)
from app.modules.costs.permissions import COSTS_READ
from app.modules.costs.service import CostQueries, CycleProfit
from app.modules.masterdata.models import PRODUCT_TYPE_LABELS, ProductType
from app.modules.production.catalog import report_period
from app.modules.production.models import CropCycle, CycleStatus, Farm, Plot, Season

GROUP = "Costos y rentabilidad"
ZERO = Decimal(0)
MONEY = Decimal("0.01")
PERIOD = ReportFilter(kind="period", label="Período")


def _col(key: str, label: str, kind: str = "money") -> ReportColumn:
    return ReportColumn(key=key, label=label, kind=kind)


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY)


def _period(db: Session, p: ReportParams) -> tuple[str, Scope]:
    date_from, date_to = report_period(db, p.date_from, p.date_to, p.season_id)
    return period_text(date_from, date_to), Scope(date_from=date_from, date_to=date_to)


# --- Rentabilidad ---

PROFIT_GROUPS = {
    "cycle": "Ciclo",
    "crop_season": "Cultivo y temporada",
    "crop": "Cultivo",
    "season": "Temporada",
    "plot": "Lote",
    "farm": "Establecimiento",
}
GROUP_KEY: dict[str, Callable[[CycleProfit], tuple[str, str]]] = {
    "cycle": lambda p: (str(p.cycle.id), p.cycle.name),
    "crop_season": lambda p: (
        f"{p.cycle.crop_id}{p.cycle.season_id}",
        f"{p.cycle.crop.name} · {p.cycle.season.name}",
    ),
    "crop": lambda p: (str(p.cycle.crop_id), p.cycle.crop.name),
    "season": lambda p: (str(p.cycle.season_id), p.cycle.season.name),
    "plot": lambda p: (str(p.cycle.plot_id), f"{p.cycle.plot.farm.name} · {p.cycle.plot.name}"),
    "farm": lambda p: (str(p.cycle.plot.farm_id), p.cycle.plot.farm.name),
}


@define_report(
    key="profitability",
    title="Rentabilidad",
    group=GROUP,
    description="Costos, ingresos y margen por ciclo, cultivo, temporada, lote o establecimiento.",
    permission=COSTS_READ,
    filters=[
        choice("group_by", "Ver por", PROFIT_GROUPS, "cycle"),
        ReportFilter(kind="season", label="Temporada"),
        ReportFilter(kind="crop", label="Cultivo"),
        ReportFilter(kind="farm", label="Establecimiento"),
        ReportFilter(kind="plot", label="Lote"),
        choice(
            "scope",
            "Ciclos",
            {"all": "Todos", "active": "En curso", "finished": "Finalizados"},
            "all",
        ),
    ],
)
def profitability(db: Session, p: ReportParams) -> TableReport:
    group_by = p.group_by if p.group_by in GROUP_KEY else "cycle"
    query = select(CropCycle).join(Plot).order_by(CropCycle.start_date)
    if p.season_id:
        query = query.where(CropCycle.season_id == p.season_id)
    if p.crop_id:
        query = query.where(CropCycle.crop_id == p.crop_id)
    if p.plot_id:
        query = query.where(CropCycle.plot_id == p.plot_id)
    if p.farm_id:
        query = query.where(Plot.farm_id == p.farm_id)
    if p.scope in ("active", "finished"):
        query = query.where(CropCycle.status == CycleStatus(p.scope))
    profits = CostQueries(db).profitability(list(db.scalars(query)))

    same_unit = group_by in ("cycle", "crop", "crop_season")
    groups: dict[str, list[CycleProfit]] = defaultdict(list)
    labels: dict[str, str] = {}
    for profit in profits:
        key, label = GROUP_KEY[group_by](profit)
        groups[key].append(profit)
        labels[key] = label

    rows = []
    for key, items in groups.items():
        area = sum((i.cycle.area_ha for i in items), ZERO)
        s = [i.summary for i in items]
        total = sum((x.total_cost for x in s), ZERO)
        revenue = sum((i.revenue for i in items), ZERO)
        harvested = sum((x.harvested_quantity for x in s), ZERO)
        margin = revenue - total
        cells: dict[str, object] = {
            "name": labels[key],
            "area": area,
            "inputs": sum((x.input_cost for x in s), ZERO),
            "machinery": sum((x.machinery_cost for x in s), ZERO),
            "expenses": sum((x.expense_cost for x in s), ZERO),
            "total": total,
            "revenue": revenue,
            "margin": margin,
            "margin_ha": _money(margin / area) if area else None,
            "margin_pct": percent(margin, revenue),
        }
        if same_unit:
            cells["harvested"] = f"{format_quantity(harvested)} {s[0].harvest_unit}"
            cells["cost_unit"] = _money(total / harvested) if harvested else None
        link = ReportLink(kind="cycle", id=items[0].cycle.id) if group_by == "cycle" else None
        rows.append(ReportRow(cells=cells, link=link))

    columns = [
        _col("name", PROFIT_GROUPS[group_by], "text"),
        _col("area", "Ha", "quantity"),
        _col("inputs", "Insumos"),
        _col("machinery", "Maquinaria"),
        _col("expenses", "Servicios y gastos"),
        _col("total", "Costo total"),
    ]
    if same_unit:
        columns += [_col("harvested", "Cosechado", "text"), _col("cost_unit", "Costo por unidad")]
    columns += [
        _col("revenue", "Ingresos"),
        _col("margin", "Margen"),
        _col("margin_ha", "Margen/ha"),
        _col("margin_pct", "Margen %", "percent"),
    ]
    season = db.get(Season, p.season_id) if p.season_id else None
    return TableReport(
        key="profitability",
        title=f"Rentabilidad por {PROFIT_GROUPS[group_by].lower()}",
        subtitle=f"Temporada {season.name}" if season else "Todas las temporadas",
        columns=columns,
        rows=rows,
        totals=sum_rows(
            rows, ["area", "inputs", "machinery", "expenses", "total", "revenue", "margin"]
        ),
        notes=[
            "Ingresos: ventas sin IVA de las partidas cosechadas en cada ciclo (las notas de "
            "crédito restan). La maquinaria se valoriza por tarifa.",
        ],
    )


# --- Resultado de gestión ---


@define_report(
    key="management_result",
    title="Resultado de gestión",
    group=GROUP,
    description="Ventas − costo de lo vendido − costos de producción − mermas − estructura.",
    permission=COSTS_READ,
    filters=[PERIOD],
)
def management_result(db: Session, p: ReportParams) -> TableReport:
    subtitle, scope = _period(db, p)
    result = CostQueries(db).management_result(scope.date_from, scope.date_to)
    rows = [
        ReportRow(
            cells={
                "label": line.label,
                "amount": line.amount,
                "pct": percent(line.amount, result.sales),
            },
            style=line.style,
            indent=line.indent,
        )
        for line in result.lines
    ]
    return TableReport(
        key="management_result",
        title="Resultado de gestión",
        subtitle=subtitle,
        columns=[
            _col("label", "Concepto", "text"),
            _col("amount", "Importe"),
            _col("pct", "% de ventas", "percent"),
        ],
        rows=rows,
        notes=[
            "Importes sin IVA. La producción propia entra al stock a costo 0: su costo está en "
            "los costos de producción del período.",
            "La maquinaria cuenta por sus gastos reales (combustible, reparaciones…), no por "
            "tarifa. Retiros y aportes del dueño no forman parte del resultado.",
        ],
    )


# --- Costos por lote ---


@define_report(
    key="plot_costs",
    title="Costos por lote",
    group=GROUP,
    description="Insumos, maquinaria y gastos de cada lote en un período.",
    permission=COSTS_READ,
    filters=[PERIOD, ReportFilter(kind="farm", label="Establecimiento")],
)
def plot_costs(db: Session, p: ReportParams) -> TableReport:
    subtitle, base = _period(db, p)
    scope = ExpenseScope(date_from=base.date_from, date_to=base.date_to, farm_id=p.farm_id)
    totals: dict[UUID, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: ZERO))
    for f in input_facts(db, scope):
        if f.plot_id:
            totals[f.plot_id]["inputs"] += f.cost
    for m in machinery_facts(db, scope):
        totals[m.plot_id]["machinery"] += m.cost
    farm_only: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    for e in expense_facts(db, scope):
        if e.plot_id:
            totals[e.plot_id]["cycles" if e.crop_cycle_id else "plot"] += e.amount
        elif e.farm_id:
            farm_only[e.farm_id] += e.amount

    plots = {pl.id: pl for pl in db.scalars(select(Plot).where(Plot.id.in_(totals)))}
    rows = []
    for plot_id, t in sorted(
        totals.items(), key=lambda i: (plots[i[0]].farm.name, plots[i[0]].name)
    ):
        plot = plots[plot_id]
        total = t["inputs"] + t["machinery"] + t["cycles"] + t["plot"]
        rows.append(
            ReportRow(
                cells={
                    "farm": plot.farm.name,
                    "plot": plot.name,
                    "area": plot.area_ha,
                    "inputs": _money(t["inputs"]),
                    "machinery": _money(t["machinery"]),
                    "cycles": _money(t["cycles"]),
                    "plot_expenses": _money(t["plot"]),
                    "total": _money(total),
                    "per_ha": _money(total / plot.area_ha) if plot.area_ha else None,
                }
            )
        )
    for farm_id, amount in farm_only.items():
        farm = db.get(Farm, farm_id)
        rows.append(
            ReportRow(
                cells={
                    "farm": farm.name if farm else "",
                    "plot": "(del establecimiento)",
                    "plot_expenses": _money(amount),
                    "total": _money(amount),
                }
            )
        )
    return TableReport(
        key="plot_costs",
        title="Costos por lote",
        subtitle=subtitle,
        columns=[
            _col("farm", "Establecimiento", "text"),
            _col("plot", "Lote", "text"),
            _col("area", "Ha", "quantity"),
            _col("inputs", "Insumos"),
            _col("machinery", "Maquinaria"),
            _col("cycles", "Servicios y gastos de ciclos"),
            _col("plot_expenses", "Gastos sin asignar a ciclo"),
            _col("total", "Total"),
            _col("per_ha", "Costo/ha"),
        ],
        rows=rows,
        totals=sum_rows(rows, ["inputs", "machinery", "cycles", "plot_expenses", "total"]),
        notes=["La maquinaria se valoriza por tarifa. Montos sin IVA."],
    )


# --- Gastos ---

EXPENSE_GROUPS = {
    "detail": "Detalle",
    "category": "Categoría",
    "destination": "Destino",
    "month": "Mes",
    "party": "Proveedor",
}
EXPENSE_SCOPES = {"all": "Todos", "structure": "De estructura", "destination": "Con destino"}


class _Names:
    """Nombres de los destinos (una consulta por tabla)."""

    def __init__(self, db: Session, facts: list[ExpenseFact]) -> None:
        def ids(values: set[UUID | None]) -> set[UUID]:
            return {v for v in values if v}

        cycles = ids({f.crop_cycle_id for f in facts})
        self.cycles = {
            c.id: c.name for c in db.scalars(select(CropCycle).where(CropCycle.id.in_(cycles)))
        }
        self.plots = self._names(db, Plot, ids({f.plot_id for f in facts}))
        self.farms = self._names(db, Farm, ids({f.farm_id for f in facts}))
        self.assets = self._names(db, Asset, ids({f.asset_id for f in facts}))

    @staticmethod
    def _names(
        db: Session, model: type[Plot] | type[Farm] | type[Asset], ids: set[UUID]
    ) -> dict[UUID, str]:
        rows = db.execute(select(model.id, model.name).where(model.id.in_(ids))).all()
        return dict(rows)

    def destination(self, f: ExpenseFact) -> str:
        if f.is_structure:
            return "Estructura"
        place = next(
            (
                names[i]
                for names, i in (
                    (self.cycles, f.crop_cycle_id),
                    (self.plots, f.plot_id),
                    (self.farms, f.farm_id),
                )
                if i in names
            ),
            "",
        )
        asset = self.assets.get(f.asset_id) if f.asset_id else None
        return " · ".join(x for x in (place, asset) if x)


@define_report(
    key="expenses",
    title="Gastos",
    group=GROUP,
    description="Gastos de compras y de caja por categoría, destino, mes o proveedor.",
    permission=COSTS_READ,
    filters=[
        PERIOD,
        choice("scope", "Gastos", EXPENSE_SCOPES, "all"),
        choice("group_by", "Ver por", EXPENSE_GROUPS, "category"),
        ReportFilter(kind="expense_category", label="Categoría"),
        ReportFilter(kind="farm", label="Establecimiento"),
        ReportFilter(kind="plot", label="Lote"),
        ReportFilter(kind="asset", label="Activo"),
    ],
)
def expenses(db: Session, p: ReportParams) -> TableReport:
    subtitle, base = _period(db, p)
    facts = expense_facts(
        db,
        ExpenseScope(
            date_from=base.date_from,
            date_to=base.date_to,
            farm_id=p.farm_id,
            plot_id=p.plot_id,
            category_id=p.expense_category_id,
            asset_id=p.asset_id,
        ),
    )
    if p.scope == "structure":
        facts = [f for f in facts if f.is_structure]
    elif p.scope == "destination":
        facts = [f for f in facts if not f.is_structure]
    names = _Names(db, facts)
    group_by = p.group_by if p.group_by in EXPENSE_GROUPS else "category"
    title = "Gastos de estructura" if p.scope == "structure" else "Gastos"

    if group_by == "detail":
        rows = [
            ReportRow(
                cells={
                    "date": f.date,
                    "label": f.label,
                    "party": f.party_name,
                    "category": f.category,
                    "description": f.description,
                    "destination": names.destination(f),
                    "amount": f.amount,
                },
                link=ReportLink(
                    kind="commercial_document" if f.source == "purchase" else "cash_movement",
                    id=f.source_id,
                ),
            )
            for f in facts
        ]
        columns = [
            _col("date", "Fecha", "date"),
            _col("label", "Comprobante", "text"),
            _col("party", "Proveedor", "text"),
            _col("category", "Categoría", "text"),
            _col("description", "Detalle", "text"),
            _col("destination", "Destino", "text"),
            _col("amount", "Importe"),
        ]
    else:
        key: Callable[[ExpenseFact], str] = {
            "category": lambda f: f.category,
            "destination": names.destination,
            "month": lambda f: f.date.strftime("%m/%Y"),
            "party": lambda f: f.party_name or "(caja)",
        }[group_by]
        grouped: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for f in facts:
            grouped[key(f)] += f.amount
        total = sum(grouped.values(), ZERO)
        order = sorted(grouped.items(), key=lambda i: i[0] if group_by == "month" else -i[1])
        if group_by == "month":
            order = sorted(grouped.items(), key=lambda i: i[0][3:] + i[0][:2])
        rows = [
            ReportRow(cells={"name": name, "amount": _money(amount), "pct": percent(amount, total)})
            for name, amount in order
        ]
        columns = [
            _col("name", EXPENSE_GROUPS[group_by], "text"),
            _col("amount", "Importe"),
            _col("pct", "% del total", "percent"),
        ]
    return TableReport(
        key="expenses",
        title=title,
        subtitle=subtitle,
        columns=columns,
        rows=rows,
        totals=sum_rows(rows, ["amount"]),
        notes=["Importes sin IVA; las notas de crédito restan."],
    )


# --- Margen por producto ---


@define_report(
    key="product_margin",
    title="Margen por producto",
    group=GROUP,
    description="Ventas, costo de lo vendido y margen de cada producto (reventa, elaborados…).",
    permission=COSTS_READ,
    filters=[PERIOD, ReportFilter(kind="product_type", label="Tipo de producto")],
)
def product_margin(db: Session, p: ReportParams) -> TableReport:
    subtitle, scope = _period(db, p)
    by_product: dict[UUID, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO, ZERO])
    products = {}
    for s in sale_facts(db, scope.date_from, scope.date_to):
        if s.product is None or (p.product_type and s.product.type != p.product_type):
            continue
        products[s.product.id] = s.product
        values = by_product[s.product.id]
        values[0] += s.quantity
        values[1] += s.revenue
        values[2] += s.cost
    rows = []
    for product_id, (quantity, revenue, cost) in sorted(
        by_product.items(), key=lambda i: -(i[1][1] - i[1][2])
    ):
        product = products[product_id]
        margin = revenue - cost
        rows.append(
            ReportRow(
                cells={
                    "product": product.name,
                    "type": PRODUCT_TYPE_LABELS[ProductType(product.type)],
                    "quantity": f"{format_quantity(quantity)} {product.unit.code}",
                    "revenue": _money(revenue),
                    "cost": _money(cost),
                    "margin": _money(margin),
                    "pct": percent(margin, revenue),
                }
            )
        )
    return TableReport(
        key="product_margin",
        title="Margen por producto",
        subtitle=subtitle,
        columns=[
            _col("product", "Producto", "text"),
            _col("type", "Tipo", "text"),
            _col("quantity", "Vendido", "text"),
            _col("revenue", "Ventas"),
            _col("cost", "Costo de lo vendido"),
            _col("margin", "Margen"),
            _col("pct", "Margen %", "percent"),
        ],
        rows=rows,
        totals=sum_rows(rows, ["revenue", "cost", "margin"]),
        notes=[
            "Ventas sin IVA; costo a costo promedio del momento de la venta. La producción propia "
            "entra al stock a costo 0: su rentabilidad se ve en el reporte de Rentabilidad."
        ],
    )
