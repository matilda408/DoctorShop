from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column(
        "users", sa.Column("registration_completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_users_phone", "users", ["phone"])
    # Existing accounts keep their access and do not have to repeat onboarding.
    # New accounts created after this migration receive NULL until they provide FIO and phone.
    op.execute(
        "UPDATE users SET registration_completed_at = timezone('UTC', now()) "
        "WHERE registration_completed_at IS NULL"
    )

    # Create the PostgreSQL type explicitly once.  A regular ``sa.Enum`` also
    # installs a CREATE TYPE hook on the table, so the explicit ``create``
    # below used to be followed by a second CREATE TYPE from create_table().
    withdrawal_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="withdrawal_status",
        create_type=False,
    )
    withdrawal_status.create(op.get_bind(), checkfirst=True)
    currency = postgresql.ENUM(name="currency", create_type=False)

    op.create_table(
        "expert_plan_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("plan_duration_id", sa.Integer(), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_duration_id"], ["plan_durations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expert_profile_id", "plan_duration_id", "currency"),
    )
    op.create_index(
        "ix_expert_plan_prices_expert_profile_id", "expert_plan_prices", ["expert_profile_id"]
    )
    op.create_index(
        "ix_expert_plan_prices_plan_duration_id", "expert_plan_prices", ["plan_duration_id"]
    )
    op.create_index("ix_expert_plan_prices_currency", "expert_plan_prices", ["currency"])

    op.create_table(
        "expert_price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("plan_duration_id", sa.Integer(), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("old_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("changed_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_duration_id"], ["plan_durations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_expert_price_history_expert_profile_id", "expert_price_history", ["expert_profile_id"]
    )
    op.create_index(
        "ix_expert_price_history_plan_duration_id", "expert_price_history", ["plan_duration_id"]
    )

    op.create_table(
        "service_finance_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("commission_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("updated_by_telegram_id", sa.BigInteger(), nullable=True),
        *timestamp_columns(),
    )
    op.execute("INSERT INTO service_finance_settings (id, commission_percent) VALUES (1, 20.00)")
    op.create_table(
        "service_commission_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("old_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("new_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("changed_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
    )

    op.create_table(
        "expert_earnings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("transaction_payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["transaction_payment_id"], ["transactions.payment_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("transaction_payment_id"),
    )
    op.create_index(
        "ix_expert_earnings_expert_profile_id", "expert_earnings", ["expert_profile_id"]
    )
    op.create_index(
        "ix_expert_earnings_transaction_payment_id", "expert_earnings", ["transaction_payment_id"]
    )
    op.create_index("ix_expert_earnings_currency", "expert_earnings", ["currency"])

    op.create_table(
        "expert_withdrawals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("bank_name", sa.String(128), nullable=False),
        sa.Column("status", withdrawal_status, nullable=False),
        sa.Column("processed_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(512), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_expert_withdrawals_expert_profile_id", "expert_withdrawals", ["expert_profile_id"]
    )
    op.create_index("ix_expert_withdrawals_currency", "expert_withdrawals", ["currency"])
    op.create_index("ix_expert_withdrawals_status", "expert_withdrawals", ["status"])


def downgrade() -> None:
    op.drop_table("expert_withdrawals")
    op.drop_table("expert_earnings")
    op.drop_table("service_commission_history")
    op.drop_table("service_finance_settings")
    op.drop_table("expert_price_history")
    op.drop_table("expert_plan_prices")
    postgresql.ENUM(name="withdrawal_status", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "registration_completed_at")
    op.drop_column("users", "phone")
