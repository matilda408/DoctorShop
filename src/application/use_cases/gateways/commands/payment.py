import uuid
from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from src.application.common import (
    EventPublisher,
    Interactor,
    Notifier,
    Redirect,
    TranslatorHub,
    TranslatorRunner,
)
from src.application.common.dao import (
    ExpertDao,
    PaymentGatewayDao,
    ReferralDao,
    SubscriptionDao,
    TransactionDao,
    UserDao,
)
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import (
    PaymentResultDto,
    PlanSnapshotDto,
    PriceDetailsDto,
    TransactionDto,
    UserDto,
)
from src.application.dto.payment_gateway import (
    FreeKassaGatewaySettingsDto,
    MulenPayGatewaySettingsDto,
    PayMasterGatewaySettingsDto,
    PaymentGatewayDto,
    PlategaGatewaySettingsDto,
    RoboKassaGatewaySettingsDto,
    UrlPayGatewaySettingsDto,
    WataGatewaySettingsDto,
    YooKassaGatewaySettingsDto,
    YooMoneyGatewaySettingsDto,
)
from src.application.events import UserPurchaseEvent
from src.application.use_cases.consultation.commands import (
    PurchaseConsultation,
    PurchaseConsultationDto,
)
from src.application.use_cases.consultation.expert_business import (
    RecordExpertEarning,
    RecordExpertEarningDto,
    ReverseExpertEarning,
    ReverseExpertEarningDto,
)
from src.application.use_cases.gateways.queries.providers import GetPaymentGatewayInstance
from src.application.use_cases.referral.commands.rewards import (
    AssignReferralRewards,
    AssignReferralRewardsDto,
)
from src.application.use_cases.subscription.commands.purchase import (
    PurchaseSubscription,
    PurchaseSubscriptionDto,
)
from src.core.enums import Currency, PaymentGatewayType, PurchaseType, TransactionStatus
from src.core.payment_policy import ACTIVE_PAYMENT_GATEWAYS
from src.core.utils.i18n_helpers import i18n_format_days


class CreateDefaultPaymentGateway(Interactor[None, None]):
    required_permission = None

    def __init__(self, uow: UnitOfWork, gateway_dao: PaymentGatewayDao) -> None:
        self.uow = uow
        self.gateway_dao = gateway_dao

    async def _execute(self, actor: UserDto, data: None) -> None:
        async with self.uow:
            for gateway_type in ACTIVE_PAYMENT_GATEWAYS:
                if await self.gateway_dao.get_by_type(gateway_type):
                    continue

                is_active = gateway_type == PaymentGatewayType.TELEGRAM_STARS

                settings_map = {
                    PaymentGatewayType.YOOKASSA: YooKassaGatewaySettingsDto,
                    PaymentGatewayType.YOOMONEY: YooMoneyGatewaySettingsDto,
                    PaymentGatewayType.FREEKASSA: FreeKassaGatewaySettingsDto,
                    PaymentGatewayType.MULENPAY: MulenPayGatewaySettingsDto,
                    PaymentGatewayType.PAYMASTER: PayMasterGatewaySettingsDto,
                    PaymentGatewayType.PLATEGA: PlategaGatewaySettingsDto,
                    PaymentGatewayType.ROBOKASSA: RoboKassaGatewaySettingsDto,
                    PaymentGatewayType.URLPAY: UrlPayGatewaySettingsDto,
                    PaymentGatewayType.WATA: WataGatewaySettingsDto,
                }
                dto_class = settings_map.get(gateway_type)
                settings = dto_class() if dto_class else None

                await self.gateway_dao.create(
                    PaymentGatewayDto(
                        type=gateway_type,
                        currency=Currency.from_gateway_type(gateway_type),
                        is_active=is_active,
                        settings=settings,
                    )
                )
                logger.info(f"Payment gateway '{gateway_type}' created")

            await self.uow.commit()


