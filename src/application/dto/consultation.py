from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.core.enums import ConsultationStatus, ExpertProfileStatus, SubscriptionStatus
from src.core.utils.time import datetime_now

from .base import BaseDto, TimestampMixin, TrackableMixin
from .plan import PlanSnapshotDto


@dataclass(kw_only=True)
class ExpertProfileDto(BaseDto, TrackableMixin, TimestampMixin):
    user_telegram_id: int
    display_name: str
    specialization: str
    short_description: str = ""
    description: str = ""
    experience_years: int = 0
    photo_file_id: Optional[str] = None
    status: ExpertProfileStatus = ExpertProfileStatus.DRAFT

    @property
    def is_available(self) -> bool:
        return self.status == ExpertProfileStatus.ACTIVE


@dataclass(kw_only=True)
class ConsultationDto(BaseDto, TrackableMixin, TimestampMixin):
    client_telegram_id: int
    expert_profile_id: int
    client_thread_id: Optional[int]
    expert_thread_id: Optional[int]
    status: ConsultationStatus
    access_expires_at: datetime
    last_message_at: Optional[datetime] = None
    creation_error: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.status == ConsultationStatus.ACTIVE and self.access_expires_at > datetime_now()


@dataclass(kw_only=True)
class ExpertSubscriptionDto(BaseDto, TrackableMixin, TimestampMixin):
    client_telegram_id: int
    expert_profile_id: int
    consultation_id: int
    transaction_payment_id: UUID
    status: SubscriptionStatus
    starts_at: datetime
    expires_at: datetime
    plan_snapshot: PlanSnapshotDto
