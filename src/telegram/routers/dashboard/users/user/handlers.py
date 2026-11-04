from typing import Union
from uuid import UUID

from adaptix import Retort
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import Notifier, Redirect
from src.application.common.dao import ExpertDao, PlanDao, SubscriptionDao, TransactionDao, UserDao
from src.application.dto import MessagePayloadDto, UserDto
from src.application.use_cases.consultation.commands import (
    SetExpertProfileStatus,
    SetExpertProfileStatusDto,
)
from src.application.use_cases.plan.commands.access import (
    ToggleUserPlanAccess,
    ToggleUserPlanAccessDto,
)
from src.application.use_cases.subscription.commands.management import (
    AddSubscriptionDuration,
    AddSubscriptionDurationDto,
    DeleteSubscription,
    ToggleSubscriptionStatus,
)
from src.application.use_cases.subscription.commands.set_plan import (
    SetUserSubscription,
    SetUserSubscriptionDto,
)
from src.application.use_cases.subscription.commands.sync import (
    CheckSubscriptionSyncState,
    SyncSubscriptionFromRemnashop,
    SyncSubscriptionFromRemnawave,
)
from src.application.use_cases.user.commands.blocking import ToggleUserBlockedStatus
from src.application.use_cases.user.commands.messaging import (
    SendMessageToUser,
    SendMessageToUserDto,
)
from src.application.use_cases.user.commands.profile_edit import (
    ChangeUserPoints,
    ChangeUserPointsDto,
    SetUserPersonalDiscount,
    SetUserPersonalDiscountDto,
    SetUserPurchaseDiscount,
    SetUserPurchaseDiscountDto,
    ToggleUserTrialAvailable,
)
from src.application.use_cases.user.commands.roles import SetUserRole, SetUserRoleDto
from src.application.use_cases.user.queries.plans import GetAvailablePlans
from src.core.constants import TARGET_TELEGRAM_ID, USER_KEY
from src.core.enums import ExpertProfileStatus, Role
from src.core.utils.validators import parse_int
from src.telegram.states import DashboardUser
from src.telegram.utils import is_double_click


async def start_user_window(
    manager: Union[DialogManager, DialogManager],
    target_telegram_id: int,
) -> None:
    await manager.start(
        state=DashboardUser.MAIN,
        data={"target_telegram_id": target_telegram_id},
        mode=StartMode.RESET_STACK,
    )


async def on_user_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_user: int,
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.info(f"{user.log} User id '{selected_user}' selected")
    await start_user_window(manager=dialog_manager, target_telegram_id=selected_user)


@inject
async def on_block_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    toggle_user_blocked_status: FromDishka[ToggleUserBlockedStatus],
    redirect: FromDishka[Redirect],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await toggle_user_blocked_status(user, target_telegram_id)
    await redirect.to_main_menu(target_telegram_id)


@inject
async def on_trial_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    toggle_user_trial_available: FromDishka[ToggleUserTrialAvailable],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await toggle_user_trial_available(user, target_telegram_id)


@inject
async def on_expert_profile_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    set_expert_profile_status: FromDishka[SetExpertProfileStatus],
) -> None:
    actor: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    profile = await expert_dao.get_by_user(target_telegram_id)
    if not profile or profile.id is None:
        raise ValueError("Expert profile not found")
    status = ExpertProfileStatus.DISABLED if profile.is_available else ExpertProfileStatus.ACTIVE
    await set_expert_profile_status(
        actor,
        SetExpertProfileStatusDto(expert_profile_id=profile.id, status=status),
    )


@inject
async def on_role_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_role: Role,
    set_user_role: FromDishka[SetUserRole],
    redirect: FromDishka[Redirect],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await set_user_role(user, SetUserRoleDto(target_telegram_id, Role(selected_role)))
    await redirect.to_main_menu(target_telegram_id)


