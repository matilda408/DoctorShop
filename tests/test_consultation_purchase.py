from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.dto import (
    ExpertProfileDto,
    PlanSnapshotDto,
    PriceDetailsDto,
    TransactionDto,
    UserDto,
)
from src.application.use_cases.consultation.commands import (
    PurchaseConsultation,
    PurchaseConsultationDto,
    RetryConsultationTopic,
    SetConsultationActive,
    SetConsultationActiveDto,
    SetExpertProfileStatus,
    SetExpertProfileStatusDto,
)
from src.application.use_cases.gateways.commands.payment import (
    ProcessPayment,
    ProcessPaymentDto,
)
from src.core.enums import (
    ConsultationStatus,
    Currency,
    ExpertProfileStatus,
    PaymentGatewayType,
    PurchaseType,
    Role,
    TransactionStatus,
)
from src.core.exceptions import PermissionDeniedError
from src.core.utils.time import datetime_now
from src.telegram.routers.experts.handlers import can_access_consultation


class FakeConsultationDao:
    def __init__(self) -> None:
        self.consultations = {}
        self.subscriptions = []
        self.activated_subscription_ids = []
        self.expired_subscription_ids = []

    @property
    def consultation(self):
        return next(iter(self.consultations.values()), None)

    async def subscription_exists(self, payment_id):
        return any(item.transaction_payment_id == payment_id for item in self.subscriptions)

    async def get_by_client_and_expert(self, client_telegram_id, expert_profile_id):
        return self.consultations.get((client_telegram_id, expert_profile_id))

    async def get_by_id(self, consultation_id):
        return next(
            (item for item in self.consultations.values() if item.id == consultation_id),
            None,
        )

    async def create(self, consultation):
        consultation.id = len(self.consultations) + 1
        self.consultations[(consultation.client_telegram_id, consultation.expert_profile_id)] = (
            consultation
        )
        return consultation

    async def update(self, consultation):
        self.consultations[(consultation.client_telegram_id, consultation.expert_profile_id)] = (
            consultation
        )
        return consultation

    async def create_subscription(self, subscription):
        subscription.id = len(self.subscriptions) + 1
        self.subscriptions.append(subscription)
        return subscription

    async def activate_subscriptions(self, consultation_id):
        self.activated_subscription_ids.append(consultation_id)

    async def expire_subscriptions(self, consultation_id):
        self.expired_subscription_ids.append(consultation_id)


class FakeExpertDao:
    def __init__(self, profile_ids=(7,)) -> None:
        self.profiles = {
            profile_id: ExpertProfileDto(
                id=profile_id,
                user_telegram_id=700 + profile_id,
                display_name=f"Доктор {profile_id}",
                specialization="Терапевт",
                status=ExpertProfileStatus.ACTIVE,
            )
            for profile_id in profile_ids
        }

    async def get_by_id(self, profile_id):
        return self.profiles.get(profile_id)

    async def update_status(self, profile_id, status):
        profile = self.profiles.get(profile_id)
        if profile:
            profile.status = status
        return profile

    async def get_active(self):
        return [profile for profile in self.profiles.values() if profile.is_available]


class FakeUserDao:
    def __init__(self, user=None) -> None:
        self.updated_users = []
        self.user = user

    async def get_by_telegram_id(self, telegram_id):
        return self.user if self.user and self.user.telegram_id == telegram_id else None

    async def update(self, user):
        self.updated_users.append(user)
        return user


class FakeBot:
    def __init__(self, *, topic_error=None, fail_on_call=None) -> None:
        self.created_topics = 0
        self.sent_messages = 0
        self.topic_error = topic_error
        self.fail_on_call = fail_on_call

    async def create_forum_topic(self, chat_id, name):
        self.created_topics += 1
        if self.topic_error and (
            self.fail_on_call is None or self.created_topics == self.fail_on_call
        ):
            raise self.topic_error
        return SimpleNamespace(message_thread_id=98 + self.created_topics)

    async def send_message(self, **kwargs):
        self.sent_messages += 1


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


class FakeTransactionDao:
    def __init__(self, transaction):
        self.transaction = transaction
        self.updated_statuses = []

    async def get_by_payment_id_for_update(self, payment_id):
        return self.transaction if self.transaction.payment_id == payment_id else None

    async def update_status(self, payment_id, status):
        self.updated_statuses.append(status)
        self.transaction.status = status
        return self.transaction


class ForbiddenPurchase:
    @property
    def system(self):
        raise AssertionError("Purchase must not run for an unsuccessful payment")


