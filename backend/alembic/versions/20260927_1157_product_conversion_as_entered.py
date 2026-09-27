"""product conversion as entered

Revision ID: ba9f551735f9
Revises: 4066984c07f2
Create Date: 2026-09-27 11:57:29.298888-03:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ba9f551735f9"
down_revision: str | None = "4066984c07f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Antes: 1 <unidad> = factor <unidad del producto>. Ahora se guarda como se carga:
    # 1 <unidad del producto> = quantity <unidad>  →  quantity = 1 / factor
    op.add_column("product_unit_conversions", sa.Column("quantity", sa.Numeric(18, 6)))
    op.execute("UPDATE product_unit_conversions SET quantity = ROUND(1 / factor, 6)")
    op.alter_column("product_unit_conversions", "quantity", nullable=False)
    op.drop_column("product_unit_conversions", "factor")


def downgrade() -> None:
    op.add_column("product_unit_conversions", sa.Column("factor", sa.Numeric(18, 6)))
    op.execute("UPDATE product_unit_conversions SET factor = ROUND(1 / quantity, 6)")
    op.alter_column("product_unit_conversions", "factor", nullable=False)
    op.drop_column("product_unit_conversions", "quantity")
