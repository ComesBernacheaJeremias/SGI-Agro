"""enable unaccent

Revision ID: 37901fc9d62a
Revises: a7c31ea69e78
Create Date: 2026-09-27 01:34:29.576303-03:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "37901fc9d62a"
down_revision: str | None = "a7c31ea69e78"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Búsquedas sin distinguir tildes ("jeremias" encuentra "Jeremías")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS unaccent")