class FakeEarningReversal:
    def __init__(self) -> None:
        self.payment_ids = []

    @property
    def system(self):
        return self.reverse

    async def reverse(self, data):
        self.payment_ids.append(data.payment_id)


def make_transaction(*, payment_id=None, duration=30, expert_profile_id=7, user_id=123):
    return TransactionDto(
        payment_id=payment_id or uuid4(),
        user_telegram_id=user_id,
        status=TransactionStatus.COMPLETED,
        purchase_type=PurchaseType.NEW,
        gateway_type=PaymentGatewayType.TELEGRAM_STARS,
        pricing=PriceDetailsDto(
            original_amount=Decimal("100"),
            discount_percent=0,
            final_amount=Decimal("100"),
        ),
        currency=Currency.XTR,
        plan_snapshot=PlanSnapshotDto(
            id=1,
            name="consultation",
            duration=duration,
        ),
        expert_profile_id=expert_profile_id,
    )


@pytest.mark.asyncio
async def test_purchase_creates_paired_private_topics_and_is_idempotent():
    consultation_dao = FakeConsultationDao()
    bot = FakeBot()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=FakeUserDao(),
        bot=bot,
    )
    user = UserDto(telegram_id=123, name="Клиент")
    transaction = make_transaction()

    first = await purchase.system(PurchaseConsultationDto(user, transaction))
    second = await purchase.system(PurchaseConsultationDto(user, transaction))

    assert first.id == second.id == 1
    assert first.client_thread_id == 99
    assert first.expert_thread_id == 100
    assert bot.created_topics == 2
    assert len(consultation_dao.subscriptions) == 1


@pytest.mark.asyncio
async def test_new_payment_extends_existing_consultation_without_duplicate_topic():
    consultation_dao = FakeConsultationDao()
    bot = FakeBot()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=FakeUserDao(),
        bot=bot,
    )
    user = UserDto(telegram_id=123, name="Клиент")
    first = await purchase.system(PurchaseConsultationDto(user, make_transaction(duration=30)))
    first_expiry = first.access_expires_at
    second = await purchase.system(PurchaseConsultationDto(user, make_transaction(duration=10)))

    assert second.access_expires_at >= first_expiry + timedelta(days=10)
    assert second.access_expires_at > datetime_now()
    assert bot.created_topics == 2
    assert len(consultation_dao.subscriptions) == 2


@pytest.mark.asyncio
async def test_purchase_consumes_banked_referral_days():
    consultation_dao = FakeConsultationDao()
    user_dao = FakeUserDao()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=user_dao,
        bot=FakeBot(),
    )
    user = UserDto(
        telegram_id=123,
        name="Клиент",
        consultation_bonus_days=5,
    )
    before_purchase = datetime_now()

    consultation = await purchase.system(
        PurchaseConsultationDto(user, make_transaction(duration=10))
    )

    assert consultation.access_expires_at >= before_purchase + timedelta(days=15)
    assert user.consultation_bonus_days == 0
    assert user_dao.updated_users == [user]


@pytest.mark.asyncio
async def test_one_client_can_purchase_from_multiple_experts():
    consultation_dao = FakeConsultationDao()
    bot = FakeBot()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao((7, 8)),
        user_dao=FakeUserDao(),
        bot=bot,
    )
    user = UserDto(telegram_id=123, name="Клиент")

    first = await purchase.system(
        PurchaseConsultationDto(user, make_transaction(expert_profile_id=7))
    )
    second = await purchase.system(
        PurchaseConsultationDto(user, make_transaction(expert_profile_id=8))
    )

    assert first.id != second.id
    assert {item.expert_profile_id for item in consultation_dao.consultations.values()} == {
        7,
        8,
    }
    assert bot.created_topics == 4


@pytest.mark.asyncio
async def test_one_expert_can_receive_multiple_clients():
    consultation_dao = FakeConsultationDao()
    bot = FakeBot()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=FakeUserDao(),
        bot=bot,
    )

    for user_id in (123, 124):
        await purchase.system(
            PurchaseConsultationDto(
                UserDto(telegram_id=user_id, name=f"Клиент {user_id}"),
                make_transaction(user_id=user_id),
            )
        )

    assert {item.client_telegram_id for item in consultation_dao.consultations.values()} == {
        123,
        124,
    }
    assert bot.created_topics == 4


