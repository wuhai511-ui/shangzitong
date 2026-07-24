"""add_auto_swipe_tables

Revision ID: 48985a71b068
Revises: 81c619a30398
Create Date: 2026-07-24 11:32:21.528239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '48985a71b068'
down_revision: Union[str, None] = '81c619a30398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('auto_swipe_policies',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('max_daily_per_merchant', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('max_single_amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('min_interest_free_days', sa.Integer(), server_default='0', nullable=True),
    sa.Column('max_parallel_transactions', sa.Integer(), server_default='3', nullable=True),
    sa.Column('retry_strategy', sa.Text(), nullable=True),
    sa.Column('swipe_window_start', sa.Time(), nullable=True),
    sa.Column('swipe_window_end', sa.Time(), nullable=True),
    sa.Column('notification_webhook', sa.String(length=256), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='0', nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agency_id')
    )
    op.create_table('transactions',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('merchant_id', sa.BigInteger(), nullable=False),
    sa.Column('merchant_no', sa.String(length=64), nullable=False),
    sa.Column('card_id', sa.BigInteger(), nullable=True),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
    sa.Column('scheduled_at', sa.DateTime(), nullable=True),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.Column('provider_txn_id', sa.String(length=128), nullable=True),
    sa.Column('retry_count', sa.Integer(), server_default='0', nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('result_snapshot', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['card_id'], ['cards.id'], ),
    sa.ForeignKeyConstraint(['channel_id'], ['agency_payment_channels.id'], ),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_transactions_agency_id'), ['agency_id'], unique=False)
        batch_op.create_index('ix_transactions_agency_merchant_status_scheduled', ['agency_id', 'merchant_id', 'status', 'scheduled_at'], unique=False)
        batch_op.create_index('ix_transactions_status_scheduled', ['status', 'scheduled_at'], unique=False)

    op.create_table('auto_swipe_execution_logs',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('event_type', sa.String(length=32), nullable=False),
    sa.Column('event_data', sa.Text(), nullable=True),
    sa.Column('severity', sa.String(length=10), server_default='info', nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('auto_swipe_execution_logs')
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index('ix_transactions_status_scheduled')
        batch_op.drop_index('ix_transactions_agency_merchant_status_scheduled')
        batch_op.drop_index(batch_op.f('ix_transactions_agency_id'))
    op.drop_table('transactions')
    op.drop_table('auto_swipe_policies')
