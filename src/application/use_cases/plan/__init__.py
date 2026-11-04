from typing import Final

from src.application.common import Interactor

from .commands.access import AddAllowedUserToPlan, ToggleUserPlanAccess
from .commands.commit import CommitPlan
from .commands.durations import AddPlanDuration, RemovePlanDuration
from .commands.edit import (
    UpdatePlanDescription,
    UpdatePlanName,
    UpdatePlanPrice,
    UpdatePlanTag,
)
from .commands.order import DeletePlan, MoveDurationUp, MovePlanUp
from .exchange import ExportPlans, ParsePlansImport
from .queries.match import MatchPlan

PLAN_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    AddAllowedUserToPlan,
    AddPlanDuration,
    CommitPlan,
    DeletePlan,
    MovePlanUp,
    RemovePlanDuration,
    UpdatePlanDescription,
    UpdatePlanName,
    UpdatePlanPrice,
    UpdatePlanTag,
    ParsePlansImport,
    ExportPlans,
    MatchPlan,
    ToggleUserPlanAccess,
    MoveDurationUp,
)
