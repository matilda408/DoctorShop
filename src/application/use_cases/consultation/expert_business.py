from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.application.common import Interactor, Notifier
from src.application.common.dao import ExpertDao, ExpertFinanceDao, UserDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import (
    ExpertEarningDto,
    ExpertPlanPriceDto,
    ExpertProfileDto,
    ExpertStatsDto,
    ExpertWithdrawalDto,
    MediaDescriptorDto,
    MessagePayloadDto,
    ServiceFinanceSettingsDto,
    TransactionDto,
    UserDto,
)
from src.core.enums import Currency, ExpertProfileStatus, MediaType, Role, WithdrawalStatus
from src.core.exceptions import ExpertApplicationAlreadyProcessedError, PermissionDeniedError
from src.core.payment_policy import NEW_PLAN_CURRENCIES


def parse_positive_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Введите корректную сумму") from error
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    return amount


@dataclass(frozen=True)
class SubmitExpertApplicationDto:
    display_name: str
    specialization: str
    description: str
    experience_years: int
    photo_file_id: str


class SubmitExpertApplication(Interactor[SubmitExpertApplicationDto, ExpertProfileDto]):
    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        expert_dao: ExpertDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: SubmitExpertApplicationDto) -> ExpertProfileDto:
        if not actor.is_registration_completed:
            raise ValueError("Сначала завершите регистрацию")
        display_name = " ".join(data.display_name.split())
        specialization = " ".join(data.specialization.split())
        description = data.description.strip()
        if not 3 <= len(display_name) <= 128:
            raise ValueError("Некорректное имя эксперта")
        if not 2 <= len(specialization) <= 128:
            raise ValueError("Некорректная специализация")
        if not 10 <= len(description) <= 2000:
            raise ValueError("Описание должно содержать от 10 до 2000 символов")
        if data.experience_years < 0 or data.experience_years > 80:
            raise ValueError("Стаж должен быть от 0 до 80 лет")
        if not data.photo_file_id:
            raise ValueError("Добавьте фотографию для карточки эксперта")

        async with self.uow:
            profile = await self.expert_dao.get_by_user(actor.telegram_id)
            if profile and profile.status == ExpertProfileStatus.ACTIVE:
                raise ValueError("Ваша анкета эксперта уже активна")
            if profile is None:
                profile = await self.expert_dao.create(
                    ExpertProfileDto(
                        user_telegram_id=actor.telegram_id,
                        display_name=display_name,
                        specialization=specialization,
                        short_description=description[:512],
                        description=description,
                        experience_years=data.experience_years,
                        photo_file_id=data.photo_file_id,
                        status=ExpertProfileStatus.MODERATION,
                    )
                )
            else:
                profile.display_name = display_name
                profile.specialization = specialization
                profile.short_description = description[:512]
                profile.description = description
                profile.experience_years = data.experience_years
                profile.photo_file_id = data.photo_file_id
                profile.status = ExpertProfileStatus.MODERATION
                profile = await self.expert_dao.update(profile)
            await self.uow.commit()

        await self.notifier.notify_admins(
            MessagePayloadDto(
                i18n_key="ntf-expert.application",
                i18n_kwargs={
                    "id": profile.id,
                    "telegram_id": actor.telegram_id,
                    "username": actor.username or 0,
                    "name": profile.display_name,
                    "specialization": profile.specialization,
                    "experience": profile.description,
                },
                media=MediaDescriptorDto(
                    kind="file_id",
                    value=profile.photo_file_id or data.photo_file_id,
                ),
                media_type=MediaType.PHOTO,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Одобрить",
                                callback_data=f"expert_application:approve:{profile.id}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отклонить",
                                callback_data=f"expert_application:reject:{profile.id}",
                            ),
                        ]
                    ]
                ),
                delete_after=None,
            )
        )
        return profile


@dataclass(frozen=True)
class ModerateExpertApplicationDto:
    expert_profile_id: int
    approve: bool
    reason: str | None = None


