from datetime import datetime
from typing import Optional, cast
from uuid import UUID

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.common.dao import ConsultationDao, ExpertDao
from src.application.dto import (
    ConsultationDto,
    ExpertProfileDto,
    ExpertSubscriptionDto,
    PlanDto,
    PlanPriceDto,
)
from src.core.enums import ConsultationStatus, ExpertProfileStatus, SubscriptionStatus
from src.infrastructure.database.models import (
    Consultation,
    ExpertPlan,
    ExpertPlanPrice,
    ExpertProfile,
    ExpertSubscription,
    Plan,
    PlanDuration,
)


class ExpertDaoImpl(ExpertDao):
    def __init__(
        self, session: AsyncSession, retort: Retort, conversion_retort: ConversionRetort
    ) -> None:
        self.session = session
        self.retort = retort
        self._to_dto = conversion_retort.get_converter(ExpertProfile, ExpertProfileDto)
        self._to_dto_list = conversion_retort.get_converter(
            list[ExpertProfile], list[ExpertProfileDto]
        )
        self._plans_to_dto = conversion_retort.get_converter(list[Plan], list[PlanDto])

    async def create(self, profile: ExpertProfileDto) -> ExpertProfileDto:
        db_profile = ExpertProfile(**self.retort.dump(profile))
        self.session.add(db_profile)
        await self.session.flush()
        return self._to_dto(db_profile)

    async def get_by_id(self, profile_id: int) -> Optional[ExpertProfileDto]:
        db_profile = await self.session.scalar(
            select(ExpertProfile).where(ExpertProfile.id == profile_id)
        )
        return self._to_dto(db_profile) if db_profile else None

    async def get_by_id_for_update(self, profile_id: int) -> Optional[ExpertProfileDto]:
        db_profile = await self.session.scalar(
            select(ExpertProfile)
            .where(ExpertProfile.id == profile_id)
            .with_for_update()
        )
        return self._to_dto(db_profile) if db_profile else None

    async def get_by_user(self, telegram_id: int) -> Optional[ExpertProfileDto]:
        db_profile = await self.session.scalar(
            select(ExpertProfile).where(ExpertProfile.user_telegram_id == telegram_id)
        )
        return self._to_dto(db_profile) if db_profile else None

    async def get_active(self) -> list[ExpertProfileDto]:
        rows = await self.session.scalars(
            select(ExpertProfile)
            .where(ExpertProfile.status == ExpertProfileStatus.ACTIVE)
            .order_by(ExpertProfile.specialization, ExpertProfile.display_name)
        )
        return self._to_dto_list(cast(list[ExpertProfile], rows.all()))

    async def get_all(self) -> list[ExpertProfileDto]:
        rows = await self.session.scalars(
            select(ExpertProfile).order_by(ExpertProfile.created_at.desc())
        )
        return self._to_dto_list(cast(list[ExpertProfile], rows.all()))

    async def update(self, profile: ExpertProfileDto) -> ExpertProfileDto:
        if profile.id is None:
            raise ValueError("Cannot update expert profile without id")
        values = {
            key: value
            for key, value in self.retort.dump(profile).items()
            if key not in {"id", "created_at", "updated_at"}
        }
        db_profile = await self.session.scalar(
            update(ExpertProfile)
            .where(ExpertProfile.id == profile.id)
            .values(**values)
            .returning(ExpertProfile)
        )
        if not db_profile:
            raise ValueError(f"Expert profile '{profile.id}' not found")
        return self._to_dto(db_profile)

    async def update_status(
        self, profile_id: int, status: ExpertProfileStatus
    ) -> Optional[ExpertProfileDto]:
        db_profile = await self.session.scalar(
            update(ExpertProfile)
            .where(ExpertProfile.id == profile_id)
            .values(status=status)
            .returning(ExpertProfile)
        )
        return self._to_dto(db_profile) if db_profile else None

    async def get_available_plans(self, profile_id: int) -> list[PlanDto]:
        rows = await self.session.scalars(
            select(Plan)
            .join(ExpertPlan, ExpertPlan.plan_id == Plan.id)
            .where(
                ExpertPlan.expert_profile_id == profile_id,
                ExpertPlan.is_active.is_(True),
                Plan.is_active.is_(True),
                Plan.is_trial.is_(False),
            )
            .options(selectinload(Plan.durations).selectinload(PlanDuration.prices))
            .order_by(Plan.order_index)
        )
        plans = cast(list[Plan], rows.all())
        if not plans:
            fallback_rows = await self.session.scalars(
                select(Plan)
                .where(Plan.is_active.is_(True), Plan.is_trial.is_(False))
                .options(selectinload(Plan.durations).selectinload(PlanDuration.prices))
                .order_by(Plan.order_index)
            )
            plans = cast(list[Plan], fallback_rows.all())
        result = self._plans_to_dto(plans)
        duration_ids = [
            duration.id for plan in result for duration in plan.durations if duration.id is not None
        ]
        if not duration_ids:
            return result
        override_rows = await self.session.scalars(
            select(ExpertPlanPrice).where(
                ExpertPlanPrice.expert_profile_id == profile_id,
                ExpertPlanPrice.plan_duration_id.in_(duration_ids),
            )
        )
        overrides = {(row.plan_duration_id, row.currency): row.price for row in override_rows.all()}
        for plan in result:
            for duration in plan.durations:
                duration_id = duration.id
                if duration_id is None:
                    continue
                for currency in {key[1] for key in overrides if key[0] == duration_id}:
                    override = overrides[(duration_id, currency)]
                    existing = next(
                        (price for price in duration.prices if price.currency == currency), None
                    )
                    if existing:
                        existing.price = override
                    else:
                        duration.prices.append(PlanPriceDto(currency=currency, price=override))
        return result


