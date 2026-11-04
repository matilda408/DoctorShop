from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove VPN-only configuration while preserving all business records."""
    for column_name in (
        "traffic_limit_strategy",
        "traffic_limit",
        "device_limit",
        "internal_squads",
        "external_squad",
    ):
        op.drop_column("subscriptions", column_name)

    for column_name in (
        "type",
        "traffic_limit_strategy",
        "traffic_limit",
        "device_limit",
        "internal_squads",
        "external_squad",
    ):
        op.drop_column("plans", column_name)


def downgrade() -> None:
    plan_type = postgresql.ENUM(name="plan_type", create_type=False)
    strategy = postgresql.ENUM(name="plan_traffic_limit_strategy", create_type=False)

    op.add_column(
        "plans",
        sa.Column("type", plan_type, nullable=False, server_default="UNLIMITED"),
    )
    op.add_column(
        "plans",
        sa.Column("traffic_limit_strategy", strategy, nullable=False, server_default="NO_RESET"),
    )
    op.add_column(
        "plans", sa.Column("traffic_limit", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "plans", sa.Column("device_limit", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "plans",
        sa.Column(
            "internal_squads",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "plans",
        sa.Column("external_squad", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.add_column(
        "subscriptions",
        sa.Column("traffic_limit_strategy", strategy, nullable=False, server_default="NO_RESET"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("traffic_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("device_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "internal_squads",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("external_squad", postgresql.UUID(as_uuid=True), nullable=True),
    )