@pytest.mark.asyncio
async def test_topic_creation_error_is_persisted_without_duplicate_subscription():
    consultation_dao = FakeConsultationDao()
    transaction = make_transaction()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=FakeUserDao(),
        bot=FakeBot(topic_error=RuntimeError("telegram unavailable")),
    )
    user = UserDto(telegram_id=123, name="Клиент")

    first = await purchase.system(PurchaseConsultationDto(user, transaction))
    second = await purchase.system(PurchaseConsultationDto(user, transaction))

    assert first.status == ConsultationStatus.ERROR
    assert first.creation_error == "telegram unavailable"
    assert second.id == first.id
    assert len(consultation_dao.subscriptions) == 1


@pytest.mark.asyncio
async def test_retry_creates_only_missing_private_topic():
    consultation_dao = FakeConsultationDao()
    expert_dao = FakeExpertDao()
    bot = FakeBot(
        topic_error=RuntimeError("expert private topics unavailable"),
        fail_on_call=2,
    )
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=expert_dao,
        user_dao=FakeUserDao(),
        bot=bot,
    )
    consultation = await purchase.system(
        PurchaseConsultationDto(
            UserDto(telegram_id=123, name="Клиент"),
            make_transaction(),
        )
    )

    assert consultation.status == ConsultationStatus.ERROR
    assert consultation.client_thread_id == 99
    assert consultation.expert_thread_id is None

    bot.topic_error = None
    retried = await RetryConsultationTopic(
        uow=FakeUnitOfWork(),
        consultation_dao=consultation_dao,
        expert_dao=expert_dao,
        bot=bot,
    )(
        UserDto(telegram_id=1, name="Администратор", role=Role.ADMIN),
        consultation.id,
    )

    assert retried.status == ConsultationStatus.ACTIVE
    assert retried.client_thread_id == 99
    assert retried.expert_thread_id == 101
    assert bot.created_topics == 3


def test_disabled_expert_is_not_available_for_new_purchases():
    profile = FakeExpertDao().profiles[7]
    profile.status = ExpertProfileStatus.DISABLED

    assert profile.is_available is False


@pytest.mark.asyncio
async def test_admin_can_close_and_restore_existing_consultation():
    consultation_dao = FakeConsultationDao()
    bot = FakeBot()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=FakeExpertDao(),
        user_dao=FakeUserDao(),
        bot=bot,
    )
    consultation = await purchase.system(
        PurchaseConsultationDto(
            UserDto(telegram_id=123, name="Клиент"),
            make_transaction(),
        )
    )
    lifecycle = SetConsultationActive(
        uow=FakeUnitOfWork(),
        consultation_dao=consultation_dao,
    )
    admin = UserDto(telegram_id=1, name="Администратор", role=Role.ADMIN)

    closed = await lifecycle(
        admin,
        SetConsultationActiveDto(consultation_id=consultation.id, active=False),
    )
    restored = await lifecycle(
        admin,
        SetConsultationActiveDto(consultation_id=consultation.id, active=True),
    )

    assert closed.id == restored.id == consultation.id
    assert restored.status == ConsultationStatus.ACTIVE
    assert consultation_dao.expired_subscription_ids == [consultation.id]
    assert consultation_dao.activated_subscription_ids == [consultation.id]

    expert = UserDto(telegram_id=777, name="Эксперт", role=Role.EXPERT)
    with pytest.raises(PermissionDeniedError):
        await lifecycle(
            expert,
            SetConsultationActiveDto(consultation_id=consultation.id, active=False),
        )


@pytest.mark.asyncio
async def test_disabling_expert_hides_profile_without_deleting_consultation():
    consultation_dao = FakeConsultationDao()
    expert_dao = FakeExpertDao()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=expert_dao,
        user_dao=FakeUserDao(),
        bot=FakeBot(),
    )
    consultation = await purchase.system(
        PurchaseConsultationDto(
            UserDto(telegram_id=123, name="Клиент"),
            make_transaction(),
        )
    )
    status = SetExpertProfileStatus(FakeUnitOfWork(), expert_dao)
    admin = UserDto(telegram_id=1, name="Администратор", role=Role.ADMIN)

    await status(
        admin,
        SetExpertProfileStatusDto(
            expert_profile_id=7,
            status=ExpertProfileStatus.DISABLED,
        ),
    )

    assert await expert_dao.get_active() == []
    assert await consultation_dao.get_by_id(consultation.id) is consultation


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "actor",
    [
        UserDto(telegram_id=999, name="Чужой клиент"),
        UserDto(telegram_id=888, name="Другой эксперт", role=Role.EXPERT),
    ],
)
async def test_client_and_expert_cannot_open_foreign_consultation(actor):
    consultation_dao = FakeConsultationDao()
    expert_dao = FakeExpertDao()
    purchase = PurchaseConsultation(
        consultation_dao=consultation_dao,
        expert_dao=expert_dao,
        user_dao=FakeUserDao(),
        bot=FakeBot(),
    )
    consultation = await purchase.system(
        PurchaseConsultationDto(
            UserDto(telegram_id=123, name="Клиент"),
            make_transaction(),
        )
    )

    assert can_access_consultation(actor, consultation, expert_dao.profiles[7]) is False


