"""user plugin likes and review rating retirement

Revision ID: 20260529_0001
Revises: 20260526_0001
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260529_0001"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plugin_id", "user_id", name="uq_plugin_like_user"),
    )
    op.create_index(op.f("ix_plugin_likes_id"), "plugin_likes", ["id"], unique=False)
    op.create_index(op.f("ix_plugin_likes_plugin_id"), "plugin_likes", ["plugin_id"], unique=False)
    op.create_index(op.f("ix_plugin_likes_user_id"), "plugin_likes", ["user_id"], unique=False)

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column("rating", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column("rating", existing_type=sa.Float(), nullable=False)

    op.drop_index(op.f("ix_plugin_likes_user_id"), table_name="plugin_likes")
    op.drop_index(op.f("ix_plugin_likes_plugin_id"), table_name="plugin_likes")
    op.drop_index(op.f("ix_plugin_likes_id"), table_name="plugin_likes")
    op.drop_table("plugin_likes")
