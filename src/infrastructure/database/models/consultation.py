from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.enums import (
    ConsultationStatus,
    Currency,
    ExpertProfileStatus,
    SubscriptionStatus,
    WithdrawalStatus,
)

from .base import BaseSql
from .timestamp import TimestampMixin


class ExpertProfile(BaseSql, TimestampMixin):
    __tablename__ = "expert_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(128))
    specialization: Mapped[str] = mapped_column(String(128), index=True)
    short_description: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    experience_years: Mapped[int] = mapped_column(default=0)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(512))
    status: Mapped[ExpertProfileStatus] = mapped_column(index=True)


class ExpertPlan(BaseSql):
    __tablename__ = "expert_plans"
    __table_args__ = (UniqueConstraint("expert_profile_id", "plan_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"),
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True)


class ExpertPlanPrice(BaseSql, TimestampMixin):
    __tablename__ = "expert_plan_prices"
    __table_args__ = (UniqueConstraint("expert_profile_id", "plan_duration_id", "currency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="CASCADE"), index=True
    )
    plan_duration_id: Mapped[int] = mapped_column(
        ForeignKey("plan_durations.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[Currency] = mapped_column(index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class ExpertPriceHistory(BaseSql):
    __tablename__ = "expert_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="CASCADE"), index=True
    )
    plan_duration_id: Mapped[int] = mapped_column(
        ForeignKey("plan_durations.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[Currency]
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    new_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    changed_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime]


class ServiceFinanceSettings(BaseSql, TimestampMixin):
    __tablename__ = "service_finance_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    updated_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger)


class ServiceCommissionHistory(BaseSql):
    __tablename__ = "service_commission_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    old_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    new_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    changed_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime]


class ExpertEarning(BaseSql):
    __tablename__ = "expert_earnings"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="RESTRICT"), index=True
    )
    transaction_payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.payment_id", ondelete="RESTRICT"), unique=True, index=True
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[Currency] = mapped_column(index=True)
    created_at: Mapped[datetime]
    reversed_at: Mapped[Optional[datetime]]


class ExpertWithdrawal(BaseSql, TimestampMixin):
    __tablename__ = "expert_withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[Currency] = mapped_column(index=True)
    bank_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[WithdrawalStatus] = mapped_column(index=True)
    processed_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    processed_at: Mapped[Optional[datetime]]
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(512))


class Consultation(BaseSql, TimestampMixin):
    __tablename__ = "consultations"
    __table_args__ = (UniqueConstraint("client_telegram_id", "expert_profile_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
    )
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="RESTRICT"),
        index=True,
    )
    client_thread_id: Mapped[Optional[int]]
    expert_thread_id: Mapped[Optional[int]]
    status: Mapped[ConsultationStatus] = mapped_column(index=True)
    access_expires_at: Mapped[datetime] = mapped_column(index=True)
    last_message_at: Mapped[Optional[datetime]]
    creation_error: Mapped[Optional[str]] = mapped_column(Text)


class ExpertSubscription(BaseSql, TimestampMixin):
    __tablename__ = "expert_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
    )
    expert_profile_id: Mapped[int] = mapped_column(
        ForeignKey("expert_profiles.id", ondelete="RESTRICT"),
        index=True,
    )
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("consultations.id", ondelete="RESTRICT"),
        index=True,
    )
    transaction_payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.payment_id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(index=True)
    starts_at: Mapped[datetime]
    expires_at: Mapped[datetime] = mapped_column(index=True)
    plan_snapshot: Mapped[dict[str, Any]]
