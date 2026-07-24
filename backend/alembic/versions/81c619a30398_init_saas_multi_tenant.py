"""init_saas_multi_tenant

Revision ID: 81c619a30398
Revises: 
Create Date: 2026-07-24 10:45:33.735036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '81c619a30398'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- (a) Create new tables ----

    op.create_table('agencies',
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('contact_name', sa.String(length=32), nullable=False),
    sa.Column('contact_phone', sa.String(length=20), nullable=False),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # ---- (b) Insert root agency ----
    op.execute(
        "INSERT INTO agencies (id, name, contact_name, contact_phone, status, created_at, updated_at, deleted_at) "
        "VALUES (1, 'Root Agency', '', '', 1, datetime('now'), datetime('now'), NULL)"
    )

    op.create_table('agency_payment_channels',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('org_no', sa.String(length=64), nullable=False),
    sa.Column('api_key_cipher', sa.String(length=512), nullable=True),
    sa.Column('api_secret_cipher', sa.String(length=512), nullable=True),
    sa.Column('key_version', sa.Integer(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agency_id', 'provider', 'org_no')
    )
    op.create_table('merchants',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('business_type', sa.String(length=32), nullable=False),
    sa.Column('is_micro', sa.Boolean(), nullable=True),
    sa.Column('auto_swipe_enabled', sa.Boolean(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('merchant_onboarding_applications',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('merchant_id', sa.BigInteger(), nullable=True),
    sa.Column('agency_payment_channel_id', sa.BigInteger(), nullable=True),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('provider_application_id', sa.String(length=128), nullable=True),
    sa.Column('external_merchant_no', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('is_simulated', sa.Boolean(), nullable=True),
    sa.Column('request_snapshot', sa.Text(), nullable=True),
    sa.Column('response_snapshot', sa.Text(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('rejected_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agency_payment_channel_id'], ['agency_payment_channels.id'], ),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('onboarding_invites',
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('verified_at', sa.DateTime(), nullable=True),
    sa.Column('consumed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.ForeignKeyConstraint(['channel_id'], ['agency_payment_channels.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('onboarding_sessions',
    sa.Column('invite_id', sa.BigInteger(), nullable=False),
    sa.Column('agency_id', sa.BigInteger(), nullable=False),
    sa.Column('session_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['invite_id'], ['onboarding_invites.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_hash')
    )

    # ---- Existing tables not yet in DB (models added after bootstrap ran) ----
    op.create_table('manual_settlements',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('agency_id', sa.BigInteger(), nullable=True),
    sa.Column('period_type', sa.String(length=8), nullable=False),
    sa.Column('period_date', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('manual_settlements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_manual_settlements_period_date'), ['period_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_manual_settlements_user_id'), ['user_id'], unique=False)

    op.create_table('merchant_profiles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('agency_id', sa.BigInteger(), nullable=True),
    sa.Column('available_cash', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('available_cash_updated_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('merchant_profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_merchant_profiles_user_id'), ['user_id'], unique=True)

    # ---- (c) Add columns to existing users table ----
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('auth_method', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('mfa_enabled', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.Integer(), nullable=True))

    # ---- (d) Add agency_id to existing business tables ----
    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))

    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))

    with op.batch_alter_table('email_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))

    with op.batch_alter_table('settlements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))

    with op.batch_alter_table('sftp_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agency_id', sa.BigInteger(), nullable=True))

    # ---- (e) Backfill: set agency_id=1 on all existing rows ----
    backfill_tables = [
        'users', 'cards', 'merchant_profiles', 'manual_settlements',
        'data_sources', 'settlements', 'email_configs', 'sftp_configs',
    ]
    for tbl in backfill_tables:
        op.execute(f"UPDATE {tbl} SET agency_id = 1 WHERE agency_id IS NULL")

    # ---- (g) Create composite indexes ----
    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cards_agency_id'), ['agency_id'], unique=False)

    with op.batch_alter_table('merchants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_merchants_agency_id_user_id'), ['agency_id', 'user_id'], unique=False)

    with op.batch_alter_table('merchant_onboarding_applications', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_merchant_onboarding_applications_agency_id_status'),
            ['agency_id', 'status'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_merchant_onboarding_applications_apc_id_pai'),
            ['agency_payment_channel_id', 'provider_application_id'], unique=False
        )


def downgrade() -> None:
    # Drop indexes first
    with op.batch_alter_table('merchant_onboarding_applications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_merchant_onboarding_applications_apc_id_pai'))
        batch_op.drop_index(batch_op.f('ix_merchant_onboarding_applications_agency_id_status'))

    with op.batch_alter_table('merchants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_merchants_agency_id_user_id'))

    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cards_agency_id'))

    # Drop new columns from existing tables
    with op.batch_alter_table('sftp_configs', schema=None) as batch_op:
        batch_op.drop_column('agency_id')

    with op.batch_alter_table('settlements', schema=None) as batch_op:
        batch_op.drop_column('agency_id')

    with op.batch_alter_table('email_configs', schema=None) as batch_op:
        batch_op.drop_column('agency_id')

    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.drop_column('agency_id')

    with op.batch_alter_table('cards', schema=None) as batch_op:
        batch_op.drop_column('agency_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('mfa_enabled')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('auth_method')
        batch_op.drop_column('role')
        batch_op.drop_column('agency_id')

    # Drop tables that were newly created (reverse of creation order)
    with op.batch_alter_table('merchant_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_merchant_profiles_user_id'))
    op.drop_table('merchant_profiles')

    with op.batch_alter_table('manual_settlements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_manual_settlements_user_id'))
        batch_op.drop_index(batch_op.f('ix_manual_settlements_period_date'))
    op.drop_table('manual_settlements')

    op.drop_table('onboarding_sessions')
    op.drop_table('onboarding_invites')
    op.drop_table('merchant_onboarding_applications')
    op.drop_table('merchants')
    op.drop_table('agency_payment_channels')
    op.drop_table('agencies')