class ModerateExpertApplication(Interactor[ModerateExpertApplicationDto, ExpertProfileDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(
        self,
        uow: UnitOfWork,
        expert_dao: ExpertDao,
        user_dao: UserDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.user_dao = user_dao
        self.notifier = notifier

    async def _execute(
        self, actor: UserDto, data: ModerateExpertApplicationDto
    ) -> ExpertProfileDto:
        async with self.uow:
            profile = await self.expert_dao.get_by_id_for_update(data.expert_profile_id)
            if not profile:
                raise ValueError("Анкета эксперта не найдена")
            if profile.status != ExpertProfileStatus.MODERATION:
                raise ExpertApplicationAlreadyProcessedError("Заявка уже обработана")
            profile.status = (
                ExpertProfileStatus.ACTIVE if data.approve else ExpertProfileStatus.DISABLED
            )
            profile = await self.expert_dao.update(profile)
            applicant = await self.user_dao.get_by_telegram_id(profile.user_telegram_id)
            if not applicant:
                raise ValueError("Пользователь эксперта не найден")
            if data.approve and applicant.role == Role.USER:
                applicant.role = Role.EXPERT
                await self.user_dao.update(applicant)
            elif not data.approve and applicant.role == Role.EXPERT:
                applicant.role = Role.USER
                await self.user_dao.update(applicant)
            await self.uow.commit()

        await self.notifier.notify_user(
            applicant,
            MessagePayloadDto(
                i18n_key="ntf-expert.application-approved"
                if data.approve
                else "ntf-expert.application-rejected",
                i18n_kwargs={"reason": data.reason or "Причина не указана"},
                delete_after=None,
            ),
        )
        return profile


@dataclass(frozen=True)
class SetExpertPriceDto:
    plan_duration_id: int
    currency: Currency
    price: Decimal


class SetExpertPrice(Interactor[SetExpertPriceDto, ExpertPlanPriceDto]):
    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        expert_dao: ExpertDao,
        finance_dao: ExpertFinanceDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.finance_dao = finance_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: SetExpertPriceDto) -> ExpertPlanPriceDto:
        if data.currency not in NEW_PLAN_CURRENCIES:
            raise ValueError("Эта валюта недоступна для новых тарифов")
        profile = await self.expert_dao.get_by_user(actor.telegram_id)
        if not profile or profile.status != ExpertProfileStatus.ACTIVE:
            raise PermissionDeniedError
        if profile.id is None:
            raise ValueError("Анкета эксперта не сохранена")
        price = data.price.quantize(Decimal("0.01"))
        if price <= 0 or price > Decimal("10000000"):
            raise ValueError("Цена должна быть больше нуля и не выше 10 000 000")
        plans = await self.expert_dao.get_available_plans(profile.id)
        allowed_duration_ids = {
            duration.id for plan in plans for duration in plan.durations if duration.id is not None
        }
        if data.plan_duration_id not in allowed_duration_ids:
            raise ValueError("Этот период не относится к тарифам эксперта")
        async with self.uow:
            result = await self.finance_dao.set_price(
                profile.id,
                data.plan_duration_id,
                data.currency,
                price,
                actor.telegram_id,
            )
            await self.uow.commit()
        await self.notifier.notify_admins(
            MessagePayloadDto(
                i18n_key="ntf-expert.price-changed",
                i18n_kwargs={
                    "expert_id": profile.id,
                    "expert": profile.display_name,
                    "duration_id": data.plan_duration_id,
                    "price": price,
                    "currency": data.currency.value,
                },
                delete_after=None,
            )
        )
        return result


class GetExpertStats(Interactor[None, ExpertStatsDto]):
    required_permission = Permission.PUBLIC

    def __init__(self, expert_dao: ExpertDao, finance_dao: ExpertFinanceDao) -> None:
        self.expert_dao = expert_dao
        self.finance_dao = finance_dao

    async def _execute(self, actor: UserDto, data: None) -> ExpertStatsDto:
        profile = await self.expert_dao.get_by_user(actor.telegram_id)
        if not profile or profile.status != ExpertProfileStatus.ACTIVE:
            raise PermissionDeniedError
        if profile.id is None:
            raise ValueError("Анкета эксперта не сохранена")
        return await self.finance_dao.get_stats(profile.id)


@dataclass(frozen=True)
class SetServiceCommissionDto:
    percent: Decimal


class SetServiceCommission(Interactor[SetServiceCommissionDto, ServiceFinanceSettingsDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(self, uow: UnitOfWork, finance_dao: ExpertFinanceDao) -> None:
        self.uow = uow
        self.finance_dao = finance_dao

    async def _execute(
        self, actor: UserDto, data: SetServiceCommissionDto
    ) -> ServiceFinanceSettingsDto:
        percent = data.percent.quantize(Decimal("0.01"))
        if percent < 0 or percent > 100:
            raise ValueError("Комиссия должна быть от 0 до 100%")
        async with self.uow:
            result = await self.finance_dao.set_commission(percent, actor.telegram_id)
            await self.uow.commit()
        return result


@dataclass(frozen=True)
class RecordExpertEarningDto:
    transaction: TransactionDto


class RecordExpertEarning(Interactor[RecordExpertEarningDto, ExpertEarningDto]):
    required_permission = None

    def __init__(self, finance_dao: ExpertFinanceDao) -> None:
        self.finance_dao = finance_dao

    async def _execute(self, actor: UserDto, data: RecordExpertEarningDto) -> ExpertEarningDto:
        if not data.transaction.is_completed:
            raise ValueError("Доход можно начислить только по успешно оплаченному платежу")
        expert_profile_id = data.transaction.expert_profile_id
        if expert_profile_id is None:
            raise ValueError("Платёж не связан с экспертом")
        return await self.finance_dao.record_earning(
            expert_profile_id,
            data.transaction.payment_id,
            data.transaction.pricing.final_amount,
            data.transaction.currency,
        )


@dataclass(frozen=True)
class ReverseExpertEarningDto:
    payment_id: UUID


class ReverseExpertEarning(Interactor[ReverseExpertEarningDto, Optional[ExpertEarningDto]]):
    required_permission = None

    def __init__(self, finance_dao: ExpertFinanceDao) -> None:
        self.finance_dao = finance_dao

    async def _execute(
        self,
        actor: UserDto,
        data: ReverseExpertEarningDto,
    ) -> Optional[ExpertEarningDto]:
        return await self.finance_dao.reverse_earning(data.payment_id)


@dataclass(frozen=True)
class RequestExpertWithdrawalDto:
    amount: Decimal
    currency: Currency
    bank_name: str


class RequestExpertWithdrawal(Interactor[RequestExpertWithdrawalDto, ExpertWithdrawalDto]):
    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        expert_dao: ExpertDao,
        finance_dao: ExpertFinanceDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.finance_dao = finance_dao
        self.notifier = notifier

    async def _execute(
        self, actor: UserDto, data: RequestExpertWithdrawalDto
    ) -> ExpertWithdrawalDto:
        profile = await self.expert_dao.get_by_user(actor.telegram_id)
        if not profile or profile.status != ExpertProfileStatus.ACTIVE:
            raise PermissionDeniedError
        amount = data.amount.quantize(Decimal("0.01"))
        bank_name = " ".join(data.bank_name.split())
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
        if not 2 <= len(bank_name) <= 128:
            raise ValueError("Укажите название банка")
        if profile.id is None:
            raise ValueError("Анкета эксперта не сохранена")
        async with self.uow:
            withdrawal = await self.finance_dao.create_withdrawal(
                profile.id,
                amount,
                data.currency,
                bank_name,
            )
            await self.uow.commit()
        await self.notifier.notify_admins(
            MessagePayloadDto(
                i18n_key="ntf-expert.withdrawal-request",
                i18n_kwargs={
                    "id": withdrawal.id,
                    "expert": profile.display_name,
                    "amount": withdrawal.amount,
                    "currency": withdrawal.currency.value,
                    "bank": withdrawal.bank_name,
                },
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Одобрить",
                                callback_data=f"expert_withdrawal:approve:{withdrawal.id}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отклонить",
                                callback_data=f"expert_withdrawal:reject:{withdrawal.id}",
                            ),
                        ]
                    ]
                ),
                delete_after=None,
            )
        )
        return withdrawal