@dataclass(frozen=True)
class CreatePaymentDto:
    plan_snapshot: PlanSnapshotDto
    pricing: PriceDetailsDto
    purchase_type: PurchaseType
    gateway_type: PaymentGatewayType
    platega_payment_method: int | None = None
    expert_profile_id: int | None = None


class CreatePayment(Interactor[CreatePaymentDto, PaymentResultDto]):
    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        payment_gateway_dao: PaymentGatewayDao,
        transaction_dao: TransactionDao,
        get_payment_gateway_instance: GetPaymentGatewayInstance,
        translator_hub: TranslatorHub,
        expert_dao: ExpertDao,
    ) -> None:
        self.uow = uow
        self.payment_gateway_dao = payment_gateway_dao
        self.transaction_dao = transaction_dao
        self.get_payment_gateway_instance = get_payment_gateway_instance
        self.translator_hub = translator_hub
        self.expert_dao = expert_dao

    async def _execute(self, actor: UserDto, data: CreatePaymentDto) -> PaymentResultDto:
        if data.gateway_type not in ACTIVE_PAYMENT_GATEWAYS:
            raise ValueError("Этот способ оплаты больше не поддерживается")
        if data.expert_profile_id is not None:
            expert = await self.expert_dao.get_by_id(data.expert_profile_id)
            if not expert or not expert.is_available:
                raise ValueError("Selected expert is not available for purchase")
            if expert.user_telegram_id == actor.telegram_id:
                raise ValueError("Expert cannot purchase a consultation with themselves")
            available_plans = await self.expert_dao.get_available_plans(data.expert_profile_id)
            if data.plan_snapshot.id not in {plan.id for plan in available_plans}:
                raise ValueError("Selected plan is not available for this expert")

        gateway_instance = await self.get_payment_gateway_instance.system(data.gateway_type)
        i18n = self.translator_hub.get_translator_by_locale(actor.language)

        key, kw = i18n_format_days(data.plan_snapshot.duration)
        details = i18n.get(
            "payment-invoice-description",
            purchase_type=data.purchase_type,
            name=data.plan_snapshot.name,
            duration=i18n.get(key, **kw),
        )

        transaction = TransactionDto(
            payment_id=uuid.uuid4(),
            user_telegram_id=actor.telegram_id,
            status=TransactionStatus.PENDING,
            purchase_type=data.purchase_type,
            gateway_type=gateway_instance.data.type,
            pricing=data.pricing,
            currency=gateway_instance.data.currency,
            plan_snapshot=data.plan_snapshot,
            expert_profile_id=data.expert_profile_id,
        )

        async with self.uow:
            if data.pricing.is_free:
                await self.transaction_dao.create(transaction)
                await self.uow.commit()

                logger.info(
                    f"Payment for user '{actor.telegram_id}' not created because pricing is free"
                )
                return PaymentResultDto(id=transaction.payment_id, url=None)

            if data.gateway_type == PaymentGatewayType.PLATEGA:
                payment: PaymentResultDto = await getattr(
                    gateway_instance, "handle_create_payment"
                )(
                    amount=data.pricing.final_amount,
                    details=details,
                    payment_method=data.platega_payment_method,
                )
            else:
                payment = await gateway_instance.handle_create_payment(
                    amount=data.pricing.final_amount,
                    details=details,
                )

            transaction.payment_id = payment.id
            await self.transaction_dao.create(transaction)
            await self.uow.commit()

        logger.info(f"Created transaction '{payment.id}' for user '{actor.telegram_id}'")
        return payment


