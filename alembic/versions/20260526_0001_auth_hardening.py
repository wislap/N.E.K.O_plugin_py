"""auth hardening sessions and throttling

Revision ID: 20260526_0001
Revises: 20260521_0001
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa


revision = '20260526_0001'
down_revision = '20260521_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'refresh_token_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('replaced_by_jti', sa.String(length=64), nullable=True),
        sa.Column('client_id', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_token_sessions_id'), 'refresh_token_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_token_sessions_jti'), 'refresh_token_sessions', ['jti'], unique=True)
    op.create_index(op.f('ix_refresh_token_sessions_token_hash'), 'refresh_token_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_token_sessions_user_id'), 'refresh_token_sessions', ['user_id'], unique=False)

    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column('first_failed_at', sa.DateTime(), nullable=True),
        sa.Column('last_failed_at', sa.DateTime(), nullable=True),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_attempts_id'), 'login_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_login_attempts_identifier'), 'login_attempts', ['identifier'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_login_attempts_identifier'), table_name='login_attempts')
    op.drop_index(op.f('ix_login_attempts_id'), table_name='login_attempts')
    op.drop_table('login_attempts')
    op.drop_index(op.f('ix_refresh_token_sessions_user_id'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_token_hash'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_jti'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_id'), table_name='refresh_token_sessions')
    op.drop_table('refresh_token_sessions')
