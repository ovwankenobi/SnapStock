"""buyer order payment confirmation

Buyer orders now wait for the seller to confirm payment before they count:

- `pending_payment` and `cancelled` sale statuses. A pending order reserves its
  stock; a cancelled one (rejected by the seller or cancelled by the buyer) has
  returned it. Neither counts in any metric.
- `sales.payment_proof_url` / `proof_submitted_at` for the buyer's payment screenshot.
- `cancel` stock movement reason, for the stock a cancelled order returns.

Revision ID: f6b2d8e4a9c1
Revises: e5a9c3f1b7d2
Create Date: 2026-10-18 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6b2d8e4a9c1'
down_revision: Union[str, Sequence[str], None] = 'e5a9c3f1b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADD VALUE cannot run inside a transaction block on older Postgres versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE sale_status ADD VALUE IF NOT EXISTS 'PENDING_PAYMENT'")
        op.execute("ALTER TYPE sale_status ADD VALUE IF NOT EXISTS 'CANCELLED'")
        op.execute("ALTER TYPE stock_movement_reason ADD VALUE IF NOT EXISTS 'CANCEL'")

    op.add_column('sales', sa.Column('payment_proof_url', sa.String(), nullable=True))
    op.add_column('sales', sa.Column('proof_submitted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema.

    Postgres cannot drop enum values, so PENDING_PAYMENT / CANCELLED and the CANCEL
    stock movement reason stay on their types (unused by older code paths).
    """
    op.drop_column('sales', 'proof_submitted_at')
    op.drop_column('sales', 'payment_proof_url')
