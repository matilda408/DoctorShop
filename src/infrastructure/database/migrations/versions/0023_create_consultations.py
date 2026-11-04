from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'EXPERT'")
    op.add_column(
        "users",
        sa.Column("consultation_bonus_days", sa.Integer(), nullable=False, server_default="0"),
    )

    expert_status = sa.Enum(
        "DRAFT",
        "MODERATION",
        "ACTIVE",
        "HIDDEN",
        "DISABLED",
        name="expert_profile_status",
    )
    consultation_status = sa.Enum(
        "CREATING",
        "ACTIVE",
        "EXPIRED",
        "CLOSED",
        "ERROR",
        name="consultation_status",
    )
    op.create_table(
        "expert_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("specialization", sa.String(128), nullable=False),
        sa.Column("short_description", sa.String(512), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_file_id", sa.String(512), nullable=True),
        sa.Column("status", expert_status, nullable=False),
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
        sa.ForeignKeyConstraint(["user_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_telegram_id"),
    )
    op.create_index("ix_expert_profiles_user_telegram_id", "expert_profiles", ["user_telegram_id"])
    op.create_index("ix_expert_profiles_specialization", "expert_profiles", ["specialization"])
    op.create_index("ix_expert_profiles_status", "expert_profiles", ["status"])

    op.create_table(
        "expert_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expert_profile_id", "plan_id"),
    )
    op.create_index("ix_expert_plans_expert_profile_id", "expert_plans", ["expert_profile_id"])
    op.create_index("ix_expert_plans_plan_id", "expert_plans", ["plan_id"])

    op.create_table(
        "consultations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("client_thread_id", sa.Integer(), nullable=True),
        sa.Column("expert_thread_id", sa.Integer(), nullable=True),
        sa.Column("status", consultation_status, nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creation_error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["client_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("client_telegram_id", "expert_profile_id"),
    )
    op.create_index("ix_consultations_client_telegram_id", "consultations", ["client_telegram_id"])
    op.create_index("ix_consultations_expert_profile_id", "consultations", ["expert_profile_id"])
    op.create_index("ix_consultations_status", "consultations", ["status"])
    op.create_index("ix_consultations_access_expires_at", "consultations", ["access_expires_at"])

    op.add_column("transactions", sa.Column("expert_profile_id", sa.Integer(), nullable=True))
    op.create_index("ix_transactions_expert_profile_id", "transactions", ["expert_profile_id"])
    op.create_foreign_key(
        "fk_transactions_expert_profile_id",
        "transactions",
        "expert_profiles",
        ["expert_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "expert_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("expert_profile_id", sa.Integer(), nullable=False),
        sa.Column("consultation_id", sa.Integer(), nullable=False),
        sa.Column("transaction_payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", postgresql.ENUM(name="subscription_status", create_type=False), nullable=False
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["client_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expert_profile_id"], ["expert_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["transaction_payment_id"], ["transactions.payment_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("transaction_payment_id"),
    )
    for name, column in (
        ("client_telegram_id", "client_telegram_id"),
        ("expert_profile_id", "expert_profile_id"),
        ("consultation_id", "consultation_id"),
        ("transaction_payment_id", "transaction_payment_id"),
        ("status", "status"),
        ("expires_at", "expires_at"),
    ):
        op.create_index(f"ix_expert_subscriptions_{name}", "expert_subscriptions", [column])


def downgrade() -> None:
    op.drop_table("expert_subscriptions")
    op.drop_constraint("fk_transactions_expert_profile_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_expert_profile_id", table_name="transactions")
    op.drop_column("transactions", "expert_profile_id")
    op.drop_table("consultations")
    op.drop_table("expert_plans")
    op.drop_table("expert_profiles")
    postgresql.ENUM(name="consultation_status", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="expert_profile_status", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
    op.drop_column("users", "consultation_bonus_days")
    # PostgreSQL enum values are intentionally not removed from user_role.
