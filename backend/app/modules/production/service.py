"""Ciclos productivos y labores (incluida la cosecha).

Ciclo: abrir → (labores y cosechas) → finalizar (congela costos) → [reabrir: solo Soporte].
Labor: se carga sobre uno o varios ciclos; insumos y horas se reparten por superficie.
  - Insumos → comprobante de stock "Consumo" con las dimensiones de cada ciclo.
  - Cosecha → partida + comprobante "Cosecha" (ingresa el producto a costo 0: su costo
    está en el ciclo, ADR-012).
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.formatting import format_date, format_quantity
from app.core.sequences import next_number
from app.modules.assets.models import Asset, AssetStatus
from app.modules.inventory.models import CostMode, DocumentType, StockMove
from app.modules.inventory.schemas import StockAlertOut
from app.modules.inventory.service import LineSpec, MoveSpec, StockDocumentService
from app.modules.production.catalog import active_cycles_area, season_for
from app.modules.production.models import (
    Batch,
    Crop,
    CropCycle,
    CycleStatus,
    FieldOperation,
    FieldOperationAsset,
    FieldOperationCycle,
    FieldOperationInput,
    OperationStatus,
    OperationType,
    Plot,
)
from app.modules.production.schemas import (
    CycleCreate,
    CycleUpdate,
    HarvestIn,
    InputIn,
    OperationIn,
)

QTY = Decimal("0.0001")
SOURCE = "production"


def ensure_open(cycle: CropCycle) -> None:
    if cycle.is_finished:
        raise BusinessRuleError(
            f"El ciclo '{cycle.name}' está finalizado: no se pueden cargar ni modificar sus "
            "labores. Si hace falta, pedile a Soporte que lo reabra.",
            code="CYCLE_FINISHED",
        )


# --- Ciclos ---


class CycleService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id_: UUID) -> CropCycle:
        cycle = self.session.get(CropCycle, id_)
        if cycle is None:
            raise NotFoundError("No se encontró el ciclo.")
        return cycle

    def create(self, data: CycleCreate) -> CropCycle:
        plot = self.session.get(Plot, data.plot_id)
        crop = self.session.get(Crop, data.crop_id)
        if plot is None or not plot.is_active:
            raise BusinessRuleError("El lote no existe o está inactivo.", code="PLOT")
        if crop is None or not crop.is_active:
            raise BusinessRuleError("El cultivo no existe o está inactivo.", code="CROP")
        self._check_area(plot, data.area_ha, exclude=None)
        self._check_dates(data.start_date, data.expected_end_date)
        season = season_for(self.session, data.start_date)
        cycle = CropCycle(
            name=f"{crop.name} · {plot.name} · {season.name}",
            plot=plot,
            plot_id=plot.id,
            crop=crop,
            crop_id=crop.id,
            season=season,
            season_id=season.id,
            area_ha=data.area_ha,
            start_date=data.start_date,
            expected_end_date=data.expected_end_date,
            notes=data.notes,
        )
        self.session.add(cycle)
        self.session.flush()
        return cycle

    def update(self, id_: UUID, data: CycleUpdate) -> CropCycle:
        cycle = self.get(id_)
        ensure_open(cycle)
        values = data.model_dump(exclude_unset=True)
        if "area_ha" in values:
            self._check_area(cycle.plot, values["area_ha"], exclude=cycle.id)
        start = values.get("start_date", cycle.start_date)
        self._check_dates(start, values.get("expected_end_date", cycle.expected_end_date))
        first = self._first_operation_date(cycle.id)
        if first and start > first:
            raise BusinessRuleError(
                f"El inicio no puede ser posterior a la primera labor ({format_date(first)}).",
                code="CYCLE_START",
            )
        for field, value in values.items():
            setattr(cycle, field, value)
        self.session.flush()
        return cycle

    def finish(self, id_: UUID, end_date: date) -> CropCycle:
        cycle = self.get(id_)
        ensure_open(cycle)
        if end_date < cycle.start_date or end_date > date.today():
            raise BusinessRuleError(
                "La fecha de fin tiene que estar entre el inicio del ciclo y hoy.",
                code="CYCLE_END",
            )
        last = self._last_operation_date(cycle.id)
        if last and end_date < last:
            raise BusinessRuleError(
                f"La fecha de fin no puede ser anterior a la última labor ({format_date(last)}).",
                code="CYCLE_END",
            )
        cycle.status = CycleStatus.FINISHED
        cycle.end_date = end_date
        # Congelar costos: el recálculo del costo promedio ya no los cambia (ADR-004)
        self.session.execute(
            update(StockMove).where(StockMove.crop_cycle_id == cycle.id).values(frozen=True)
        )
        self.session.flush()
        return cycle

    def reopen(self, id_: UUID, reason: str) -> CropCycle:
        cycle = self.get(id_)
        if not cycle.is_finished:
            raise BusinessRuleError("El ciclo no está finalizado.", code="CYCLE_NOT_FINISHED")
        self._check_area(cycle.plot, cycle.area_ha, exclude=cycle.id)
        cycle.status = CycleStatus.ACTIVE
        cycle.end_date = None
        cycle.reopen_reason = reason
        self.session.execute(
            update(StockMove).where(StockMove.crop_cycle_id == cycle.id).values(frozen=False)
        )
        # Los costos vuelven a seguir al promedio: recalcular los insumos del ciclo
        products = set(
            self.session.scalars(
                select(StockMove.product_id).where(StockMove.crop_cycle_id == cycle.id).distinct()
            )
        )
        StockDocumentService(self.session)._recalculate(products, cycle.start_date)
        self.session.flush()
        return cycle

    # --- Validaciones ---

    def _check_area(self, plot: Plot, area: Decimal, exclude: UUID | None) -> None:
        used = active_cycles_area(self.session, plot.id, exclude)
        if used + area > plot.area_ha:
            free = plot.area_ha - used
            raise BusinessRuleError(
                f"El lote {plot.name} tiene {format_quantity(plot.area_ha)} ha y hay "
                f"{format_quantity(used)} ha ocupadas por otros ciclos en curso: quedan "
                f"{format_quantity(free)} ha libres.",
                code="PLOT_AREA",
            )

    @staticmethod
    def _check_dates(start: date, expected_end: date | None) -> None:
        if expected_end and expected_end < start:
            raise BusinessRuleError(
                "El fin estimado no puede ser anterior al inicio.", code="CYCLE_DATES"
            )

    def _operation_dates(self, cycle_id: UUID) -> tuple[date | None, date | None]:
        row = self.session.execute(
            select(func.min(FieldOperation.date), func.max(FieldOperation.date))
            .join(FieldOperationCycle)
            .where(
                FieldOperationCycle.crop_cycle_id == cycle_id,
                FieldOperation.status == OperationStatus.ACTIVE,
            )
        ).one()
        return row[0], row[1]

    def _first_operation_date(self, cycle_id: UUID) -> date | None:
        return self._operation_dates(cycle_id)[0]

    def _last_operation_date(self, cycle_id: UUID) -> date | None:
        return self._operation_dates(cycle_id)[1]


# --- Labores ---


class FieldOperationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.stock = StockDocumentService(session)

    def get(self, id_: UUID) -> FieldOperation:
        operation = self.session.get(FieldOperation, id_)
        if operation is None:
            raise NotFoundError("No se encontró la labor.")
        return operation

    def create(self, data: OperationIn) -> tuple[FieldOperation, list[StockAlertOut]]:
        if data.id and (existing := self.session.get(FieldOperation, data.id)):
            return existing, []  # reenvío desde la carga sin conexión
        op_type, cycles = self._validate(data)
        operation = FieldOperation(id=data.id or uuid7(), number=next_number(self.session, "LAB"))
        self.session.add(operation)
        self._fill(operation, data, op_type, cycles, previous_rates={})
        self.session.flush()
        return operation, self._sync_stock(operation)

    def update(self, id_: UUID, data: OperationIn) -> tuple[FieldOperation, list[StockAlertOut]]:
        operation = self._editable(id_)
        op_type, cycles = self._validate(data)
        if op_type.is_harvest != operation.is_harvest:
            raise BusinessRuleError(
                "No se puede cambiar una cosecha por otra labor (ni al revés).",
                code="HARVEST_CHANGE",
            )
        # La tarifa de un activo que ya estaba en la labor se conserva (no se relee la actual)
        previous_rates = {a.asset_id: a.rate for a in operation.assets}
        operation.cycles.clear()
        operation.inputs.clear()
        operation.assets.clear()
        self._fill(operation, data, op_type, cycles, previous_rates)
        self.session.flush()
        return operation, self._sync_stock(operation)

    def cancel(self, id_: UUID) -> tuple[FieldOperation, list[StockAlertOut]]:
        operation = self._editable(id_)
        operation.status = OperationStatus.CANCELLED
        self.session.flush()
        alerts: list[StockAlertOut] = []
        if operation.stock_document_id:
            alerts = self.stock.cancel_system(operation.stock_document_id)
        return operation, alerts

    # --- Validación ---

    def _editable(self, id_: UUID) -> FieldOperation:
        operation = self.get(id_)
        if operation.status == OperationStatus.CANCELLED:
            raise BusinessRuleError("La labor está anulada.", code="CANCELLED")
        for share in operation.cycles:
            ensure_open(share.crop_cycle)
        return operation

    def _validate(self, data: OperationIn) -> tuple[OperationType, list[CropCycle]]:
        if data.date > date.today():
            raise BusinessRuleError("La fecha no puede ser posterior a hoy.", code="FUTURE_DATE")
        op_type = self.session.get(OperationType, data.operation_type_id)
        if op_type is None or not op_type.is_active:
            raise BusinessRuleError("El tipo de labor no existe o está inactivo.", code="TYPE")
        ids = [c.crop_cycle_id for c in data.cycles]
        if len(ids) != len(set(ids)):
            raise BusinessRuleError("Un ciclo está repetido en la labor.", code="DUPLICATE_CYCLE")
        cycles = []
        for share in data.cycles:
            cycle = self.session.get(CropCycle, share.crop_cycle_id)
            if cycle is None:
                raise NotFoundError("No se encontró uno de los ciclos.")
            ensure_open(cycle)
            if data.date < cycle.start_date:
                raise BusinessRuleError(
                    f"La labor es anterior al inicio del ciclo '{cycle.name}' "
                    f"({format_date(cycle.start_date)}).",
                    code="BEFORE_CYCLE",
                )
            if share.area_ha is not None and share.area_ha > cycle.area_ha:
                raise BusinessRuleError(
                    f"La superficie trabajada en '{cycle.name}' supera la del ciclo.",
                    code="SHARE_AREA",
                )
            cycles.append(cycle)
        if data.inputs and not op_type.uses_inputs:
            raise BusinessRuleError(f"'{op_type.name}' no lleva insumos.", code="NO_INPUTS")
        if data.assets and not op_type.uses_assets:
            raise BusinessRuleError(f"'{op_type.name}' no lleva maquinaria.", code="NO_ASSETS")
        if op_type.is_harvest:
            if data.harvest is None:
                raise BusinessRuleError("Cargá los datos de la cosecha.", code="HARVEST_REQUIRED")
            if len(cycles) != 1:
                raise BusinessRuleError(
                    "Una cosecha se carga sobre un solo ciclo.", code="HARVEST_ONE_CYCLE"
                )
        elif data.harvest is not None:
            raise BusinessRuleError(f"'{op_type.name}' no es una cosecha.", code="NOT_HARVEST")
        for item in data.inputs:
            if (item.quantity is None) == (item.dose_per_ha is None):
                raise BusinessRuleError(
                    "En cada insumo cargá la cantidad total o la dosis por hectárea.",
                    code="INPUT_QUANTITY",
                )
        asset_ids = [a.asset_id for a in data.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise BusinessRuleError("Un activo está repetido en la labor.", code="DUPLICATE_ASSET")
        return op_type, cycles

    # --- Armado ---

    def _fill(
        self,
        operation: FieldOperation,
        data: OperationIn,
        op_type: OperationType,
        cycles: list[CropCycle],
        previous_rates: dict[UUID, Decimal],
    ) -> None:
        operation.date = data.date
        operation.operation_type = op_type
        operation.operation_type_id = op_type.id
        operation.notes = data.notes
        shares = [
            share.area_ha or cycle.area_ha for share, cycle in zip(data.cycles, cycles, strict=True)
        ]
        operation.total_area_ha = sum(shares, Decimal(0))
        for cycle, area in zip(cycles, shares, strict=True):
            operation.cycles.append(
                FieldOperationCycle(crop_cycle=cycle, crop_cycle_id=cycle.id, area_ha=area)
            )
        for line_no, item in enumerate(data.inputs, start=1):
            operation.inputs.append(self._input(line_no, item, operation.total_area_ha))
        for use in data.assets:
            asset = self.session.get(Asset, use.asset_id)
            if asset is None or not asset.is_active:
                raise BusinessRuleError("Un activo no existe o está inactivo.", code="ASSET")
            if asset.status == AssetStatus.IN_REPAIR:
                raise BusinessRuleError(
                    f"'{asset.name}' está en reparación.", code="ASSET_IN_REPAIR"
                )
            operation.assets.append(
                FieldOperationAsset(
                    asset=asset,
                    asset_id=asset.id,
                    usage=use.usage,
                    rate=previous_rates.get(asset.id, asset.rate),
                )
            )
        self._set_harvest(operation, data.harvest, cycles[0] if op_type.is_harvest else None)

    def _input(self, line_no: int, item: InputIn, total_area: Decimal) -> FieldOperationInput:
        spec = self.stock.line(item.product_id, item.unit_id, Decimal(1))  # valida producto/unidad
        self.stock.active_warehouse(item.warehouse_id)
        quantity = item.quantity or ((item.dose_per_ha or Decimal(0)) * total_area).quantize(QTY)
        return FieldOperationInput(
            line_no=line_no,
            product=spec.product,
            product_id=spec.product.id,
            unit=spec.unit,
            unit_id=spec.unit.id,
            quantity=quantity,
            dose_per_ha=item.dose_per_ha,
            warehouse_id=item.warehouse_id,
        )

    def _set_harvest(
        self, operation: FieldOperation, harvest: HarvestIn | None, cycle: CropCycle | None
    ) -> None:
        if harvest is None or cycle is None:
            operation.harvest_product_id = None
            operation.harvest_unit_id = None
            operation.harvest_quantity = None
            operation.harvest_warehouse_id = None
            operation.is_final_harvest = False
            return
        product_id = harvest.product_id or cycle.crop.harvest_product_id
        self.stock.line(product_id, harvest.unit_id, harvest.quantity)  # valida
        self.stock.active_warehouse(harvest.warehouse_id)
        operation.harvest_product_id = product_id
        operation.harvest_unit_id = harvest.unit_id
        operation.harvest_quantity = harvest.quantity
        operation.harvest_warehouse_id = harvest.warehouse_id
        operation.is_final_harvest = harvest.is_final

    # --- Stock ---

    def _dimensions(self, operation: FieldOperation, cycle: CropCycle) -> dict[str, UUID | None]:
        return {
            "farm_id": cycle.plot.farm_id,
            "plot_id": cycle.plot_id,
            "crop_cycle_id": cycle.id,
            "field_operation_id": operation.id,
        }

    def _sync_stock(self, operation: FieldOperation) -> list[StockAlertOut]:
        """Crea, reemplaza o anula el comprobante de stock de la labor."""
        lines, doc_type, warehouse = self._stock_lines(operation)
        if not lines:
            if operation.stock_document_id:
                alerts = self.stock.cancel_system(operation.stock_document_id)
                operation.stock_document_id = None
                return alerts
            return []
        document, alerts = self.stock.save_system(
            document_id=operation.stock_document_id,
            type_=doc_type,
            date_=operation.date,
            warehouse_id=warehouse,
            source_module=SOURCE,
            source_id=operation.id,
            lines=lines,
            notes=f"Labor {operation.number}: {operation.operation_type.name}",
        )
        operation.stock_document_id = document.id
        self.session.flush()
        return alerts

    def _stock_lines(self, operation: FieldOperation) -> tuple[list[LineSpec], DocumentType, UUID]:
        if operation.is_harvest:
            return self._harvest_lines(operation)
        lines = []
        for item in operation.inputs:
            spec = self.stock.line(item.product_id, item.unit_id, item.quantity)
            spec.moves = self._split(operation, item.warehouse_id, -spec.base_quantity)
            lines.append(spec)
        warehouse = operation.inputs[0].warehouse_id if operation.inputs else uuid7()
        return lines, DocumentType.CONSUMPTION, warehouse

    def _split(
        self, operation: FieldOperation, warehouse_id: UUID, total: Decimal
    ) -> list[MoveSpec]:
        """Reparte una cantidad entre los ciclos según su superficie (el último, el resto)."""
        moves, assigned = [], Decimal(0)
        shares = list(operation.cycles)
        for index, share in enumerate(shares):
            if index == len(shares) - 1:
                quantity = total - assigned
            else:
                quantity = (total * share.area_ha / operation.total_area_ha).quantize(QTY)
                assigned += quantity
            moves.append(
                MoveSpec(
                    warehouse_id,
                    quantity,
                    CostMode.AVERAGE,
                    dimensions=self._dimensions(operation, share.crop_cycle),
                )
            )
        return moves

    def _harvest_lines(
        self, operation: FieldOperation
    ) -> tuple[list[LineSpec], DocumentType, UUID]:
        cycle = operation.cycles[0].crop_cycle
        assert operation.harvest_product_id and operation.harvest_unit_id  # noqa: S101
        assert operation.harvest_quantity and operation.harvest_warehouse_id  # noqa: S101
        batch = self._batch(operation, cycle)
        spec = self.stock.line(
            operation.harvest_product_id, operation.harvest_unit_id, operation.harvest_quantity
        )
        spec.moves = [
            MoveSpec(
                operation.harvest_warehouse_id,
                spec.base_quantity,
                CostMode.OWN,  # costo 0: el costo real está en el ciclo (ADR-012)
                dimensions={**self._dimensions(operation, cycle), "batch_id": batch.id},
            )
        ]
        return [spec], DocumentType.HARVEST, operation.harvest_warehouse_id

    def _batch(self, operation: FieldOperation, cycle: CropCycle) -> Batch:
        """Partida de la cosecha (una por labor; se reutiliza al editar)."""
        batch = self.session.scalar(select(Batch).where(Batch.field_operation_id == operation.id))
        product_id = operation.harvest_product_id
        assert product_id is not None  # noqa: S101
        if batch is None:
            batch = Batch(
                code=self._batch_code(cycle, operation.date),
                product_id=product_id,
                crop_cycle_id=cycle.id,
                field_operation_id=operation.id,
                date=operation.date,
            )
            self.session.add(batch)
        else:
            batch.product_id = product_id
            batch.date = operation.date
        self.session.flush()
        return batch

    def _batch_code(self, cycle: CropCycle, day: date) -> str:
        def slug(text: str) -> str:
            plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
            return re.sub(r"[^A-Z0-9]+", "", plain.upper())[:12]

        base = f"{slug(cycle.plot.name)}-{slug(cycle.crop.species)}-{day:%Y%m%d}"
        existing = set(self.session.scalars(select(Batch.code).where(Batch.code.like(f"{base}%"))))
        if base not in existing:
            return base
        suffix = 2
        while f"{base}-{suffix}" in existing:
            suffix += 1
        return f"{base}-{suffix}"
