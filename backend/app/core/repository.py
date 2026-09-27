"""Repositorio base con las operaciones comunes; cada módulo lo extiende con sus consultas."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.models import BaseModel


class BaseRepository[M: BaseModel]:
    model: type[M]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id_: UUID) -> M | None:
        return self.session.get(self.model, id_)

    def add(self, instance: M) -> M:
        self.session.add(instance)
        self.session.flush()
        return instance
