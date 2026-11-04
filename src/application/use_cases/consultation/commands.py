from dataclasses import dataclass
from datetime import timedelta

from aiogram import Bot
from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import ConsultationDao, ExpertDao, UserDao
from src.application.common.policy import Permission, PermissionPolicy
from src.application.common.uow import UnitOfWork
from src.application.dto import (
    ConsultationDto,
    ExpertProfileDto,
    ExpertSubscriptionDto,
    TransactionDto,
    UserDto,
)
from src.core.enums import (
    ConsultationStatus,
    ExpertProfileStatus,
    Role,
    SubscriptionStatus,
)
from src.core.exceptions import PermissionDeniedError
from src.core.utils.converters import days_to_datetime
from src.core.utils.time import datetime_now


@dataclass(frozen=True)
class PurchaseConsultationDto:
    user: UserDto
    transaction: TransactionDto


async def provision_private_topics(
    bot: Bot,
    consultation_dao: ConsultationDao,
    consultation: ConsultationDto,
    expert: ExpertProfileDto,
) -> ConsultationDto:
    """Create the paired client/expert topics without duplicating either side."""
    try:
        if consultation.client_thread_id is None:
            client_topic = await bot.create_forum_topic(
                chat_id=consultation.client_telegram_id,
                name=f"Консультация · {expert.display_name}"[:128],
            )
            consultation.client_thread_id = client_topic.message_thread_id
            consultation = await consultation_dao.update(consultation)

        if consultation.expert_thread_id is None:
            expert_topic = await bot.create_forum_topic(
                chat_id=expert.user_telegram_id,
                name=f"Консультация #{consultation.id}"[:128],
            )
            consultation.expert_thread_id = expert_topic.message_thread_id
            consultation = await consultation_dao.update(consultation)

        consultation.status = ConsultationStatus.ACTIVE
        consultation.creation_error = None
        consultation = await consultation_dao.update(consultation)
    except Exception as error:
        logger.exception(
            "Failed to provision private topics for consultation '{}': {}",
            consultation.id,
            error,
        )
        consultation.status = ConsultationStatus.ERROR
        consultation.creation_error = str(error)[:2000]
        return await consultation_dao.update(consultation)

    notifications = (
        (
            consultation.client_telegram_id,
            consultation.client_thread_id,
            (
                f"Консультация с экспертом «{expert.display_name}» доступна.\n"
                "Сообщения из этой темы передаются только назначенному эксперту."
            ),
        ),
        (
            expert.user_telegram_id,
            consultation.expert_thread_id,
            (
                f"Назначена консультация #{consultation.id}.\n"
                "Сообщения из этой темы передаются только соответствующему клиенту."
            ),
        ),
    )
    for chat_id, thread_id, text in notifications:
        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
            )
        except Exception as error:
            logger.warning(
                "Could not send topic notification for consultation '{}': {}",
                consultation.id,
                error,
            )
    return consultation


class PurchaseConsultation(Interactor[PurchaseConsultationDto, ConsultationDto]):
    """Grant paid access and provision a forum topic idempotently."""

    required_permission = None

    def __init__(
        self,
        consultation_dao: ConsultationDao,
        expert_dao: ExpertDao,
        user_dao: UserDao,
        bot: Bot,
    ) -> None:
        self.consultation_dao = consultation_dao
        self.expert_dao = expert_dao
        self.user_dao = user_dao
        self.bot = bot

    async def _execute(self, actor: UserDto, data: PurchaseConsultationDto) -> ConsultationDto:
        transaction = data.transaction
        expert_profile_id = transaction.expert_profile_id
        if expert_profile_id is None:
            raise ValueError("Transaction is not linked to an expert")

        if await self.consultation_dao.subscription_exists(transaction.payment_id):
            existing = await self.consultation_dao.get_by_client_and_expert(
                data.user.telegram_id, expert_profile_id
            )
            if not existing:
                raise RuntimeError("Paid subscription exists without consultation")
            return existing

        expert = await self.expert_dao.get_by_id(expert_profile_id)
        if not expert:
            raise ValueError(f"Expert profile '{expert_profile_id}' not found")

        now = datetime_now()
        consultation = await self.consultation_dao.get_by_client_and_expert(
            data.user.telegram_id, expert_profile_id
        )
        duration = transaction.plan_snapshot.duration
        bonus_days = max(data.user.consultation_bonus_days, 0) if duration != 0 else 0
        base_date = max(consultation.access_expires_at, now) if consultation else now
        expires_at = (
            days_to_datetime(0)
            if duration == 0
            else base_date + timedelta(days=duration + bonus_days)
        )

        if consultation is None:
            consultation = await self.consultation_dao.create(
                ConsultationDto(
                    client_telegram_id=data.user.telegram_id,
                    expert_profile_id=expert_profile_id,
                    client_thread_id=None,
                    expert_thread_id=None,
                    status=ConsultationStatus.CREATING,
                    access_expires_at=expires_at,
                )
            )
        else:
            consultation.access_expires_at = expires_at
            consultation.status = (
                ConsultationStatus.ACTIVE
                if consultation.client_thread_id is not None
                and consultation.expert_thread_id is not None
                else ConsultationStatus.CREATING
            )
            consultation.creation_error = None
            consultation = await self.consultation_dao.update(consultation)

        await self.consultation_dao.create_subscription(
            ExpertSubscriptionDto(
                client_telegram_id=data.user.telegram_id,
                expert_profile_id=expert_profile_id,
                consultation_id=consultation.id,  # type: ignore[arg-type]
                transaction_payment_id=transaction.payment_id,
                status=SubscriptionStatus.ACTIVE,
                starts_at=now,
                expires_at=expires_at,
                plan_snapshot=transaction.plan_snapshot,
            )
        )
        if bonus_days:
            data.user.consultation_bonus_days = 0
            await self.user_dao.update(data.user)

        if consultation.client_thread_id is None or consultation.expert_thread_id is None:
            consultation = await provision_private_topics(
                self.bot,
                self.consultation_dao,
                consultation,
                expert,
            )

        logger.info(
            "Consultation access granted: consultation_id='{}', client='{}', expert='{}'",
            consultation.id,
            data.user.telegram_id,
            expert_profile_id,
        )
        return consultation


