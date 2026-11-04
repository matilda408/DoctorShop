from typing import Final

from src.application.common import Interactor

from .commands.synchronization import SyncRemnaUser

REMNAWAVE_USE_CASES: Final[tuple[type[Interactor], ...]] = (SyncRemnaUser,)
