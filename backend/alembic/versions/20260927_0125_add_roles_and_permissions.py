"""add roles and permissions

Revision ID: 9f385537601b
Revises: da9ff898fd4d
Create Date: 2026-09-27 01:25:54.629424-03:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from uuid6 import uuid7

SYSTEM_ROLES = [
    ("support", "Soporte", "Desarrollador: acceso total, incluido reabrir ciclos."),
    ("owner", "Dueño", "Acceso total a la operación y administración."),
    ("staff", "Administrativo", "Carga diaria. Permisos editables."),
    ("read_only", "Solo lectura", "Puede ver todo, no modificar."),
]


revision: str = "9f385537601b"
down_revision: str | None = "da9ff898fd4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission", name=op.f("pk_role_permissions")),
    )
    # Roles del sistema
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        roles,
        [
            {"id": uuid7(), "code": code, "name": name, "description": desc, "is_system": True}
            for code, name, desc in SYSTEM_ROLES
        ],
    )

    # Usuarios existentes → soporte (el primer usuario es el desarrollador)
    op.add_column("users", sa.Column("role_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE users SET role_id = (SELECT id FROM roles WHERE code = 'support')")
    op.alter_column("users", "role_id", nullable=False)
    op.create_foreign_key(op.f("fk_users_role_id_roles"), "users", "roles", ["role_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(op.f("fk_users_role_id_roles"), "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_table("roles")
