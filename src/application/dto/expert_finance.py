from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.core.enums import Currency, WithdrawalStatus

from .base import BaseDto, TimestampMixin, TrackableMixin


@dataclass(kw_only=True)
class ExpertPlanPriceDto(BaseDto, TrackableMixin, TimestampMixin):
    expert_profile_id: int
    plan_duration_id: int
    currency: Currency
    price: Decimal


@dataclass(kw_only=True)
class ServiceFinanceSettingsDto(BaseDto, TrackableMixin, TimestampMixin):
    commission_percent: Decimal = Decimal("20.00")
    updated_by_telegram_id: Optional[int] = None


@dataclass(kw_only=True)
class ExpertEarningDto(BaseDto):
    expert_profile_id: int
    transaction_payment_id: UUID
    gross_amount: Decimal
    commission_percent: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    currency: Currency
    created_at: datetime
    reversed_at: Optional[datetime] = None


@dataclass(kw_only=True)
class ExpertWithdrawalDto(BaseDto, TrackableMixin, TimestampMixin):
    expert_profile_id: int
    amount: Decimal
    currency: Currency
    bank_name: str
    status: WithdrawalStatus = WithdrawalStatus.PENDING
    processed_by_telegram_id: Optional[int] = None
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


@dataclass(kw_only=True)
class ExpertCurrencyStatsDto:
    currency: Currency
    gross: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    earned: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")
    withdrawn: Decimal = Decimal("0")

    @property
    def available(self) -> Decimal:
        return self.earned - self.reserved - self.withdrawn


@dataclass(kw_only=True)
class ExpertStatsDto:
    clients_count: int
    consultations_count: int
    active_consultations_count: int
    finances: list[ExpertCurrencyStatsDto] = field(default_factory=list)
