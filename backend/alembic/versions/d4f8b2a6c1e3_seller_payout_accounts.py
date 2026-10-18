"""seller payout accounts

Adds `seller_payout_accounts`, which stores where a seller receives non-cash
payments: GCash, Maya, bank or other e-wallet. Each row has an account name,
an account number, an optional QR image and a default flag. `method` reuses the
existing `payment_method` enum, so it is not created here.

Revision ID: d4f8b2a6c1e3
Revises: c3e1a7d9f2b4
Create Date: 2026-10-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4f8b2a6c1e3'
down_revision: Union[str, Sequence[str], None] = 'c3e1a7d9f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    payment_method = postgresql.ENUM(
        'CASH', 'GCASH', 'MAYA', 'BANK_TRANSFER', 'OTHER', name='payment_method', create_type=False
    )
    op.create_table(
        'seller_payout_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('seller_profile_id', sa.UUID(), nullable=False),
        sa.Column('method', payment_method, nullable=False),
        sa.Column('account_name', sa.String(), nullable=False),
        sa.Column('account_number', sa.String(), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=True),
        sa.Column('qr_url', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['seller_profile_id'], ['seller_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_seller_payout_accounts_seller_profile_id'),
        'seller_payout_accounts',
        ['seller_profile_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_seller_payout_accounts_seller_profile_id'), table_name='seller_payout_accounts')
    op.drop_table('seller_payout_accounts')
