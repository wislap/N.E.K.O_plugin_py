"""user plugin installs

Revision ID: 20260521_0001
Revises: 20260516_0001
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa


revision = '20260521_0001'
down_revision = '20260516_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_plugin_installs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plugin_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('channel', sa.String(length=16), nullable=True),
        sa.Column('package_sha256', sa.String(length=64), nullable=True),
        sa.Column('payload_hash', sa.String(length=128), nullable=True),
        sa.Column('installed_plugin_id', sa.String(length=100), nullable=True),
        sa.Column('client_id', sa.String(length=50), nullable=False),
        sa.Column('installed_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'plugin_id', name='uq_user_plugin_install'),
    )
    op.create_index(op.f('ix_user_plugin_installs_id'), 'user_plugin_installs', ['id'], unique=False)
    op.create_index(op.f('ix_user_plugin_installs_plugin_id'), 'user_plugin_installs', ['plugin_id'], unique=False)
    op.create_index(op.f('ix_user_plugin_installs_user_id'), 'user_plugin_installs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_plugin_installs_user_id'), table_name='user_plugin_installs')
    op.drop_index(op.f('ix_user_plugin_installs_plugin_id'), table_name='user_plugin_installs')
    op.drop_index(op.f('ix_user_plugin_installs_id'), table_name='user_plugin_installs')
    op.drop_table('user_plugin_installs')
