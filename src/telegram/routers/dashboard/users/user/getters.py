import re
from typing import Any, Optional, Union

from adaptix import Retort
from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from remnapy import RemnawaveSDK
from remnapy.exceptions import NotFoundError

from src.application.common import TranslatorRunner
from src.application.common.dao import (
    ConsultationDao,
    ExpertDao,
    PlanDao,
    ReferralDao,
    SubscriptionDao,
    TransactionDao,
    UserDao,
)
from src.application.dto import PlanDurationDto, RemnaSubscriptionDto, SubscriptionDto, UserDto
from src.application.use_cases.statistics.queries.users import GetUserStatistics
from src.application.use_cases.user.queries.plans import GetAvailablePlans
from src.application.use_cases.user.queries.profile import (
    GetUserProfile,
    GetUserProfileSubscription,
)
from src.core.config import AppConfig
from src.core.constants import DATETIME_FORMAT, TARGET_TELEGRAM_ID
from src.core.enums import PlanAvailability, Role
from src.core.types import RemnaUserDto
from src.core.utils.i18n_helpers import (
    i18n_format_days,
    i18n_format_expire_time,
)

CUSTOM_EMOJI_PATTERN = re.compile(
    r'<tg-emoji\s+emoji-id=["\'](?P<id>\d+)["\'][^>]*>.*?</tg-emoji>',
    re.DOTALL,
)


def format_plan_name(name: str) -> str:
    return " ".join(CUSTOM_EMOJI_PATTERN.sub("", name).split())


async def format_discount_plan(
    plan_id: int | None,
    i18n: TranslatorRunner,
    plan_dao: PlanDao,
) -> str:
    if not plan_id:
        return "все тарифы"

    plan = await plan_dao.get_by_id(plan_id)
    return format_plan_name(i18n.get(plan.name)) if plan else "тариф удален"


@inject
async def user_getter(
    dialog_manager: DialogManager,
    user: UserDto,
    i18n: FromDishka[TranslatorRunner],
    plan_dao: FromDishka[PlanDao],
    get_user_profile: FromDishka[GetUserProfile],
    expert_dao: FromDishka[ExpertDao],
    consultation_dao: FromDishka[ConsultationDao],
    transaction_dao: FromDishka[TransactionDao],
    config: AppConfig,
    **kwargs: Any,
) -> dict[str, Any]:
    dialog_manager.dialog_data.pop("payload", None)
    target_telegram_id: int = dialog_manager.start_data[TARGET_TELEGRAM_ID]  # type: ignore[call-overload, index, assignment]
    dialog_manager.dialog_data[TARGET_TELEGRAM_ID] = target_telegram_id
    profile = await get_user_profile(user, target_telegram_id)
    personal_discount_plan = await format_discount_plan(
        profile.target_user.personal_discount_plan_id,
        i18n,
        plan_dao,
    )
    purchase_discount_plan = await format_discount_plan(
        profile.target_user.purchase_discount_plan_id,
        i18n,
        plan_dao,
    )
    expert_profile = await expert_dao.get_by_user(profile.target_user.telegram_id)
    client_consultations = await consultation_dao.get_by_client(profile.target_user.telegram_id)
    expert_consultations = (
        await consultation_dao.get_by_expert(expert_profile.id)
        if expert_profile and expert_profile.id is not None
        else []
    )
    selected_experts = []
    for consultation in client_consultations:
        selected_expert = await expert_dao.get_by_id(consultation.expert_profile_id)
        selected_experts.append(
            selected_expert.display_name
            if selected_expert
            else f"#{consultation.expert_profile_id}"
        )
    expert_transactions = (
        await transaction_dao.get_by_expert(expert_profile.id)
        if expert_profile and expert_profile.id is not None
        else []
    )

    data: dict[str, Any] = {
        "telegram_id": profile.target_user.telegram_id,
        "username": profile.target_user.username or False,
        "name": profile.target_user.name,
        "phone": profile.target_user.phone or False,
        "role": profile.target_user.role,
        "language": profile.target_user.language,
        "show_points": profile.show_points,
        "points": profile.target_user.points,
        "personal_discount": profile.target_user.personal_discount,
        "personal_discount_plan": personal_discount_plan,
        "purchase_discount": profile.target_user.purchase_discount,
        "purchase_discount_plan": purchase_discount_plan,
        "is_blocked": profile.target_user.is_blocked,
        "is_bot_blocked": profile.target_user.is_bot_blocked,
        "is_trial_available": profile.target_user.is_trial_available,
        "is_not_self": profile.target_user.telegram_id != user.telegram_id,
        "can_edit": profile.can_edit,
        "status": None,
        "is_trial": False,
        "has_subscription": profile.subscription is not None,
        "is_expert": expert_profile is not None,
        "expert_status": expert_profile.status if expert_profile else None,
        "expert_active": expert_profile.is_available if expert_profile else False,
        "expert_profile_id": expert_profile.id if expert_profile else None,
        "client_consultations_count": len(client_consultations),
        "client_active_consultations_count": sum(
            consultation.is_active for consultation in client_consultations
        ),
        "selected_experts": ", ".join(selected_experts) or "—",
        "expert_clients_count": len(
            {consultation.client_telegram_id for consultation in expert_consultations}
        ),
        "expert_active_consultations_count": sum(
            consultation.is_active for consultation in expert_consultations
        ),
        "expert_completed_consultations_count": sum(
            not consultation.is_active for consultation in expert_consultations
        ),
        "expert_payments_count": len(expert_transactions),
        "legacy_vpn_enabled": config.legacy_vpn_enabled,
    }

    if profile.subscription:
        data.update(
            {
                "status": profile.subscription.current_status,
                "is_trial": profile.subscription.is_trial,
                "expire_time": i18n_format_expire_time(profile.subscription.expire_at),
            }
        )

    return data