class ConsultationDaoImpl(ConsultationDao):
    def __init__(
        self, session: AsyncSession, retort: Retort, conversion_retort: ConversionRetort
    ) -> None:
        self.session = session
        self.retort = retort
        self._to_dto = conversion_retort.get_converter(Consultation, ConsultationDto)
        self._to_dto_list = conversion_retort.get_converter(
            list[Consultation], list[ConsultationDto]
        )
        self._subscription_to_dto = conversion_retort.get_converter(
            ExpertSubscription, ExpertSubscriptionDto
        )

    async def create(self, consultation: ConsultationDto) -> ConsultationDto:
        db_consultation = Consultation(**self.retort.dump(consultation))
        self.session.add(db_consultation)
        await self.session.flush()
        return self._to_dto(db_consultation)

    async def update(self, consultation: ConsultationDto) -> ConsultationDto:
        if consultation.id is None:
            raise ValueError("Cannot update consultation without id")
        values = {
            key: value
            for key, value in self.retort.dump(consultation).items()
            if key not in {"id", "created_at", "updated_at"}
        }
        db_consultation = await self.session.scalar(
            update(Consultation)
            .where(Consultation.id == consultation.id)
            .values(**values)
            .returning(Consultation)
        )
        if not db_consultation:
            raise ValueError(f"Consultation '{consultation.id}' not found")
        return self._to_dto(db_consultation)

    async def get_by_id(self, consultation_id: int) -> Optional[ConsultationDto]:
        row = await self.session.scalar(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        return self._to_dto(row) if row else None

    async def get_by_client_and_expert(
        self, client_telegram_id: int, expert_profile_id: int
    ) -> Optional[ConsultationDto]:
        row = await self.session.scalar(
            select(Consultation).where(
                Consultation.client_telegram_id == client_telegram_id,
                Consultation.expert_profile_id == expert_profile_id,
            )
        )
        return self._to_dto(row) if row else None

    async def get_by_participant_thread(
        self, telegram_id: int, message_thread_id: int
    ) -> Optional[ConsultationDto]:
        row = await self.session.scalar(
            select(Consultation)
            .join(ExpertProfile, ExpertProfile.id == Consultation.expert_profile_id)
            .where(
                or_(
                    (
                        (Consultation.client_telegram_id == telegram_id)
                        & (Consultation.client_thread_id == message_thread_id)
                    ),
                    (
                        (ExpertProfile.user_telegram_id == telegram_id)
                        & (Consultation.expert_thread_id == message_thread_id)
                    ),
                )
            )
        )
        return self._to_dto(row) if row else None

    async def get_by_client(self, telegram_id: int) -> list[ConsultationDto]:
        rows = await self.session.scalars(
            select(Consultation)
            .where(Consultation.client_telegram_id == telegram_id)
            .order_by(Consultation.updated_at.desc())
        )
        return self._to_dto_list(cast(list[Consultation], rows.all()))

    async def get_by_expert(self, expert_profile_id: int) -> list[ConsultationDto]:
        rows = await self.session.scalars(
            select(Consultation)
            .where(Consultation.expert_profile_id == expert_profile_id)
            .order_by(Consultation.updated_at.desc())
        )
        return self._to_dto_list(cast(list[Consultation], rows.all()))

    async def get_expired_active(self, now: datetime) -> list[ConsultationDto]:
        rows = await self.session.scalars(
            select(Consultation).where(
                Consultation.status == ConsultationStatus.ACTIVE,
                Consultation.access_expires_at <= now,
            )
        )
        return self._to_dto_list(cast(list[Consultation], rows.all()))

    async def create_subscription(
        self, subscription: ExpertSubscriptionDto
    ) -> ExpertSubscriptionDto:
        db_subscription = ExpertSubscription(**self.retort.dump(subscription))
        self.session.add(db_subscription)
        await self.session.flush()
        return self._subscription_to_dto(db_subscription)

    async def subscription_exists(self, payment_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(
                    select(ExpertSubscription)
                    .where(ExpertSubscription.transaction_payment_id == payment_id)
                    .exists()
                )
            )
        )

    async def expire_subscriptions(self, consultation_id: int) -> None:
        await self.session.execute(
            update(ExpertSubscription)
            .where(
                ExpertSubscription.consultation_id == consultation_id,
                ExpertSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .values(status=SubscriptionStatus.EXPIRED)
        )

    async def activate_subscriptions(self, consultation_id: int) -> None:
        await self.session.execute(
            update(ExpertSubscription)
            .where(ExpertSubscription.consultation_id == consultation_id)
            .values(status=SubscriptionStatus.ACTIVE)
        )
