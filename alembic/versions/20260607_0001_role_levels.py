"""add role levels

Revision ID: 20260607_0001
Revises: 20260529_0001
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa


revision = "20260607_0001"
down_revision = "20260529_0001"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("permission_groups", "level"):
        with op.batch_alter_table("permission_groups") as batch_op:
            batch_op.add_column(
                sa.Column("level", sa.Integer(), nullable=False, server_default="10")
            )

    op.execute("UPDATE permission_groups SET level = 1000 WHERE code = 'super_admin'")
    op.execute("UPDATE permission_groups SET level = 300 WHERE code = 'system_admin'")
    op.execute("UPDATE permission_groups SET level = 200 WHERE code IN ('plugin_admin', 'ai_admin')")


def downgrade() -> None:
    if _has_column("permission_groups", "level"):
        with op.batch_alter_table("permission_groups") as batch_op:
            batch_op.drop_column("level")