@inject
async def subscription_getter(
    dialog_manager: DialogManager,
    user: UserDto,
    get_user_profile_subscription: FromDishka[GetUserProfileSubscription],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]

    user_profile_subscription = await get_user_profile_subscription(user, target_telegram_id)

    subscription = user_profile_subscription.subscription
    remna_user = user_profile_subscription.remna_user

    return {
        "is_trial": subscription.is_trial,
        "is_active": subscription.is_active,
        "url": remna_user.subscription_url,
        "subscription_id": subscription.user_remna_id,
        "subscription_status": subscription.current_status,
        "expire_time": i18n_format_expire_time(subscription.expire_at),
        "is_trial_plan": subscription.plan_snapshot.is_trial,
        "plan_name": subscription.plan_snapshot.name,
        "plan_duration": i18n_format_days(subscription.plan_snapshot.duration),
        "can_edit": user_profile_subscription.can_edit,
    }


@inject
async def discount_getter(
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    plan_dao: FromDishka[PlanDao],
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    if "personal_discount_plan_id" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["personal_discount_plan_id"] = (
            target_user.personal_discount_plan_id
        )
    if "purchase_discount_plan_id" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["purchase_discount_plan_id"] = (
            target_user.purchase_discount_plan_id
        )

    selected_personal_plan_id = dialog_manager.dialog_data.get("personal_discount_plan_id")
    selected_purchase_plan_id = dialog_manager.dialog_data.get("purchase_discount_plan_id")
    active_plans = await plan_dao.get_active_plans()
    personal_discount_plans = [
        {
            "id": 0,
            "name": f"{'🔘' if selected_personal_plan_id is None else '⚪'} Все тарифы",
        }
    ]
    purchase_discount_plans = [
        {
            "id": 0,
            "name": f"{'🔘' if selected_purchase_plan_id is None else '⚪'} Все тарифы",
        }
    ]

    for plan in active_plans:
        plan_name = format_plan_name(i18n.get(plan.name))
        personal_discount_plans.append(
            {
                "id": plan.id,
                "name": (f"{'🔘' if selected_personal_plan_id == plan.id else '⚪'} {plan_name}"),
            }
        )
        purchase_discount_plans.append(
            {
                "id": plan.id,
                "name": (f"{'🔘' if selected_purchase_plan_id == plan.id else '⚪'} {plan_name}"),
            }
        )

    return {
        "percentages": [0, 5, 10, 25, 40, 50, 70, 80, 100],
        "personal_discount_plans": personal_discount_plans,
        "purchase_discount_plans": purchase_discount_plans,
    }


@inject
async def points_getter(
    dialog_manager: DialogManager,
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    formatted_points = [
        {
            "operation": "+" if value > 0 else "",
            "points": value,
        }
        for value in [5, -5, 25, -25, 50, -50, 100, -100]
    ]

    return {
        "current_points": target_user.points,
        "points": formatted_points,
    }


@inject
async def expire_time_getter(
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    subscription_dao: FromDishka[SubscriptionDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    subscription = await subscription_dao.get_current(target_telegram_id)

    if not subscription:
        raise ValueError(f"Current subscription for user '{target_telegram_id}' not found")

    formatted_durations = []
    for value in [1, -1, 3, -3, 7, -7, 14, -14, 30, -30]:
        key, kw = i18n_format_days(value)
        key2, kw2 = i18n_format_days(-value)
        formatted_durations.append(
            {
                "operation": "+" if value > 0 else "-",
                "duration": i18n.get(key, **kw) if value > 0 else i18n.get(key2, **kw2),
                "days": value,
            }
        )

    return {
        "expire_time": i18n_format_expire_time(subscription.expire_at),
        "durations": formatted_durations,
    }


@inject
async def statistics_getter(
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    get_user_statistics: FromDishka[GetUserStatistics],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    data = await get_user_statistics.system(target_telegram_id)

    payment_amounts = (
        "\n".join(
            i18n.get(
                "msg-user-statistics-payment-amount",
                currency=p.currency,
                amount=p.total_amount,
            )
            for p in data.payment_amounts
        )
        or False
    )

    return {
        "has_referrals": data.referrals_level_1 > 0,
        "last_payment_at": data.last_payment_at or 0,
        "payment_amounts": payment_amounts,
        "registered_at": data.registered_at,
        "referrer_telegram_id": data.referrer_telegram_id or 0,
        "referrer_username": data.referrer_username or 0,
        "referrals_level_1": data.referrals_level_1,
        "referrals_level_2": data.referrals_level_2,
        "reward_points": data.reward_points,
        "reward_days": data.reward_days,
    }


@inject
async def referrals_getter(
    dialog_manager: DialogManager,
    referral_dao: FromDishka[ReferralDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    referrals = await referral_dao.get_referrals_list(referrer_id=target_telegram_id, limit=100)

    return {
        "referrals": [
            {
                "telegram_id": r.referred.telegram_id,
                "name": r.referred.name,
            }
            for r in referrals
        ]
    }


@inject
async def transactions_getter(
    dialog_manager: DialogManager,
    transaction_dao: FromDishka[TransactionDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    transactions = await transaction_dao.get_by_user(target_telegram_id)

    if not transactions:
        raise ValueError(f"Transactions not found for user '{target_telegram_id}'")

    formatted_transactions = [
        {
            "payment_id": transaction.payment_id,
            "status": transaction.status,
            "created_at": transaction.created_at.strftime(DATETIME_FORMAT),  # type: ignore[union-attr]
        }
        for transaction in transactions
    ]

    return {"transactions": formatted_transactions}


@inject
async def transaction_getter(
    dialog_manager: DialogManager,
    transaction_dao: FromDishka[TransactionDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    selected_transaction = dialog_manager.dialog_data["selected_transaction"]
    transaction = await transaction_dao.get_by_payment_id(selected_transaction)

    if not transaction:
        raise ValueError(
            f"Transaction '{selected_transaction}' not found for user '{target_telegram_id}'"
        )

    return {
        "is_test": transaction.is_test,
        "is_trial_plan": transaction.plan_snapshot.is_trial,
        "payment_id": transaction.payment_id,
        "purchase_type": transaction.purchase_type,
        "transaction_status": transaction.status,
        "gateway_type": transaction.gateway_type,
        "final_amount": transaction.pricing.final_amount,
        "currency": transaction.currency.symbol,
        "discount_percent": transaction.pricing.discount_percent,
        "original_amount": transaction.pricing.original_amount,
        "created_at": transaction.created_at.strftime(DATETIME_FORMAT),  # type: ignore[union-attr]
        "plan_name": transaction.plan_snapshot.name,
        "plan_duration": i18n_format_days(transaction.plan_snapshot.duration),
    }


@inject
async def give_access_getter(
    dialog_manager: DialogManager,
    plan_dao: FromDishka[PlanDao],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    plans = await plan_dao.filter_by_availability(PlanAvailability.ALLOWED)

    if not plans:
        raise ValueError("Allowed plans not found")

    formatted_plans = [
        {
            "plan_name": i18n.get(plan.name),
            "plan_id": plan.id,
            "selected": True if target_telegram_id in plan.allowed_user_ids else False,
        }
        for plan in plans
    ]

    return {"plans": formatted_plans}


@inject
async def give_subscription_getter(
    dialog_manager: DialogManager,
    user_dao: FromDishka[UserDao],
    i18n: FromDishka[TranslatorRunner],
    get_available_plans: FromDishka[GetAvailablePlans],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    plans = await get_available_plans.system(target_user)

    if not plans:
        raise ValueError("Available plans not found")

    formatted_plans = [
        {
            "plan_name": i18n.get(plan.name),
            "plan_id": plan.id,
        }
        for plan in plans
    ]

    return {"plans": formatted_plans}


@inject
async def subscription_duration_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    plan_dao: FromDishka[PlanDao],
    **kwargs: Any,
) -> dict[str, Any]:
    selected_plan_id = dialog_manager.dialog_data["selected_plan_id"]
    plan = await plan_dao.get_by_id(selected_plan_id)

    if not plan:
        raise ValueError(f"Plan '{selected_plan_id}' not found")

    return {"durations": retort.dump(plan.durations, list[PlanDurationDto])}


@inject
async def role_getter(
    dialog_manager: DialogManager,
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    roles = [
        role
        for role in Role
        if role != target_user.role and role not in [Role.SYSTEM, Role.OWNER, Role.PREVIEW]
    ]
    return {"roles": roles[::-1]}


@inject
async def sync_getter(  # noqa: C901
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    remnawave_sdk: FromDishka[RemnawaveSDK],
    **kwargs: Any,
) -> dict[str, Any]:
    target_telegram_id = dialog_manager.dialog_data[TARGET_TELEGRAM_ID]
    target_user = await user_dao.get_by_telegram_id(target_telegram_id)

    if not target_user:
        raise ValueError(f"User '{target_telegram_id}' not found")

    bot_sub = await subscription_dao.get_current(target_telegram_id)
    remna_sub: Optional[RemnaSubscriptionDto] = None
    remna_updated_at = None

    try:
        result = await remnawave_sdk.users.get_users_by_telegram_id(
            telegram_id=str(target_telegram_id)
        )
        if result:
            remna_user: RemnaUserDto = result[0]
            remna_sub = RemnaSubscriptionDto.from_remna_user(remna_user)
            remna_updated_at = remna_user.updated_at
    except NotFoundError:
        pass

    def format_subscription(sub: Union[None, SubscriptionDto, RemnaSubscriptionDto]) -> str:
        if not sub:
            return ""

        sub_id = str(getattr(sub, "user_remna_id", getattr(sub, "uuid", "")))

        kwargs = {
            "id": sub_id,
            "status": sub.status,
            "url": sub.url,
            "expire_time": i18n_format_expire_time(sub.expire_at),
            "tag": sub.tag or False,
        }
        return i18n.get("msg-user-sync-subscription", **kwargs)

    bot_version_key = "UNKNOWN"
    remna_version_key = "UNKNOWN"

    if bot_sub and remna_sub:
        if bot_sub.updated_at > remna_updated_at:  # type: ignore[operator]
            bot_version_key, remna_version_key = "NEWER", "OLDER"
        elif bot_sub.updated_at < remna_updated_at:  # type: ignore[operator]
            bot_version_key, remna_version_key = "OLDER", "NEWER"

    return {
        "has_bot_subscription": bool(bot_sub),
        "has_remna_subscription": bool(remna_sub),
        "bot_version": i18n.get("msg-user-sync-version", version=bot_version_key),
        "remna_version": i18n.get("msg-user-sync-version", version=remna_version_key),
        "bot_subscription": format_subscription(bot_sub),
        "remna_subscription": format_subscription(remna_sub),
    }
