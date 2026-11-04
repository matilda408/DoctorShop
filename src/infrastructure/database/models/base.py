from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ARRAY, DateTime, Enum, Integer
from sqlalchemy import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, registry

from src.core.enums import (
    BroadcastAudience,
    BroadcastMessageStatus,
    BroadcastStatus,
    ConsultationStatus,
    Currency,
    ExpertProfileStatus,
    Locale,
    PaymentGatewayType,
    PlanAvailability,
    PurchaseType,
    ReferralAccrualStrategy,
    ReferralLevel,
    ReferralRewardStrategy,
    ReferralRewardType,
    Role,
    SubscriptionStatus,
    TransactionStatus,
    WithdrawalStatus,
)

mapper_registry = registry(
    type_annotation_map={
        int: Integer,
        dict[str, Any]: JSONB,
        UUID: PG_UUID,
        list[UUID]: ARRAY(PG_UUID),
        datetime: DateTime(timezone=True),
        #
        Locale: Enum(Locale, name="locale"),
        Role: Enum(Role, name="user_role"),
        Currency: Enum(Currency, name="currency"),
        PaymentGatewayType: Enum(PaymentGatewayType, name="payment_gateway_type"),
        PurchaseType: Enum(PurchaseType, name="purchase_type"),
        TransactionStatus: Enum(TransactionStatus, name="transaction_status"),
        SubscriptionStatus: Enum(SubscriptionStatus, name="subscription_status"),
        ExpertProfileStatus: Enum(ExpertProfileStatus, name="expert_profile_status"),
        ConsultationStatus: Enum(ConsultationStatus, name="consultation_status"),
        WithdrawalStatus: Enum(WithdrawalStatus, name="withdrawal_status"),
        PlanAvailability: Enum(PlanAvailability, name="plan_availability"),
        BroadcastStatus: Enum(BroadcastStatus, name="broadcast_status"),
        BroadcastAudience: Enum(BroadcastAudience, name="broadcast_audience"),
        BroadcastMessageStatus: Enum(BroadcastMessageStatus, name="broadcast_message_status"),
        ReferralAccrualStrategy: Enum(ReferralAccrualStrategy, name="referral_accrual_strategy"),
        ReferralLevel: Enum(ReferralLevel, name="referral_level"),
        ReferralRewardStrategy: Enum(ReferralRewardStrategy, name="referral_reward_strategy"),
        ReferralRewardType: Enum(ReferralRewardType, name="referral_reward_type"),
    }
)


class BaseSql(DeclarativeBase):
    registry = mapper_registry