@dataclass(frozen=True)
class ProcessExpertWithdrawalDto:
    withdrawal_id: int
    approve: bool
    reason: str | None = None


class ProcessExpertWithdrawal(Interactor[ProcessExpertWithdrawalDto, ExpertWithdrawalDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(
        self,
        uow: UnitOfWork,
        expert_dao: ExpertDao,
        user_dao: UserDao,
        finance_dao: ExpertFinanceDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.user_dao = user_dao
        self.finance_dao = finance_dao
        self.notifier = notifier

    async def _execute(
        self, actor: UserDto, data: ProcessExpertWithdrawalDto
    ) -> ExpertWithdrawalDto:
        async with self.uow:
            withdrawal = await self.finance_dao.process_withdrawal(
                data.withdrawal_id,
                WithdrawalStatus.APPROVED if data.approve else WithdrawalStatus.REJECTED,
                actor.telegram_id,
                data.reason,
            )
            profile = await self.expert_dao.get_by_id(withdrawal.expert_profile_id)
            if not profile:
                raise ValueError("Анкета эксперта не найдена")
            expert_user = await self.user_dao.get_by_telegram_id(profile.user_telegram_id)
            if not expert_user:
                raise ValueError("Пользователь эксперта не найден")
            await self.uow.commit()
        await self.notifier.notify_user(
            expert_user,
            MessagePayloadDto(
                i18n_key="ntf-expert.withdrawal-approved"
                if data.approve
                else "ntf-expert.withdrawal-rejected",
                i18n_kwargs={
                    "id": withdrawal.id,
                    "amount": withdrawal.amount,
                    "currency": withdrawal.currency.value,
                    "reason": data.reason or "Причина не указана",
                },
                delete_after=None,
            ),
        )
        return withdrawal
