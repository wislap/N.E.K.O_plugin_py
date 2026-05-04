"""add trusted release fields to versions

Revision ID: 20260505_0002
Revises: 20260502_0001
Create Date: 2026-05-05 00:02:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260505_0002"
down_revision = "20260502_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("versions", sa.Column("source_repo_url", sa.String(length=500), nullable=True))
    op.add_column("versions", sa.Column("source_commit", sa.String(length=64), nullable=True))
    op.add_column("versions", sa.Column("release_tag", sa.String(length=100), nullable=True))
    op.add_column("versions", sa.Column("release_url", sa.String(length=500), nullable=True))
    op.add_column("versions", sa.Column("actions_run_url", sa.String(length=500), nullable=True))
    op.add_column("versions", sa.Column("package_url", sa.String(length=500), nullable=True))
    op.add_column("versions", sa.Column("package_sha256", sa.String(length=64), nullable=True))
    op.add_column("versions", sa.Column("payload_hash", sa.String(length=64), nullable=True))
    op.add_column("versions", sa.Column("neko_repo", sa.String(length=200), nullable=True))
    op.add_column("versions", sa.Column("neko_ref", sa.String(length=100), nullable=True))
    op.add_column("versions", sa.Column("neko_commit", sa.String(length=64), nullable=True))
    op.add_column(
        "versions",
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="unverified"),
    )
    op.add_column("versions", sa.Column("verification_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("versions", "verification_summary")
    op.drop_column("versions", "verification_status")
    op.drop_column("versions", "neko_commit")
    op.drop_column("versions", "neko_ref")
    op.drop_column("versions", "neko_repo")
    op.drop_column("versions", "payload_hash")
    op.drop_column("versions", "package_sha256")
    op.drop_column("versions", "package_url")
    op.drop_column("versions", "actions_run_url")
    op.drop_column("versions", "release_url")
    op.drop_column("versions", "release_tag")
    op.drop_column("versions", "source_commit")
    op.drop_column("versions", "source_repo_url")
