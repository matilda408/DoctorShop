from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expert_earnings",
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_expert_earnings_reversed_at",
        "expert_earnings",
        ["reversed_at"],
    )

    # Preserve the stored commission snapshot. Only exclude earnings whose
    # source payment is already known to be unsuccessful or reversed.
    op.execute(
        """
        UPDATE expert_earnings AS earning
        SET reversed_at = COALESCE(payment.updated_at, earning.created_at)
        FROM transactions AS payment
        WHERE payment.payment_id = earning.transaction_payment_id
          AND payment.status IN ('CANCELED', 'REFUNDED', 'FAILED')
          AND earning.reversed_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_expert_earnings_reversed_at", table_name="expert_earnings")
    op.drop_column("expert_earnings", "reversed_at")
