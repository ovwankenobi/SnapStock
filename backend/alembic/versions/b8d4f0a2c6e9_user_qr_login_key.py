"""user qr login key

`users.qr_login_key_hash` / `qr_login_created_at` for the login QR a user makes on
their Profile page. Only a SHA-256 of the key is stored.

Revision ID: b8d4f0a2c6e9
Revises: a7c3e9f5b1d4
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d4f0a2c6e9'
down_revision: Union[str, Sequence[str], None] = 'a7c3e9f5b1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('qr_login_key_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('qr_login_created_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_qr_login_key_hash'), 'users', ['qr_login_key_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_qr_login_key_hash'), table_name='users')
    op.drop_column('users', 'qr_login_created_at')
    op.drop_column('users', 'qr_login_key_hash')
