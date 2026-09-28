"""Textos de roles: "ciclo" pasa a "cultivo" y Soporte queda como uso del desarrollador (ADR-026).

Revision ID: 3c1d6e2a9b40
Revises: ff39a7910a0c
Create Date: 2026-09-28 12:00:00-03:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "3c1d6e2a9b40"
down_revision: str | None = "ff39a7910a0c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = "Uso del desarrollador: acceso total, incluido reabrir cultivos. No se asigna a usuarios de la empresa."
OLD = "Desarrollador: acceso total, incluido reabrir ciclos."


def upgrade() -> None:
    op.execute(f"UPDATE roles SET description = '{NEW}' WHERE code = 'support'")


def downgrade() -> None:
    op.execute(f"UPDATE roles SET description = '{OLD}' WHERE code = 'support'")
