"""Conexión a PostgreSQL y sesión por request (una transacción por operación)."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import audit  # noqa: F401  (activa el historial automático de cambios)
from app.core.config import get_settings

engine = create_engine(get_settings().database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Abre una sesión; confirma si todo salió bien, revierte si hubo error."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# scope="function": el commit ocurre ANTES de enviar la respuesta,
# así un error al guardar nunca llega al usuario como "OK".
DbSession = Annotated[Session, Depends(get_db, scope="function")]
