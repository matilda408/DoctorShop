from typing import Optional, Protocol

from src.core.enums import PurchaseType


class Redirect(Protocol):
    async def to_main_menu(self, telegram_id: int) -> None: ...

    async def to_user_editor(self, telegram_id: int, target_telegram_id: int) -> None: ...

    async def to_success_trial(self, telegram_id: int) -> None: ...

    async def to_success_payment(
        self,
        telegram_id: int,
        purchase_type: PurchaseType,
        expert_profile_id: Optional[int] = None,
    ) -> None: ...

    async def to_failed_payment(self, telegram_id: int) -> None: ...
