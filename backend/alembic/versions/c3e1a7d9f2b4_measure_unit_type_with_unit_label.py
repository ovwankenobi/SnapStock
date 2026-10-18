"""measure unit type with unit label

Replaces the weight-only GRAMS unit type with a generic MEASURE type whose unit
(kg, yd, m, ...) is configured per product via `unit_label`. Quantities, stock and
thresholds for measure products are stored in thousandths of the unit, which is
exactly what existing grams data already is for kg — so only prices change
(per gram -> per kg).

Revision ID: c3e1a7d9f2b4
Revises: bfad0a553622
Create Date: 2026-10-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e1a7d9f2b4'
down_revision: Union[str, Sequence[str], None] = 'bfad0a553622'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE unit_type RENAME VALUE 'GRAMS' TO 'MEASURE'")
    op.add_column('products', sa.Column('unit_label', sa.String(length=16), nullable=True))
    op.add_column('sale_items', sa.Column('unit_label_snapshot', sa.String(length=16), nullable=True))

    op.execute(
        "UPDATE products SET unit_label = 'kg', price_cents = price_cents * 1000 "
        "WHERE unit_type = 'MEASURE'"
    )
    # line_total_cents is unchanged: grams x (cents/kg) / 1000 == grams x (cents/g).
    op.execute(
        "UPDATE sale_items SET unit_label_snapshot = 'kg', "
        "unit_price_cents_snapshot = unit_price_cents_snapshot * 1000 "
        "WHERE unit_type_snapshot = 'MEASURE'"
    )


def downgrade() -> None:
    """Downgrade schema.

    Non-kg measure products cannot be represented as grams; they are converted
    with the same per-1000 scale, which is only exact for kg.
    """
    op.execute(
        "UPDATE sale_items SET unit_price_cents_snapshot = ROUND(unit_price_cents_snapshot / 1000.0) "
        "WHERE unit_type_snapshot = 'MEASURE'"
    )
    op.execute(
        "UPDATE products SET price_cents = GREATEST(1, ROUND(price_cents / 1000.0)) "
        "WHERE unit_type = 'MEASURE'"
    )
    op.drop_column('sale_items', 'unit_label_snapshot')
    op.drop_column('products', 'unit_label')
    op.execute("ALTER TYPE unit_type RENAME VALUE 'MEASURE' TO 'GRAMS'")
