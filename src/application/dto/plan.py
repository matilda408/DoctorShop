from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Self

from src.core.enums import Currency, PlanAvailability

from .base import BaseDto, TimestampMixin, TrackableMixin


@dataclass(kw_only=True)
class PlanSnapshotDto:
    id: int

    name: str
    tag: Optional[str] = None

    duration: int

    is_trial: bool = False

    @classmethod
    def from_plan(cls, plan: "PlanDto", duration: int) -> Self:
        return cls(
            id=plan.id,  # type: ignore[arg-type]
            name=plan.name,
            tag=plan.tag,
            duration=duration,
            is_trial=plan.is_trial,
        )

    @classmethod
    def test(cls) -> "PlanSnapshotDto":
        return cls(
            id=-1,
            name="test",
            tag=None,
            duration=0,
        )


@dataclass(kw_only=True)
class PlanDto(BaseDto, TrackableMixin, TimestampMixin):
    public_code: Optional[str] = None
    name: str = "Default Plan"
    description: Optional[str] = None
    tag: Optional[str] = None

    availability: PlanAvailability = PlanAvailability.ALL

    allowed_user_ids: list[int] = field(default_factory=list)

    order_index: int = 0
    is_active: bool = False
    is_trial: bool = False

    durations: list["PlanDurationDto"] = field(default_factory=list)

    def get_duration(self, days: int) -> Optional["PlanDurationDto"]:
        return next((d for d in self.durations if d.days == days), None)


@dataclass(kw_only=True)
class PlanDurationDto(BaseDto, TrackableMixin):
    days: int
    order_index: int = 0
    prices: list["PlanPriceDto"] = field(default_factory=list)

    def get_price(self, currency: Currency) -> Decimal:
        return next((p.price for p in self.prices if p.currency == currency))


@dataclass(kw_only=True)
class PlanPriceDto(BaseDto, TrackableMixin):
    currency: Currency
    price: Decimal
