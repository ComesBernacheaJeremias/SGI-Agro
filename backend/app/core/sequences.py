"""Numeración correlativa de comprobantes (ING-000001, EGR-000001…).

Una fila por serie en `document_sequences`, bloqueada durante la transacción:
dos altas simultáneas nunca obtienen el mismo número.
"""

from sqlalchemy import String, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.models import Base


class DocumentSequence(Base):
    __tablename__ = "document_sequences"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_number: Mapped[int] = mapped_column(default=0)


def next_number(session: Session, code: str, digits: int = 6) -> str:
    """Siguiente número de la serie `code`: next_number(db, "ING") → "ING-000001"."""
    session.execute(
        insert(DocumentSequence).values(code=code, last_number=0).on_conflict_do_nothing()
    )
    sequence = session.scalars(
        select(DocumentSequence).where(DocumentSequence.code == code).with_for_update()
    ).one()
    sequence.last_number += 1
    return f"{code}-{sequence.last_number:0{digits}d}"
