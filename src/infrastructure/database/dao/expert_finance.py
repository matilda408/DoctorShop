from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao import ExpertFinanceDao
from src.application.dto import (
    ExpertCurrencyStatsDto,
    ExpertEarningDto,
    ExpertPlanPriceDto,
    ExpertStatsDto,
    ExpertWithdrawalDto,
    ServiceFinanceSettingsDto,
)
from src.application.services import calculate_expert_earning
from src.core.enums import ConsultationStatus, Currency, TransactionStatus, WithdrawalStatus
from src.core.utils.time import datetime_now
from src.infrastructure.database.models import (
    Consultation,
    ExpertEarning,
    ExpertPlanPrice,
    ExpertPriceHistory,
    ExpertProfile,
    ExpertWithdrawal,
    ServiceCommissionHistory,
    ServiceFinanceSettings,
    Transaction,
)


class ExpertFinanceDaoImpl(ExpertFinanceDao):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _settings_dto(row: ServiceFinanceSettings) -> ServiceFinanceSettingsDto:
        return ServiceFinanceSettingsDto(
            id=row.id,
            commission_percent=row.commission_percent,
            updated_by_telegram_id=row.updated_by_telegram_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _price_dto(row: ExpertPlanPrice) -> ExpertPlanPriceDto:
        return ExpertPlanPriceDto(
            id=row.id,
            expert_profile_id=row.expert_profile_id,
            plan_duration_id=row.plan_duration_id,
            currency=row.currency,
            price=row.price,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _withdrawal_dto(row: ExpertWithdrawal) -> ExpertWithdrawalDto:
        return ExpertWithdrawalDto(
            id=row.id,
            expert_profile_id=row.expert_profile_id,
            amount=row.amount,
            currency=row.currency,
            bank_name=row.bank_name,
            status=row.status,
            processed_by_telegram_id=row.processed_by_telegram_id,
            processed_at=row.processed_at,
            rejection_reason=row.rejection_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_settings(self) -> ServiceFinanceSettingsDto:
        row = await self.session.get(ServiceFinanceSettings, 1)
        if row is None:
            row = ServiceFinanceSettings(id=1, commission_percent=Decimal("20.00"))
            self.session.add(row)
            await self.session.flush()
        return self._settings_dto(row)

    async def set_commission(
        self, percent: Decimal, changed_by_telegram_id: int
    ) -> ServiceFinanceSettingsDto:
        settings = await self.session.get(ServiceFinanceSettings, 1, with_for_update=True)
        if settings is None:
            settings = ServiceFinanceSettings(
                id=1,
                commission_percent=Decimal("20.00"),
                updated_by_telegram_id=changed_by_telegram_id,
            )
            self.session.add(settings)
            await self.session.flush()
        old_percent = settings.commission_percent
        settings.commission_percent = percent
        settings.updated_by_telegram_id = changed_by_telegram_id
        self.session.add(
            ServiceCommissionHistory(
                old_percent=old_percent,
                new_percent=percent,
                changed_by_telegram_id=changed_by_telegram_id,
                created_at=datetime_now(),
            )
        )
        await self.session.flush()
        return self._settings_dto(settings)

    async def get_prices(self, expert_profile_id: int) -> list[ExpertPlanPriceDto]:
        rows = await self.session.scalars(
            select(ExpertPlanPrice).where(ExpertPlanPrice.expert_profile_id == expert_profile_id)
        )
        return [self._price_dto(row) for row in rows.all()]

    async def set_price(
        self,
        expert_profile_id: int,
        plan_duration_id: int,
        currency: Currency,
        price: Decimal,
        changed_by_telegram_id: int,
    ) -> ExpertPlanPriceDto:
        row = await self.session.scalar(
            select(ExpertPlanPrice)
            .where(
                ExpertPlanPrice.expert_profile_id == expert_profile_id,
                ExpertPlanPrice.plan_duration_id == plan_duration_id,
                ExpertPlanPrice.currency == currency,
            )
            .with_for_update()
        )
        old_price = row.price if row else None
        if row is None:
            row = ExpertPlanPrice(
                expert_profile_id=expert_profile_id,
                plan_duration_id=plan_duration_id,
                currency=currency,
                price=price,
            )
            self.session.add(row)
        else:
            row.price = price
        self.session.add(
            ExpertPriceHistory(
                expert_profile_id=expert_profile_id,
                plan_duration_id=plan_duration_id,
                currency=currency,
                old_price=old_price,
                new_price=price,
                changed_by_telegram_id=changed_by_telegram_id,
                created_at=datetime_now(),
            )
        )
        await self.session.flush()
        return self._price_dto(row)

    async def record_earning(
        self,
        expert_profile_id: int,
        payment_id: UUID,
        gross_amount: Decimal,
        currency: Currency,
    ) -> ExpertEarningDto:
        existing = await self.session.scalar(
            select(ExpertEarning).where(ExpertEarning.transaction_payment_id == payment_id)
        )
        if existing:
            return self._earning_dto(existing)

        settings = await self.get_settings()
        amounts = calculate_expert_earning(gross_amount, settings.commission_percent)
        earning = ExpertEarning(
            expert_profile_id=expert_profile_id,
            transaction_payment_id=payment_id,
            gross_amount=amounts.gross,
            commission_percent=amounts.commission_percent,
            commission_amount=amounts.commission,
            net_amount=amounts.net,
            currency=currency,
            created_at=datetime_now(),
        )
        self.session.add(earning)
        await self.session.flush()
        return self._earning_dto(earning)

    async def reverse_earning(self, payment_id: UUID) -> Optional[ExpertEarningDto]:
        earning = await self.session.scalar(
            select(ExpertEarning)
            .where(ExpertEarning.transaction_payment_id == payment_id)
            .with_for_update()
        )
        if earning is None:
            return None
        if earning.reversed_at is None:
            earning.reversed_at = datetime_now()
            await self.session.flush()
        return self._earning_dto(earning)

    @staticmethod
    def _earning_dto(row: ExpertEarning) -> ExpertEarningDto:
        return ExpertEarningDto(
            id=row.id,
            expert_profile_id=row.expert_profile_id,
            transaction_payment_id=row.transaction_payment_id,
            gross_amount=row.gross_amount,
            commission_percent=row.commission_percent,
            commission_amount=row.commission_amount,
            net_amount=row.net_amount,
            currency=row.currency,
            created_at=row.created_at,
            reversed_at=row.reversed_at,
        )

    async def get_stats(self, expert_profile_id: int) -> ExpertStatsDto:
        clients_count = (
            await self.session.scalar(
                select(func.count(distinct(Consultation.client_telegram_id))).where(
                    Consultation.expert_profile_id == expert_profile_id
                )
            )
            or 0
        )
        consultations_count = (
            await self.session.scalar(
                select(func.count(Consultation.id)).where(
                    Consultation.expert_profile_id == expert_profile_id
                )
            )
            or 0
        )
        active_count = (
            await self.session.scalar(
                select(func.count(Consultation.id)).where(
                    Consultation.expert_profile_id == expert_profile_id,
                    Consultation.status == ConsultationStatus.ACTIVE,
                )
            )
            or 0
        )

        earning_rows = (
            await self.session.execute(
                select(
                    ExpertEarning.currency,
                    func.sum(ExpertEarning.gross_amount),
                    func.sum(ExpertEarning.commission_amount),
                    func.sum(ExpertEarning.net_amount),
                )
                .join(
                    Transaction,
                    Transaction.payment_id == ExpertEarning.transaction_payment_id,
                )
                .where(
                    ExpertEarning.expert_profile_id == expert_profile_id,
                    ExpertEarning.reversed_at.is_(None),
                    Transaction.status == TransactionStatus.COMPLETED,
                )
                .group_by(ExpertEarning.currency)
            )
        ).all()
        withdrawal_rows = (
            await self.session.execute(
                select(
                    ExpertWithdrawal.currency,
                    ExpertWithdrawal.status,
                    func.sum(ExpertWithdrawal.amount),
                )
                .where(ExpertWithdrawal.expert_profile_id == expert_profile_id)
                .group_by(ExpertWithdrawal.currency, ExpertWithdrawal.status)
            )
        ).all()

        finances: dict[Currency, ExpertCurrencyStatsDto] = {}
        for currency, gross, commission, net in earning_rows:
            finances[currency] = ExpertCurrencyStatsDto(
                currency=currency,
                gross=gross or Decimal("0"),
                commission=commission or Decimal("0"),
                earned=net or Decimal("0"),
            )
        for currency, status, amount in withdrawal_rows:
            item = finances.setdefault(currency, ExpertCurrencyStatsDto(currency=currency))
            if status == WithdrawalStatus.PENDING:
                item.reserved = amount or Decimal("0")
            elif status == WithdrawalStatus.APPROVED:
                item.withdrawn = amount or Decimal("0")
        return ExpertStatsDto(
            clients_count=int(clients_count),
            consultations_count=int(consultations_count),
            active_consultations_count=int(active_count),
            finances=list(finances.values()),
        )

    async def create_withdrawal(
        self,
        expert_profile_id: int,
        amount: Decimal,
        currency: Currency,
        bank_name: str,
    ) -> ExpertWithdrawalDto:
        profile = await self.session.scalar(
            select(ExpertProfile).where(ExpertProfile.id == expert_profile_id).with_for_update()
        )
        if not profile:
            raise ValueError("Анкета эксперта не найдена")
        stats = await self.get_stats(expert_profile_id)
        currency_stats = next((item for item in stats.finances if item.currency == currency), None)
        available = currency_stats.available if currency_stats else Decimal("0")
        if amount > available:
            raise ValueError(f"Недостаточно средств. Доступно: {available} {currency.symbol}")
        row = ExpertWithdrawal(
            expert_profile_id=expert_profile_id,
            amount=amount,
            currency=currency,
            bank_name=bank_name,
            status=WithdrawalStatus.PENDING,
        )
        self.session.add(row)
        await self.session.flush()
        return self._withdrawal_dto(row)

    async def get_withdrawal(self, withdrawal_id: int) -> Optional[ExpertWithdrawalDto]:
        row = await self.session.get(ExpertWithdrawal, withdrawal_id)
        return self._withdrawal_dto(row) if row else None

    async def get_pending_withdrawals(self) -> list[ExpertWithdrawalDto]:
        rows = await self.session.scalars(
            select(ExpertWithdrawal)
            .where(ExpertWithdrawal.status == WithdrawalStatus.PENDING)
            .order_by(ExpertWithdrawal.created_at)
        )
        return [self._withdrawal_dto(row) for row in rows.all()]

    async def process_withdrawal(
        self,
        withdrawal_id: int,
        status: WithdrawalStatus,
        processed_by_telegram_id: int,
        rejection_reason: Optional[str] = None,
    ) -> ExpertWithdrawalDto:
        row = await self.session.scalar(
            select(ExpertWithdrawal).where(ExpertWithdrawal.id == withdrawal_id).with_for_update()
        )
        if not row:
            raise ValueError("Заявка на вывод не найдена")
        if row.status != WithdrawalStatus.PENDING:
            raise ValueError("Эта заявка уже обработана")
        if status not in {WithdrawalStatus.APPROVED, WithdrawalStatus.REJECTED}:
            raise ValueError("Недопустимый статус заявки")
        row.status = status
        row.processed_by_telegram_id = processed_by_telegram_id
        row.processed_at = datetime_now()
        row.rejection_reason = rejection_reason if status == WithdrawalStatus.REJECTED else None
        await self.session.flush()
        return self._withdrawal_dto(row)