@inject
async def on_current_subscription(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    subscription_dao: FromDishka[SubscriptionDao],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    subscription = await subscription_dao.get_current(target_telegram_id)

    if not subscription:
        await notifier.notify_user(user, i18n_key="ntf-user.subscription-empty")
        return

    await dialog_manager.switch_to(state=DashboardUser.SUBSCRIPTION)


@inject
async def on_active_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    toggle_subscription_status: FromDishka[ToggleSubscriptionStatus],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await toggle_subscription_status(user, target_telegram_id)


@inject
async def on_subscription_delete(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    delete_subscription: FromDishka[DeleteSubscription],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    if is_double_click(dialog_manager, key="subscription_delete_confirm", cooldown=10):
        await delete_subscription(user, target_telegram_id)

        await notifier.notify_user(user, i18n_key="ntf-user.subscription-deleted")
        await dialog_manager.switch_to(state=DashboardUser.MAIN)
        return

    await notifier.notify_user(user, i18n_key="ntf-common.double-click-confirm")
    logger.debug(
        f"{user.log} Waiting for confirmation to delete subscription for '{target_telegram_id}'"
    )


@inject
async def on_personal_discount_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_discount: int,
    set_user_personal_discount: FromDishka[SetUserPersonalDiscount],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    selected_plan_id = dialog_manager.dialog_data.get("personal_discount_plan_id")

    await set_user_personal_discount(
        user,
        SetUserPersonalDiscountDto(
            target_telegram_id,
            selected_discount,
            plan_id=selected_plan_id,
        ),
    )
    dialog_manager.dialog_data["personal_discount_plan_id"] = (
        selected_plan_id if selected_discount > 0 else None
    )

    await dialog_manager.switch_to(state=DashboardUser.DISCOUNT)


async def on_personal_discount_plan_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_plan_id: int,
) -> None:
    dialog_manager.dialog_data["personal_discount_plan_id"] = selected_plan_id or None
    await dialog_manager.switch_to(state=DashboardUser.PERSONAL_DISCOUNT)


async def on_purchase_discount_plan_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_plan_id: int,
) -> None:
    dialog_manager.dialog_data["purchase_discount_plan_id"] = selected_plan_id or None
    await dialog_manager.switch_to(state=DashboardUser.PURCHASE_DISCOUNT)


@inject
async def on_personal_discount_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    set_user_personal_discount: FromDishka[SetUserPersonalDiscount],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    selected_plan_id = dialog_manager.dialog_data.get("personal_discount_plan_id")

    if not message.text or not message.text.isdigit():
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return

    discount = int(message.text)

    try:
        await set_user_personal_discount(
            user,
            SetUserPersonalDiscountDto(
                target_telegram_id,
                discount=discount,
                plan_id=selected_plan_id,
            ),
        )
        dialog_manager.dialog_data["personal_discount_plan_id"] = (
            selected_plan_id if discount > 0 else None
        )
        await dialog_manager.switch_to(state=DashboardUser.DISCOUNT)
    except ValueError:
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")


@inject
async def on_purchase_discount_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_discount: int,
    set_user_purchase_discount: FromDishka[SetUserPurchaseDiscount],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    selected_plan_id = dialog_manager.dialog_data.get("purchase_discount_plan_id")

    await set_user_purchase_discount(
        user,
        SetUserPurchaseDiscountDto(
            target_telegram_id,
            selected_discount,
            plan_id=selected_plan_id,
        ),
    )
    dialog_manager.dialog_data["purchase_discount_plan_id"] = (
        selected_plan_id if selected_discount > 0 else None
    )

    await dialog_manager.switch_to(state=DashboardUser.DISCOUNT)


@inject
async def on_purchase_discount_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    set_user_purchase_discount: FromDishka[SetUserPurchaseDiscount],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    selected_plan_id = dialog_manager.dialog_data.get("purchase_discount_plan_id")

    if not message.text or not message.text.isdigit():
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return

    discount = int(message.text)

    try:
        await set_user_purchase_discount(
            user,
            SetUserPurchaseDiscountDto(
                target_telegram_id,
                discount=discount,
                plan_id=selected_plan_id,
            ),
        )
        dialog_manager.dialog_data["purchase_discount_plan_id"] = (
            selected_plan_id if discount > 0 else None
        )
        await dialog_manager.switch_to(state=DashboardUser.DISCOUNT)
    except ValueError:
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")


@inject
async def on_points_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    change_user_points: FromDishka[ChangeUserPoints],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    number = parse_int(message.text)

    if number is None:
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return

    try:
        await change_user_points(user, ChangeUserPointsDto(target_telegram_id, number))
    except ValueError:
        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="ntf-user.invalid-points",
                i18n_kwargs={"operation": "ADD" if number > 0 else "SUB"},
            ),
        )


@inject
async def on_points_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_points: int,
    notifier: FromDishka[Notifier],
    change_user_points: FromDishka[ChangeUserPoints],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.info(f"{user.log} Selected points '{selected_points}'")
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    try:
        await change_user_points(user, ChangeUserPointsDto(target_telegram_id, selected_points))
    except ValueError:
        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="ntf-user.invalid-points",
                i18n_kwargs={"operation": "ADD" if selected_points > 0 else "SUB"},
            ),
        )


@inject
async def on_transactions(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    transaction_dao: FromDishka[TransactionDao],
    notifier: FromDishka[Notifier],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    transactions = await transaction_dao.get_by_user(target_telegram_id)

    if not transactions:
        await notifier.notify_user(user, i18n_key="ntf-user.transactions-empty")
        return

    await dialog_manager.switch_to(state=DashboardUser.TRANSACTIONS_LIST)


async def on_transaction_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_transaction: UUID,
) -> None:
    dialog_manager.dialog_data["selected_transaction"] = selected_transaction
    await dialog_manager.switch_to(state=DashboardUser.TRANSACTION)