class CreateTestPayment(Interactor[PaymentGatewayType, PaymentResultDto]):
    required_permission = Permission.REMNASHOP_GATEWAYS

    def __init__(
        self,
        uow: UnitOfWork,
        payment_gateway_dao: PaymentGatewayDao,
        transaction_dao: TransactionDao,
        get_payment_gateway_instance: GetPaymentGatewayInstance,
        translator_hub: TranslatorHub,
    ) -> None:
        self.uow = uow
        self.payment_gateway_dao = payment_gateway_dao
        self.transaction_dao = transaction_dao
        self.get_payment_gateway_instance = get_payment_gateway_instance
        self.translator_hub = translator_hub

    async def _execute(self, actor: UserDto, gateway_type: PaymentGatewayType) -> PaymentResultDto:
        if gateway_type not in ACTIVE_PAYMENT_GATEWAYS:
            raise ValueError("Этот способ оплаты больше не поддерживается")
        gateway_instance = await self.get_payment_gateway_instance.system(gateway_type)
        i18n = self.translator_hub.get_translator_by_locale(actor.language)

        test_pricing = PriceDetailsDto.test()
        test_plan_snapshot = PlanSnapshotDto.test()

        payment: PaymentResultDto = await gateway_instance.handle_create_payment(
            amount=test_pricing.final_amount,
            details=i18n.get("test-payment"),
        )

        async with self.uow:
            transaction = TransactionDto(
                payment_id=payment.id,
                user_telegram_id=actor.telegram_id,
                status=TransactionStatus.PENDING,
                is_test=True,
                purchase_type=PurchaseType.NEW,
                gateway_type=gateway_instance.data.type,
                pricing=test_pricing,
                currency=gateway_instance.data.currency,
                plan_snapshot=test_plan_snapshot,
            )
            await self.transaction_dao.create(transaction)
            await self.uow.commit()

        logger.info(f"Created test transaction '{payment.id}' for user '{actor.telegram_id}'")
        return payment


@dataclass(frozen=True)
class ProcessPaymentDto:
    payment_id: UUID
    new_transaction_status: TransactionStatus


