"""Destino de un gasto (dimensiones de costo, ADR-005).

Se completa hacia arriba: un ciclo implica su lote y su establecimiento; un lote, su
establecimiento. Un gasto no se puede imputar a un ciclo finalizado (ADR-004).
Sin destino = gasto de estructura (se ve aparte, no se reparte — ADR-011).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.assets.models import Asset
from app.modules.commercial.schemas import Destination, DestinationOut, Ref
from app.modules.production.models import CropCycle, Farm, Plot
from app.modules.production.service import ensure_open

DIMENSIONS = ("farm_id", "plot_id", "crop_cycle_id", "asset_id")


def resolve_destination(session: Session, dest: Destination) -> dict[str, UUID | None]:
    farm_id, plot_id = dest.farm_id, dest.plot_id
    if dest.crop_cycle_id:
        cycle = session.get(CropCycle, dest.crop_cycle_id)
        if cycle is None:
            raise NotFoundError("No se encontró el cultivo de destino.")
        ensure_open(cycle)
        plot_id, farm_id = cycle.plot_id, cycle.plot.farm_id
    elif plot_id:
        plot = session.get(Plot, plot_id)
        if plot is None:
            raise NotFoundError("No se encontró el lote de destino.")
        farm_id = plot.farm_id
    elif farm_id and session.get(Farm, farm_id) is None:
        raise NotFoundError("No se encontró el establecimiento de destino.")
    if dest.asset_id and session.get(Asset, dest.asset_id) is None:
        raise NotFoundError("No se encontró el activo de destino.")
    return {
        "farm_id": farm_id,
        "plot_id": plot_id,
        "crop_cycle_id": dest.crop_cycle_id,
        "asset_id": dest.asset_id,
    }


def ensure_destination_open(session: Session, obj: Any) -> None:
    """Un registro existente con destino en un ciclo finalizado no se puede modificar."""
    if getattr(obj, "crop_cycle_id", None):
        cycle = session.get(CropCycle, obj.crop_cycle_id)
        if cycle is not None:
            ensure_open(cycle)


def destination_out(session: Session, obj: Any) -> DestinationOut:
    def ref(model: Any, id_: UUID | None, attr: str = "name") -> Ref | None:
        if id_ is None:
            return None
        row = session.get(model, id_)
        return Ref(id=id_, name=getattr(row, attr)) if row else None

    return DestinationOut(
        farm=ref(Farm, obj.farm_id),
        plot=ref(Plot, obj.plot_id),
        crop_cycle=ref(CropCycle, obj.crop_cycle_id),
        asset=ref(Asset, obj.asset_id),
    )
