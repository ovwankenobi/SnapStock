"""profitability and sale status

Adds what profit analytics and sale corrections need:

- `products.cost_cents` (unit cost) and the append-only `product_cost_history` log.
- `sale_items.list_price_cents_snapshot` (the product price at sale time; the
  existing `unit_price_cents_snapshot` is what was actually charged, which a
  seller may edit during checkout) plus `unit_cost_cents_snapshot` and
  `cost_total_cents`, so historical COGS never changes when a cost is edited.
- `sales.subtotal_cents` / `discount_cents` (total = subtotal - discount) and
  `sales.status` (completed / voided / refunded) with when and why it changed.
- `void` and `refund` stock movement reasons, for the stock a void or refund returns.

Revision ID: e5a9c3f1b7d2
Revises: d4f8b2a6c1e3
Create Date: 2026-10-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5a9c3f1b7d2'
down_revision: Union[str, Sequence[str], None] = 'd4f8b2a6c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ADD VALUE cannot run inside a transaction block on older Postgres versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE stock_movement_reason ADD VALUE IF NOT EXISTS 'VOID'")
        op.execute("ALTER TYPE stock_movement_reason ADD VALUE IF NOT EXISTS 'REFUND'")

    op.add_column('products', sa.Column('cost_cents', sa.Integer(), nullable=True))

    cost_source = postgresql.ENUM('MANUAL', 'RESTOCK', name='cost_source')
    cost_source.create(op.get_bind())
    op.create_table(
        'product_cost_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('cost_cents', sa.Integer(), nullable=False),
        sa.Column(
            'source', postgresql.ENUM('MANUAL', 'RESTOCK', name='cost_source', create_type=False), nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_product_cost_history_product_id'), 'product_cost_history', ['product_id'], unique=False
    )

    op.add_column('sale_items', sa.Column('list_price_cents_snapshot', sa.Integer(), nullable=True))
    op.execute("UPDATE sale_items SET list_price_cents_snapshot = unit_price_cents_snapshot")
    op.alter_column('sale_items', 'list_price_cents_snapshot', nullable=False)
    op.add_column('sale_items', sa.Column('unit_cost_cents_snapshot', sa.Integer(), nullable=True))
    op.add_column('sale_items', sa.Column('cost_total_cents', sa.Integer(), nullable=True))

    sale_status = postgresql.ENUM('COMPLETED', 'VOIDED', 'REFUNDED', name='sale_status')
    sale_status.create(op.get_bind())
    op.add_column('sales', sa.Column('subtotal_cents', sa.Integer(), nullable=True))
    op.execute("UPDATE sales SET subtotal_cents = total_cents")
    op.alter_column('sales', 'subtotal_cents', nullable=False)
    op.add_column('sales', sa.Column('discount_cents', sa.Integer(), server_default='0', nullable=False))
    op.add_column(
        'sales',
        sa.Column(
            'status',
            postgresql.ENUM('COMPLETED', 'VOIDED', 'REFUNDED', name='sale_status', create_type=False),
            server_default='COMPLETED',
            nullable=False,
        ),
    )
    op.add_column('sales', sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sales', sa.Column('status_reason', sa.Text(), nullable=True))
    op.create_index(op.f('ix_sales_status'), 'sales', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema.

    Postgres cannot drop enum values, so the VOID / REFUND stock movement reasons
    stay on the type (unused by older code paths).
    """
    op.drop_index(op.f('ix_sales_status'), table_name='sales')
    op.drop_column('sales', 'status_reason')
    op.drop_column('sales', 'status_changed_at')
    op.drop_column('sales', 'status')
    op.drop_column('sales', 'discount_cents')
    op.drop_column('sales', 'subtotal_cents')
    postgresql.ENUM(name='sale_status').drop(op.get_bind())

    op.drop_column('sale_items', 'cost_total_cents')
    op.drop_column('sale_items', 'unit_cost_cents_snapshot')
    op.drop_column('sale_items', 'list_price_cents_snapshot')

    op.drop_index(op.f('ix_product_cost_history_product_id'), table_name='product_cost_history')
    op.drop_table('product_cost_history')
    postgresql.ENUM(name='cost_source').drop(op.get_bind())

    op.drop_column('products', 'cost_cents')