@inject
async def on_give_access(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    plan_dao: FromDishka[PlanDao],
    notifier: FromDishka[Notifier],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    plans = await plan_dao.get_active_allowed_plans()

    if not plans:
        await notifier.notify_user(user, i18n_key="ntf-user.allowed-plans-empty")
        return

    await dialog_manager.switch_to(state=DashboardUser.GIVE_ACCESS)


@inject
async def on_plan_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_plan_id: int,
    toggle_access: FromDishka[ToggleUserPlanAccess],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.info(f"{user.log} Selected plan '{selected_plan_id}'")
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await toggle_access(
        user, ToggleUserPlanAccessDto(plan_id=selected_plan_id, telegram_id=target_telegram_id)
    )


@inject
async def on_duration_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_duration: int,
    notifier: FromDishka[Notifier],
    add_subscription_duration: FromDishka[AddSubscriptionDuration],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    try:
        await add_subscription_duration(
            user,
            AddSubscriptionDurationDto(target_telegram_id, selected_duration),
        )
    except ValueError:
        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="ntf-user.invalid-expire-time",
                i18n_kwargs={"operation": "ADD" if selected_duration > 0 else "SUB"},
            ),
        )


@inject
async def on_duration_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    add_subscription_duration: FromDishka[AddSubscriptionDuration],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    number = parse_int(message.text)
    if number is None:
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return

    try:
        await add_subscription_duration(
            user,
            AddSubscriptionDurationDto(target_telegram_id, number),
        )
    except ValueError:
        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="ntf-user.invalid-expire-time",
                i18n_kwargs={"operation": "ADD" if number > 0 else "SUB"},
            ),
        )


@inject
async def on_send(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    notifier: FromDishka[Notifier],
    send_message_to_user: FromDishka[SendMessageToUser],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    payload = dialog_manager.dialog_data.get("payload")

    if not payload:
        await notifier.notify_user(user, i18n_key="ntf-broadcast.content-empty")
        return

    payload = retort.load(payload, MessagePayloadDto)

    if is_double_click(dialog_manager, key="message_confirm", cooldown=5):
        success = await send_message_to_user(
            user,
            SendMessageToUserDto(target_telegram_id, payload),
        )

        await dialog_manager.switch_to(state=DashboardUser.MAIN)

        i18n_key = "ntf-user.message-success" if success else "ntf-user.message-failed"
        await notifier.notify_user(user, i18n_key=i18n_key)
        return

    await notifier.notify_user(user, i18n_key="ntf-common.double-click-confirm")
    logger.debug(f"{user.log} Awaiting confirmation for message send")


@inject
async def on_sync(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    check_subscription_sync_state: FromDishka[CheckSubscriptionSyncState],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    try:
        needs_sync = await check_subscription_sync_state(user, target_telegram_id)

        if not needs_sync:
            await notifier.notify_user(user, i18n_key="ntf-user.sync-already")
            return

        await dialog_manager.switch_to(state=DashboardUser.SYNC)

    except ValueError:
        await notifier.notify_user(user, i18n_key="ntf-user.sync-missing-data")


@inject
async def on_sync_from_remnawave(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    sync_subscription_from_remnawave: FromDishka[SyncSubscriptionFromRemnawave],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await sync_subscription_from_remnawave(user, target_telegram_id)
    await notifier.notify_user(user, i18n_key="ntf-user.sync-success")
    await dialog_manager.switch_to(state=DashboardUser.MAIN)


@inject
async def on_sync_from_remnashop(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    sync_subscription_from_remnashop: FromDishka[SyncSubscriptionFromRemnashop],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    await sync_subscription_from_remnashop(user, target_telegram_id)
    await notifier.notify_user(user, i18n_key="ntf-user.sync-success")
    await dialog_manager.switch_to(state=DashboardUser.MAIN)


@inject
async def on_give_subscription(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    user_dao: FromDishka[UserDao],
    get_available_plans: FromDishka[GetAvailablePlans],
    notifier: FromDishka[Notifier],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    plans = await get_available_plans.system(target_user)

    if not plans:
        await notifier.notify_user(user, i18n_key="ntf-user.plans-empty")
        return

    await dialog_manager.switch_to(state=DashboardUser.GIVE_SUBSCRIPTION)


@inject
async def on_subscription_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_plan_id: int,
) -> None:
    dialog_manager.dialog_data["selected_plan_id"] = selected_plan_id
    await dialog_manager.switch_to(state=DashboardUser.SUBSCRIPTION_DURATION)


@inject
async def on_subscription_duration_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_duration: int,
    set_user_subscription: FromDishka[SetUserSubscription],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    plan_id = dialog_manager.dialog_data["selected_plan_id"]
    await set_user_subscription(
        user,
        SetUserSubscriptionDto(target_telegram_id, plan_id, selected_duration),
    )
    await dialog_manager.switch_to(state=DashboardUser.MAIN)
