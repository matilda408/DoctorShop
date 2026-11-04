from typing import Final

from src.application.common import Interactor

from .commands import (
    CreateExpertProfile,
    EditExpertProfile,
    ExpireConsultations,
    PurchaseConsultation,
    RetryConsultationTopic,
    SetConsultationActive,
    SetExpertProfileStatus,
)
from .expert_business import (
    GetExpertStats,
    ModerateExpertApplication,
    ProcessExpertWithdrawal,
    RecordExpertEarning,
    RequestExpertWithdrawal,
    ReverseExpertEarning,
    SetExpertPrice,
    SetServiceCommission,
    SubmitExpertApplication,
)

CONSULTATION_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    PurchaseConsultation,
    CreateExpertProfile,
    EditExpertProfile,
    SetExpertProfileStatus,
    ExpireConsultations,
    RetryConsultationTopic,
    SetConsultationActive,
    SubmitExpertApplication,
    ModerateExpertApplication,
    SetExpertPrice,
    GetExpertStats,
    SetServiceCommission,
    RecordExpertEarning,
    ReverseExpertEarning,
    RequestExpertWithdrawal,
    ProcessExpertWithdrawal,
)

__all__ = ["CONSULTATION_USE_CASES"]
