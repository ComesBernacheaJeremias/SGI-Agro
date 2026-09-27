"""Uso, planes y mantenimientos de activos (F6 — ADR-020).

- Lectura del medidor a una fecha = última lectura cargada (a mano o en un mantenimiento)
  + horas/km de las labores posteriores. Sin lecturas: suma del uso en labores.
- Plan: vence al llegar a "último + cada X" (uso) o "último + N meses", lo que llegue primero.
  "Próximo" cuando falta ≤ 10 % del intervalo o ≤ 15 días.
- Mantenimiento: los repuestos salen del stock (consumo con dimensión activo); el servicio
  externo es una compra con destino = activo, vinculada (no se carga dos veces).
- Costos del activo en un período: gastos reales (compras/caja con destino = activo +
  repuestos) frente a lo cargado a los ciclos por tarifa.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Subquery, func, select
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.core.sequences import next_number
from app.modules.assets.models import (
    Asset,
    AssetMeter,
    Maintenance,
    MaintenancePart,
    MaintenancePlan,
    MaintenanceStatus,
    MeterReading,
)
from app.modules.assets.schemas import MaintenanceIn, PlanOut, PlanStatusOut, Ref
from app.modules.commercial.expenses import expense_rows
from app.modules.commercial.models import CommercialDocument, Direction, Status
from app.modules.inventory.models import CostMode, DocumentType, StockDocument, StockMove
from app.modules.inventory.schemas import StockAlertOut
from app.modules.inventory.service import MoveSpec, StockDocumentService
from app.modules.production.models import FieldOperation, FieldOperationAsset, OperationStatus

ZERO = Decimal(0)
UPCOMING_SHARE = Decimal("0.10")
UPCOMING_DAYS = 15
SOURCE = "assets"


def unit_of(asset: Asset) -> str:
    return "km" if asset.meter == AssetMeter.KM else "h"


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


# --- Consultas compartidas (ficha, reporte, resultado de gestión) ---


def usage_rows() -> Subquery:
    """Uso de cada activo en labores vigentes: asset_id, date, usage, cost (por tarifa)."""
    return (
        select(
            FieldOperationAsset.asset_id,
            FieldOperation.date,
            FieldOperationAsset.usage,
            (FieldOperationAsset.usage * FieldOperationAsset.rate).label("cost"),
        )
        .join(FieldOperation, FieldOperation.id == FieldOperationAsset.field_operation_id)
        .where(FieldOperation.status == OperationStatus.ACTIVE)
        .subquery("asset_usage")
    )


def parts_rows() -> Subquery:
    """Repuestos consumidos en mantenimientos: asset_id, date, cost."""
    return (
        select(StockMove.asset_id, StockMove.date, (-StockMove.total_cost).label("cost"))
        .join(StockDocument, StockDocument.id == StockMove.document_id)
        .where(
            StockDocument.source_module == SOURCE,
            StockMove.cancelled.is_(False),
            StockMove.quantity < 0,
        )
        .subquery("asset_parts")
    )


@dataclass(frozen=True)
class AssetCost:
    usage: Decimal = ZERO
    rate_cost: Decimal = ZERO
    expenses: Decimal = ZERO
    parts: Decimal = ZERO

    @property
    def total(self) -> Decimal:
        return self.expenses + self.parts

    @property
    def real_rate(self) -> Decimal | None:
        return (self.total / self.usage).quantize(Decimal("0.01")) if self.usage else None


def asset_costs(
    session: Session,
    date_from: date | None,
    date_to: date | None,
    asset_ids: list[UUID] | None = None,
) -> dict[UUID, AssetCost]:
    def summed(sub: Subquery, *columns: str) -> dict[UUID, tuple[Decimal, ...]]:
        query = select(sub.c.asset_id, *(func.sum(sub.c[c]) for c in columns)).where(
            sub.c.asset_id.is_not(None)
        )
        if date_from:
            query = query.where(sub.c.date >= date_from)
        if date_to:
            query = query.where(sub.c.date <= date_to)
        if asset_ids is not None:
            query = query.where(sub.c.asset_id.in_(asset_ids))
        return {
            r[0]: tuple(Decimal(v or 0) for v in r[1:])
            for r in session.execute(query.group_by(sub.c.asset_id)).all()
        }

    usage = summed(usage_rows(), "usage", "cost")
    expenses = summed(expense_rows(), "amount")
    parts = summed(parts_rows(), "cost")
    return {
        asset_id: AssetCost(
            usage=usage.get(asset_id, (ZERO, ZERO))[0],
            rate_cost=usage.get(asset_id, (ZERO, ZERO))[1],
            expenses=expenses.get(asset_id, (ZERO,))[0],
            parts=parts.get(asset_id, (ZERO,))[0],
        )
        for asset_id in {*usage, *expenses, *parts}
    }


# --- Medidor ---


class MeterQueries:
    def __init__(self, session: Session) -> None:
        self.session = session

    def last_reading(self, asset_id: UUID, day: date) -> tuple[date, Decimal] | None:
        """Última lectura cargada hasta `day` (a mano o en un mantenimiento)."""
        candidates = [
            self.session.execute(
                select(MeterReading.date, MeterReading.value)
                .where(
                    MeterReading.asset_id == asset_id,
                    MeterReading.is_active.is_(True),
                    MeterReading.date <= day,
                )
                .order_by(MeterReading.date.desc(), MeterReading.value.desc())
                .limit(1)
            ).first(),
            self.session.execute(
                select(Maintenance.date, Maintenance.meter_reading)
                .where(
                    Maintenance.asset_id == asset_id,
                    Maintenance.status == MaintenanceStatus.ACTIVE,
                    Maintenance.meter_reading.is_not(None),
                    Maintenance.date <= day,
                )
                .order_by(Maintenance.date.desc(), Maintenance.meter_reading.desc())
                .limit(1)
            ).first(),
        ]
        found = [(r[0], r[1]) for r in candidates if r is not None and r[1] is not None]
        return max(found) if found else None

    def reading_at(self, asset_id: UUID, day: date) -> Decimal:
        """Lectura estimada: última cargada + uso en labores posteriores."""
        last = self.last_reading(asset_id, day)
        usage = usage_rows()
        query = select(func.coalesce(func.sum(usage.c.usage), 0)).where(
            usage.c.asset_id == asset_id, usage.c.date <= day
        )
        if last:
            query = query.where(usage.c.date > last[0])
        return (last[1] if last else ZERO) + Decimal(self.session.execute(query).scalar_one())


# --- Planes ---


class PlanQueries:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.meter = MeterQueries(session)

    def status(self, plan: MaintenancePlan, today: date | None = None) -> PlanStatusOut:
        today = today or date.today()
        last = self.session.execute(
            select(Maintenance.date, Maintenance.meter_reading)
            .where(Maintenance.plan_id == plan.id, Maintenance.status == MaintenanceStatus.ACTIVE)
            .order_by(Maintenance.date.desc())
            .limit(1)
        ).first()
        if last is None:
            base_date, base_reading = plan.start_date, plan.start_reading
        else:
            base_date = last[0]
            base_reading = (
                Decimal(last[1])
                if last[1] is not None
                else self.meter.reading_at(plan.asset_id, base_date)
            )
        current = self.meter.reading_at(plan.asset_id, today)
        due_reading = base_reading + plan.every_usage if plan.every_usage else None
        due_date = add_months(base_date, plan.every_months) if plan.every_months else None
        remaining_usage = due_reading - current if due_reading is not None else None
        remaining_days = (due_date - today).days if due_date else None

        state = "ok"
        if (remaining_usage is not None and remaining_usage <= 0) or (
            remaining_days is not None and remaining_days < 0
        ):
            state = "overdue"
        elif (
            remaining_usage is not None
            and plan.every_usage
            and remaining_usage <= plan.every_usage * UPCOMING_SHARE
        ) or (remaining_days is not None and remaining_days <= UPCOMING_DAYS):
            state = "upcoming"
        return PlanStatusOut(
            plan=PlanOut.model_validate(plan),
            asset=Ref(id=plan.asset.id, name=plan.asset.name),
            unit=unit_of(plan.asset),
            last_date=base_date,
            last_reading=base_reading,
            due_reading=due_reading,
            due_date=due_date,
            current_reading=current,
            remaining_usage=remaining_usage,
            remaining_days=remaining_days,
            state=state,
        )

    def statuses(self, asset_id: UUID | None = None) -> list[PlanStatusOut]:
        query = (
            select(MaintenancePlan)
            .join(Asset)
            .where(MaintenancePlan.is_active.is_(True), Asset.is_active.is_(True))
            .order_by(Asset.name, MaintenancePlan.name)
        )
        if asset_id:
            query = query.where(MaintenancePlan.asset_id == asset_id)
        return [self.status(p) for p in self.session.scalars(query)]

    def alerts(self) -> list[PlanStatusOut]:
        """Planes próximos o vencidos (vencidos primero)."""
        pending = [s for s in self.statuses() if s.state != "ok"]
        return sorted(pending, key=lambda s: (s.state != "overdue", s.asset.name))


# --- Mantenimientos ---


class MaintenanceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.stock = StockDocumentService(session)

    def get(self, id_: UUID) -> Maintenance:
        maintenance = self.session.get(Maintenance, id_)
        if maintenance is None:
            raise NotFoundError("No se encontró el mantenimiento.")
        return maintenance

    def search(
        self, asset_id: UUID | None, status: MaintenanceStatus | None, page: PageParams
    ) -> tuple[list[Maintenance], int]:
        query = select(Maintenance).order_by(Maintenance.date.desc(), Maintenance.number.desc())
        if asset_id:
            query = query.where(Maintenance.asset_id == asset_id)
        if status:
            query = query.where(Maintenance.status == status)
        return paginate(self.session, query, page)

    def create(self, data: MaintenanceIn) -> tuple[Maintenance, list[StockAlertOut]]:
        self._validate(data)
        maintenance = Maintenance(id=uuid7(), number=next_number(self.session, "MNT"))
        self.session.add(maintenance)
        self._fill(maintenance, data)
        self.session.flush()
        return maintenance, self._sync_stock(maintenance)

    def update(self, id_: UUID, data: MaintenanceIn) -> tuple[Maintenance, list[StockAlertOut]]:
        maintenance = self._editable(id_)
        if data.asset_id != maintenance.asset_id:
            raise BusinessRuleError("No se puede cambiar el activo.", code="ASSET")
        self._validate(data)
        maintenance.parts.clear()
        self._fill(maintenance, data)
        self.session.flush()
        return maintenance, self._sync_stock(maintenance)

    def cancel(self, id_: UUID) -> tuple[Maintenance, list[StockAlertOut]]:
        maintenance = self._editable(id_)
        maintenance.status = MaintenanceStatus.CANCELLED
        self.session.flush()
        if maintenance.stock_document_id:
            return maintenance, self.stock.cancel_system(maintenance.stock_document_id)
        return maintenance, []

    def _editable(self, id_: UUID) -> Maintenance:
        maintenance = self.get(id_)
        if maintenance.status == MaintenanceStatus.CANCELLED:
            raise BusinessRuleError("El mantenimiento está anulado.", code="CANCELLED")
        return maintenance

    def _validate(self, data: MaintenanceIn) -> None:
        asset = self.session.get(Asset, data.asset_id)
        if asset is None or not asset.is_active:
            raise BusinessRuleError("El activo no existe o está dado de baja.", code="ASSET")
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        if data.plan_id:
            plan = self.session.get(MaintenancePlan, data.plan_id)
            if plan is None or plan.asset_id != data.asset_id:
                raise BusinessRuleError("El plan no corresponde al activo.", code="PLAN")
        if data.parts and data.warehouse_id is None:
            raise BusinessRuleError(
                "Elegí el almacén de donde salen los repuestos.", code="WAREHOUSE_REQUIRED"
            )
        if data.purchase_document_id:
            doc = self.session.get(CommercialDocument, data.purchase_document_id)
            if doc is None or doc.direction != Direction.PURCHASE or doc.status != Status.ACTIVE:
                raise BusinessRuleError(
                    "La compra vinculada no existe o está anulada.", code="PURCHASE"
                )

    def _fill(self, maintenance: Maintenance, data: MaintenanceIn) -> None:
        maintenance.asset_id = data.asset_id
        maintenance.asset = self.session.get(Asset, data.asset_id)  # type: ignore[assignment]
        maintenance.date = data.date
        maintenance.kind = data.kind
        maintenance.plan_id = data.plan_id
        maintenance.description = data.description
        maintenance.meter_reading = data.meter_reading
        maintenance.warehouse_id = data.warehouse_id if data.parts else None
        maintenance.purchase_document_id = data.purchase_document_id
        for line_no, part in enumerate(data.parts, start=1):
            spec = self.stock.line(part.product_id, part.unit_id, part.quantity)
            maintenance.parts.append(
                MaintenancePart(
                    line_no=line_no,
                    product=spec.product,
                    product_id=spec.product.id,
                    unit=spec.unit,
                    unit_id=spec.unit.id,
                    quantity=part.quantity,
                )
            )

    def _sync_stock(self, maintenance: Maintenance) -> list[StockAlertOut]:
        if not maintenance.parts:
            if maintenance.stock_document_id:
                alerts = self.stock.cancel_system(maintenance.stock_document_id)
                maintenance.stock_document_id = None
                return alerts
            return []
        assert maintenance.warehouse_id is not None  # noqa: S101 (validado)
        lines = []
        for part in maintenance.parts:
            spec = self.stock.line(part.product_id, part.unit_id, part.quantity)
            spec.moves = [
                MoveSpec(
                    maintenance.warehouse_id,
                    -spec.base_quantity,
                    CostMode.AVERAGE,
                    dimensions={"asset_id": maintenance.asset_id},
                )
            ]
            lines.append(spec)
        document, alerts = self.stock.save_system(
            document_id=maintenance.stock_document_id,
            type_=DocumentType.CONSUMPTION,
            date_=maintenance.date,
            warehouse_id=maintenance.warehouse_id,
            source_module=SOURCE,
            source_id=maintenance.id,
            lines=lines,
            notes=f"Mantenimiento {maintenance.number} · {maintenance.asset.name}",
        )
        maintenance.stock_document_id = document.id
        self.session.flush()
        return alerts
