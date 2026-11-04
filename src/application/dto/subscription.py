from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.core.enums import SubscriptionStatus
from src.core.types import RemnaUserDto
from src.core.utils.time import datetime_now

from .base import BaseDto, TimestampMixin, TrackableMixin
from .plan import PlanSnapshotDto


@dataclass(kw_only=True)
class RemnaSubscriptionDto:
    uuid: UUID
    status: SubscriptionStatus
    expire_at: datetime
    url: str

    tag: Optional[str] = None

    @classmethod
    def from_remna_user(cls, remna_user: RemnaUserDto) -> "RemnaSubscriptionDto":
        return cls(
            uuid=remna_user.uuid,
            status=SubscriptionStatus(remna_user.status),
            expire_at=remna_user.expire_at,
            url=remna_user.subscription_url,
            tag=remna_user.tag,
        )


@dataclass(kw_only=True)
class SubscriptionDto(BaseDto, TrackableMixin, TimestampMixin):
    user_remna_id: UUID

    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    is_trial: bool = False

    tag: Optional[str] = None

    expire_at: datetime
    url: str

    plan_snapshot: "PlanSnapshotDto"

    @property
    def is_active(self) -> bool:
        return self.current_status == SubscriptionStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        return self.current_status == SubscriptionStatus.EXPIRED

    @property
    def is_unlimited(self) -> bool:
        return self.expire_at.year == 2099

    @property
    def current_status(self) -> SubscriptionStatus:
        if datetime_now() > self.expire_at:
            return SubscriptionStatus.EXPIRED
        return self.status
