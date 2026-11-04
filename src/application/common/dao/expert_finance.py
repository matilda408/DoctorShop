from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable
from uuid import UUID

from src.application.dto import (
    ExpertEarningDto,
    ExpertPlanPriceDto,
    ExpertStatsDto,
    ExpertWithdrawalDto,
    ServiceFinanceSettingsDto,
)
from src.core.enums import Currency, WithdrawalStatus


@runtime_checkable
class ExpertFinanceDao(Protocol):
    async def get_settings(self) -> ServiceFinanceSettingsDto: ...

    async def set_commission(
        self, percent: Decimal, changed_by_telegram_id: int
    ) -> ServiceFinanceSettingsDto: ...

    async def get_prices(self, expert_profile_id: int) -> list[ExpertPlanPriceDto]: ...

    async def set_price(
        self,
        expert_profile_id: int,
        plan_duration_id: int,
        currency: Currency,
        price: Decimal,
        changed_by_telegram_id: int,
    ) -> ExpertPlanPriceDto: ...

    async def record_earning(
        self,
        expert_profile_id: int,
        payment_id: UUID,
        gross_amount: Decimal,
        currency: Currency,
    ) -> ExpertEarningDto: ...

    async def reverse_earning(self, payment_id: UUID) -> Optional[ExpertEarningDto]: ...

    async def get_stats(self, expert_profile_id: int) -> ExpertStatsDto: ...

    async def create_withdrawal(
        self,
        expert_profile_id: int,
        amount: Decimal,
        currency: Currency,
        bank_name: str,
    ) -> ExpertWithdrawalDto: ...

    async def get_withdrawal(self, withdrawal_id: int) -> Optional[ExpertWithdrawalDto]: ...

    async def get_pending_withdrawals(self) -> list[ExpertWithdrawalDto]: ...

    async def process_withdrawal(
        self,
        withdrawal_id: int,
        status: WithdrawalStatus,
        processed_by_telegram_id: int,
        rejection_reason: Optional[str] = None,
    ) -> ExpertWithdrawalDto: ...
