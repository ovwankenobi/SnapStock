"""order card messages

`messages.sale_id` links the chat card posted when a buyer's online order is
ready for the seller to approve ("<buyer> bought this — approve?").

Revision ID: a7c3e9f5b1d4
Revises: f6b2d8e4a9c1
Create Date: 2026-10-18 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7c3e9f5b1d4'
down_revision: Union[str, Sequence[str], None] = 'f6b2d8e4a9c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('sale_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_messages_sale_id_sales', 'messages', 'sales', ['sale_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_messages_sale_id_sales', 'messages', type_='foreignkey')
    op.drop_column('messages', 'sale_id')
