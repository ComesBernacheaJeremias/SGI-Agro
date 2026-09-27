from typing import Annotated
from uuid import UUID

from fastapi import APIRouter

from app.core.db import DbSession
from app.modules.costs.permissions import COSTS_READ
from app.modules.costs.schemas import CycleCostOut
from app.modules.costs.service import CostQueries
from app.modules.identity.authorization import require
from app.modules.identity.models import User

router = APIRouter(prefix="/api/v1/costs", tags=["costs"])
Reader = Annotated[User, require(COSTS_READ)]


@router.get("/cycles/{id_}")
def cycle_cost(id_: UUID, db: DbSession, _: Reader) -> CycleCostOut:
    """Costo y rentabilidad de un ciclo con sus desgloses."""
    return CostQueries(db).cycle_detail(id_)
