from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import Schema


class AuditChangeOut(Schema):
    field: str
    label: str
    before: Any
    after: Any


class AuditEntryOut(Schema):
    id: UUID
    at: datetime
    action: str
    table_name: str
    table_label: str
    record_id: UUID
    user_name: str | None
    changes: list[AuditChangeOut]
