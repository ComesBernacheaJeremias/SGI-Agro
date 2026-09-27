"""Endpoints de salud: /health (la app responde) y /health/ready (la base también)."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import DbSession

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
