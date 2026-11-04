from typing import Sequence, Union

from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep gateway rows and all old transactions readable, but make the
    # legacy cryptocurrency gateways unavailable for new payments.
    op.execute(
        """
        UPDATE payment_gateways
        SET is_active = FALSE
        WHERE type IN ('CRYPTOMUS', 'HELEKET', 'CRYPTOPAY')
          AND is_active = TRUE
        """
    )
    op.execute(
        """
        UPDATE settings
        SET default_currency = 'RUB'
        WHERE default_currency = 'USD'
        """
    )


def downgrade() -> None:
    # Previous activation state cannot be reconstructed safely. Historical
    # rows remain untouched, so the downgrade intentionally performs no writes.
    pass