@dataclass(frozen=True)
class CreateExpertProfileDto:
    user_telegram_id: int
    display_name: str
    specialization: str
    short_description: str = ""
    description: str = ""
    experience_years: int = 0
    photo_file_id: str | None = None


class CreateExpertProfile(Interactor[CreateExpertProfileDto, ExpertProfileDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(self, uow: UnitOfWork, expert_dao: ExpertDao, user_dao: UserDao) -> None:
        self.uow = uow
        self.expert_dao = expert_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, data: CreateExpertProfileDto) -> ExpertProfileDto:
        async with self.uow:
            user = await self.user_dao.get_by_telegram_id(data.user_telegram_id)
            if not user:
                raise ValueError(f"User '{data.user_telegram_id}' not found")
            if await self.expert_dao.get_by_user(data.user_telegram_id):
                raise ValueError("Expert profile already exists")
            profile = await self.expert_dao.create(
                ExpertProfileDto(
                    user_telegram_id=data.user_telegram_id,
                    display_name=data.display_name,
                    specialization=data.specialization,
                    short_description=data.short_description,
                    description=data.description,
                    experience_years=data.experience_years,
                    photo_file_id=data.photo_file_id,
                    status=ExpertProfileStatus.DRAFT,
                )
            )
            user.role = Role.EXPERT
            await self.user_dao.update(user)
            await self.uow.commit()
            return profile


@dataclass(frozen=True)
class SetExpertProfileStatusDto:
    expert_profile_id: int
    status: ExpertProfileStatus


class SetExpertProfileStatus(Interactor[SetExpertProfileStatusDto, ExpertProfileDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(self, uow: UnitOfWork, expert_dao: ExpertDao) -> None:
        self.uow = uow
        self.expert_dao = expert_dao

    async def _execute(self, actor: UserDto, data: SetExpertProfileStatusDto) -> ExpertProfileDto:
        async with self.uow:
            profile = await self.expert_dao.update_status(data.expert_profile_id, data.status)
            if not profile:
                raise ValueError(f"Expert profile '{data.expert_profile_id}' not found")
            await self.uow.commit()
            return profile


@dataclass(frozen=True)
class EditExpertProfileDto:
    expert_profile_id: int
    field: str
    value: str


class EditExpertProfile(Interactor[EditExpertProfileDto, ExpertProfileDto]):
    required_permission = Permission.PUBLIC

    EDITABLE_FIELDS = {
        "name": "display_name",
        "specialization": "specialization",
        "short": "short_description",
        "description": "description",
        "experience": "experience_years",
        "photo": "photo_file_id",
    }

    def __init__(self, uow: UnitOfWork, expert_dao: ExpertDao) -> None:
        self.uow = uow
        self.expert_dao = expert_dao

    @staticmethod
    def _validate_text_value(attribute: str, raw_value: str) -> None:
        limits = {
            "display_name": (3, 128, "Имя должно содержать от 3 до 128 символов"),
            "specialization": (2, 128, "Специализация должна содержать от 2 до 128 символов"),
            "description": (10, 2000, "Описание должно содержать от 10 до 2000 символов"),
        }
        min_length, max_length, error_message = limits[attribute]
        if not min_length <= len(raw_value) <= max_length:
            raise ValueError(error_message)

    @classmethod
    def _prepare_value(
        cls,
        profile: ExpertProfileDto,
        attribute: str,
        raw_value: str,
    ) -> str | int | None:
        if attribute in {"display_name", "specialization", "description"}:
            cls._validate_text_value(attribute, raw_value)
            if attribute == "description":
                profile.short_description = raw_value[:512]
            return raw_value
        if attribute == "experience_years":
            value = int(raw_value)
            if not 0 <= value <= 100:
                raise ValueError("Experience must be between 0 and 100 years")
            return value
        if attribute == "photo_file_id" and raw_value == "-":
            return None
        if not raw_value:
            raise ValueError("Profile value cannot be empty")
        return raw_value

    async def _execute(self, actor: UserDto, data: EditExpertProfileDto) -> ExpertProfileDto:
        profile = await self.expert_dao.get_by_id(data.expert_profile_id)
        if not profile:
            raise ValueError(f"Expert profile '{data.expert_profile_id}' not found")
        if actor.role != Role.EXPERT and not PermissionPolicy.has_permission(
            actor, Permission.EXPERT_EDITOR
        ):
            raise PermissionDeniedError
        if actor.role == Role.EXPERT and profile.user_telegram_id != actor.telegram_id:
            raise PermissionDeniedError
        attribute = self.EDITABLE_FIELDS.get(data.field.lower())
        if attribute is None:
            raise ValueError("Unsupported expert profile field")
        raw_value = data.value.strip()
        value = self._prepare_value(profile, attribute, raw_value)
        setattr(profile, attribute, value)
        async with self.uow:
            profile = await self.expert_dao.update(profile)
            await self.uow.commit()
        return profile


@dataclass(frozen=True)
class SetConsultationActiveDto:
    consultation_id: int
    active: bool


class SetConsultationActive(Interactor[SetConsultationActiveDto, ConsultationDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(
        self,
        uow: UnitOfWork,
        consultation_dao: ConsultationDao,
    ) -> None:
        self.uow = uow
        self.consultation_dao = consultation_dao

    async def _execute(self, actor: UserDto, data: SetConsultationActiveDto) -> ConsultationDto:
        consultation = await self.consultation_dao.get_by_id(data.consultation_id)
        if not consultation:
            raise ValueError(f"Consultation '{data.consultation_id}' not found")
        if data.active and consultation.access_expires_at <= datetime_now():
            raise ValueError("Cannot restore consultation with expired paid access")

        async with self.uow:
            consultation.status = (
                ConsultationStatus.ACTIVE if data.active else ConsultationStatus.CLOSED
            )
            consultation.creation_error = None
            consultation = await self.consultation_dao.update(consultation)
            if consultation.id is not None:
                if data.active:
                    await self.consultation_dao.activate_subscriptions(consultation.id)
                else:
                    await self.consultation_dao.expire_subscriptions(consultation.id)
            await self.uow.commit()
        return consultation


class ExpireConsultations(Interactor[None, int]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        consultation_dao: ConsultationDao,
    ) -> None:
        self.uow = uow
        self.consultation_dao = consultation_dao

    async def _execute(self, actor: UserDto, data: None) -> int:
        expired = await self.consultation_dao.get_expired_active(datetime_now())
        if not expired:
            return 0
        async with self.uow:
            for consultation in expired:
                consultation.status = ConsultationStatus.EXPIRED
                await self.consultation_dao.update(consultation)
                if consultation.id is not None:
                    await self.consultation_dao.expire_subscriptions(consultation.id)
            await self.uow.commit()
        return len(expired)


class RetryConsultationTopic(Interactor[int, ConsultationDto]):
    required_permission = Permission.EXPERT_EDITOR

    def __init__(
        self,
        uow: UnitOfWork,
        consultation_dao: ConsultationDao,
        expert_dao: ExpertDao,
        bot: Bot,
    ) -> None:
        self.uow = uow
        self.consultation_dao = consultation_dao
        self.expert_dao = expert_dao
        self.bot = bot

    async def _execute(self, actor: UserDto, consultation_id: int) -> ConsultationDto:
        consultation = await self.consultation_dao.get_by_id(consultation_id)
        if not consultation:
            raise ValueError(f"Consultation '{consultation_id}' not found")
        if consultation.client_thread_id is not None and consultation.expert_thread_id is not None:
            return consultation
        expert = await self.expert_dao.get_by_id(consultation.expert_profile_id)
        if not expert:
            raise ValueError("Expert profile not found")
        async with self.uow:
            consultation = await provision_private_topics(
                self.bot,
                self.consultation_dao,
                consultation,
                expert,
            )
            await self.uow.commit()
        return consultation