class ProcessPayment(Interactor[ProcessPaymentDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        transaction_dao: TransactionDao,
        subscription_dao: SubscriptionDao,
        referral_dao: ReferralDao,
        event_publisher: EventPublisher,
        notifier: Notifier,
        i18n: TranslatorRunner,
        assign_referral_rewards: AssignReferralRewards,
        purchase_subscription: PurchaseSubscription,
        purchase_consultation: PurchaseConsultation,
        redirect: Redirect,
        record_expert_earning: RecordExpertEarning = None,  # type: ignore[assignment]
        reverse_expert_earning: ReverseExpertEarning = None,  # type: ignore[assignment]
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.transaction_dao = transaction_dao
        self.subscription_dao = subscription_dao
        self.referral_dao = referral_dao
        self.event_publisher = event_publisher
        self.notifier = notifier
        self.i18n = i18n
        self.assign_referral_rewards = assign_referral_rewards
        self.purchase_subscription = purchase_subscription
        self.purchase_consultation = purchase_consultation
        self.record_expert_earning = record_expert_earning
        self.reverse_expert_earning = reverse_expert_earning
        self.redirect = redirect

    async def _execute(self, actor: UserDto, data: ProcessPaymentDto) -> None:
        payment_id = data.payment_id
        new_status = data.new_transaction_status

        async with self.uow:
            transaction = await self.transaction_dao.get_by_payment_id_for_update(payment_id)

            if not transaction:
                logger.critical(f"Transaction not found for '{payment_id}'")
                return

            user = await self.user_dao.get_by_telegram_id(transaction.user_telegram_id)

            if not user:
                logger.critical(f"User not found for transaction '{payment_id}'")
                return

            if transaction.status == new_status:
                logger.warning(
                    f"Transaction '{payment_id}' for user '{user.telegram_id}' "
                    f"already has status '{new_status}'"
                )
                return

            if transaction.is_completed:
                await self._handle_completed_payment_update(transaction, user, new_status)
                return

            if new_status in {
                TransactionStatus.CANCELED,
                TransactionStatus.REFUNDED,
                TransactionStatus.FAILED,
            }:
                await self.transaction_dao.update_status(payment_id, new_status)
                await self.uow.commit()
                logger.info(
                    f"Payment '{payment_id}' for user '{user.telegram_id}' "
                    f"finished with status '{new_status}'"
                )
                return

            elif new_status == TransactionStatus.COMPLETED:
                completed_transaction = await self.transaction_dao.update_status(
                    payment_id,
                    TransactionStatus.COMPLETED,
                )
                if completed_transaction is None:
                    raise ValueError(f"Не удалось подтвердить платёж '{payment_id}'")
                expert_profile_id = await self._handle_success(user, completed_transaction)
                await self.uow.commit()
                logger.info(f"Payment succeeded '{payment_id}' for user '{user.telegram_id}'")
                if expert_profile_id is not None:
                    await self.redirect.to_success_payment(
                        user.telegram_id,
                        transaction.purchase_type,
                        expert_profile_id=expert_profile_id,
                    )

            else:
                logger.warning(
                    f"Received unhandled transaction status '{new_status}' "
                    f"for payment '{payment_id}', user '{user.telegram_id}'"
                )

    async def _handle_completed_payment_update(
        self,
        transaction: TransactionDto,
        user: UserDto,
        new_status: TransactionStatus,
    ) -> None:
        payment_id = transaction.payment_id
        if new_status not in {TransactionStatus.CANCELED, TransactionStatus.REFUNDED}:
            logger.warning(
                f"Ignoring transition from completed payment '{payment_id}' "
                f"to status '{new_status}'"
            )
            return

        await self.transaction_dao.update_status(payment_id, new_status)
        if transaction.expert_profile_id is not None and self.reverse_expert_earning:
            await self.reverse_expert_earning.system(
                ReverseExpertEarningDto(payment_id=payment_id)
            )
        await self.uow.commit()
        logger.info(
            f"Payment '{payment_id}' for user '{user.telegram_id}' "
            f"reversed with status '{new_status}'"
        )

    async def _handle_success(self, user: UserDto, transaction: TransactionDto) -> int | None:
        if transaction.is_test:
            await self.notifier.notify_user(user, i18n_key="ntf-gateway.test-payment-confirmed")
            return None

        subscription = await self.subscription_dao.get_current(user.telegram_id)
        old_plan = subscription.plan_snapshot if subscription else None

        event = UserPurchaseEvent(
            telegram_id=user.telegram_id,
            name=user.name,
            username=user.username,
            #
            purchase_type=transaction.purchase_type,
            is_trial_plan=transaction.plan_snapshot.is_trial,
            payment_id=transaction.payment_id,
            gateway_type=transaction.gateway_type,
            final_amount=transaction.pricing.final_amount,
            discount_percent=transaction.pricing.discount_percent,
            original_amount=transaction.pricing.original_amount,
            currency=transaction.currency.symbol,
            #
            plan_name=transaction.plan_snapshot.name,
            plan_duration=i18n_format_days(transaction.plan_snapshot.duration),
            #
            previous_plan_name=self.i18n.get(old_plan.name) if old_plan else "N/A",
            previous_plan_duration=i18n_format_days(old_plan.duration) if old_plan else "N/A",
        )

        await self.event_publisher.publish(event)

        if transaction.expert_profile_id is not None:
            await self.purchase_consultation.system(PurchaseConsultationDto(user, transaction))
            if self.record_expert_earning:
                await self.record_expert_earning.system(RecordExpertEarningDto(transaction))
            if not transaction.pricing.is_free:
                await self.assign_referral_rewards.system(
                    AssignReferralRewardsDto(user, transaction)
                )
            return transaction.expert_profile_id

        await self.purchase_subscription.system(
            PurchaseSubscriptionDto(user, transaction, subscription)
        )

        if not transaction.pricing.is_free:
            await self.assign_referral_rewards.system(AssignReferralRewardsDto(user, transaction))
        return None
