"""add derived stock cost mode

Revision ID: cc193ffc8082
Revises: fa5d94c1c109
Create Date: 2026-09-27 02:47:08.176853-03:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "cc193ffc8082"
down_revision: str | None = "fa5d94c1c109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Entradas de elaboración: su costo es lo consumido en el mismo comprobante
    op.execute("ALTER TYPE stock_cost_mode ADD VALUE IF NOT EXISTS 'derived'")


def downgrade() -> None:
    # PostgreSQL no permite quitar valores de un enum: se deja (no afecta a versiones previas)
    pass