@pytest.mark.asyncio
async def test_canceled_payment_does_not_create_consultation():
    transaction = make_transaction()
    transaction.status = TransactionStatus.PENDING
    transaction_dao = FakeTransactionDao(transaction)
    process = ProcessPayment(
        uow=FakeUnitOfWork(),
        user_dao=FakeUserDao(UserDto(telegram_id=123, name="Клиент")),
        transaction_dao=transaction_dao,
        subscription_dao=SimpleNamespace(),
        referral_dao=SimpleNamespace(),
        event_publisher=SimpleNamespace(),
        notifier=SimpleNamespace(),
        i18n=SimpleNamespace(),
        assign_referral_rewards=SimpleNamespace(),
        purchase_subscription=SimpleNamespace(),
        purchase_consultation=ForbiddenPurchase(),
        redirect=SimpleNamespace(),
    )

    await process.system(
        ProcessPaymentDto(
            payment_id=transaction.payment_id,
            new_transaction_status=TransactionStatus.CANCELED,
        )
    )

    assert transaction_dao.updated_statuses == [TransactionStatus.CANCELED]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "final_status",
    [TransactionStatus.CANCELED, TransactionStatus.REFUNDED],
)
async def test_completed_expert_payment_reversal_is_processed_once(final_status):
    transaction = make_transaction()
    transaction_dao = FakeTransactionDao(transaction)
    reversal = FakeEarningReversal()
    uow = FakeUnitOfWork()
    process = ProcessPayment(
        uow=uow,
        user_dao=FakeUserDao(UserDto(telegram_id=123, name="Клиент")),
        transaction_dao=transaction_dao,
        subscription_dao=SimpleNamespace(),
        referral_dao=SimpleNamespace(),
        event_publisher=SimpleNamespace(),
        notifier=SimpleNamespace(),
        i18n=SimpleNamespace(),
        assign_referral_rewards=SimpleNamespace(),
        purchase_subscription=SimpleNamespace(),
        purchase_consultation=ForbiddenPurchase(),
        redirect=SimpleNamespace(),
        reverse_expert_earning=reversal,
    )
    update = ProcessPaymentDto(
        payment_id=transaction.payment_id,
        new_transaction_status=final_status,
    )

    await process.system(update)
    await process.system(update)

    assert transaction_dao.updated_statuses == [final_status]
    assert reversal.payment_ids == [transaction.payment_id]
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_repeated_success_callback_does_not_accrue_expert_income_twice():
    transaction = make_transaction()
    transaction.status = TransactionStatus.PENDING
    transaction_dao = FakeTransactionDao(transaction)
    earning = SimpleNamespace(system=AsyncMock())
    process = ProcessPayment(
        uow=FakeUnitOfWork(),
        user_dao=FakeUserDao(UserDto(telegram_id=123, name="Клиент")),
        transaction_dao=transaction_dao,
        subscription_dao=SimpleNamespace(get_current=AsyncMock(return_value=None)),
        referral_dao=SimpleNamespace(),
        event_publisher=SimpleNamespace(publish=AsyncMock()),
        notifier=SimpleNamespace(),
        i18n=SimpleNamespace(),
        assign_referral_rewards=SimpleNamespace(system=AsyncMock()),
        purchase_subscription=SimpleNamespace(system=AsyncMock()),
        purchase_consultation=SimpleNamespace(system=AsyncMock()),
        redirect=SimpleNamespace(to_success_payment=AsyncMock()),
        record_expert_earning=earning,
    )
    update = ProcessPaymentDto(
        payment_id=transaction.payment_id,
        new_transaction_status=TransactionStatus.COMPLETED,
    )

    await process.system(update)
    await process.system(update)

    assert transaction_dao.updated_statuses == [TransactionStatus.COMPLETED]
    assert earning.system.await_count == 1
