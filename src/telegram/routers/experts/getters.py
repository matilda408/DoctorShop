from typing import Any

from aiogram.types import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common.dao import ConsultationDao, ExpertDao, UserDao
from src.application.dto import UserDto
from src.application.use_cases.consultation.expert_business import GetExpertStats
from src.core.constants import USER_KEY
from src.core.enums import Currency, ExpertProfileStatus
from src.core.exceptions import PermissionDeniedError
from src.core.payment_policy import NEW_PLAN_CURRENCIES
from src.core.utils.i18n_helpers import i18n_format_expire_time


@inject
async def catalog_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    experts = await expert_dao.get_active()
    return {
        "experts": [
            {
                "id": profile.id,
                "name": profile.display_name,
                "specialization": profile.specialization,
            }
            for profile in experts
        ],
        "has_experts": bool(experts),
    }


@inject
async def expert_details_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    profile_id = int(dialog_manager.dialog_data["expert_profile_id"])
    profile = await expert_dao.get_by_id(profile_id)
    if not profile or not profile.is_available:
        raise ValueError("Expert profile is not available")
    plans = await expert_dao.get_available_plans(profile_id)
    return {
        "name": profile.display_name,
        "specialization": profile.specialization,
        "short_description": profile.short_description,
        "description": profile.description,
        "experience_years": profile.experience_years,
        "expert_photo": (
            MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(profile.photo_file_id),
            )
            if profile.photo_file_id
            else None
        ),
        "has_expert_photo": bool(profile.photo_file_id),
        "has_plans": bool(plans),
    }


async def _format_consultations(
    consultations: list,
    expert_dao: ExpertDao,
    user_dao: UserDao,
    *,
    show_client: bool,
) -> list[dict[str, Any]]:
    result = []
    for consultation in consultations:
        profile = await expert_dao.get_by_id(consultation.expert_profile_id)
        client = await user_dao.get_by_telegram_id(consultation.client_telegram_id)
        label = (
            f"{client.name if client else consultation.client_telegram_id}"
            if show_client
            else f"{profile.display_name if profile else consultation.expert_profile_id}"
        )
        result.append(
            {
                "id": consultation.id,
                "label": label,
                "status": consultation.status,
            }
        )
    return result


@inject
async def consultations_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    consultation_dao: FromDishka[ConsultationDao],
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    consultations = await consultation_dao.get_by_client(user.telegram_id)
    items = await _format_consultations(consultations, expert_dao, user_dao, show_client=False)
    return {"consultations": items, "has_consultations": bool(items)}


@inject
async def clients_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    consultation_dao: FromDishka[ConsultationDao],
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    consultations = (
        await consultation_dao.get_by_expert(profile.id) if profile and profile.id else []
    )
    items = await _format_consultations(consultations, expert_dao, user_dao, show_client=True)
    return {"consultations": items, "has_consultations": bool(items)}


@inject
async def expert_cabinet_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None:
        raise ValueError("Expert profile not found")
    return {
        "expert_profile_id": profile.id,
        "name": profile.display_name,
        "specialization": profile.specialization,
        "status": profile.status,
    }


@inject
async def expert_finance_getter(
    dialog_manager: DialogManager,
    get_stats: FromDishka[GetExpertStats],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    stats = await get_stats(user)
    lines = []
    for item in stats.finances:
        lines.append(
            f"{item.currency.value}:\n"
            f"  Общий оборот: {item.gross}\n"
            f"  Комиссия платформы: {item.commission}\n"
            f"  Заработок эксперта: {item.earned}\n"
            f"  Доступно к выводу: {item.available}\n"
            f"  Ожидает выплаты: {item.reserved}\n"
            f"  Выплачено: {item.withdrawn}"
        )
    return {
        "clients_count": stats.clients_count,
        "consultations_count": stats.consultations_count,
        "active_consultations_count": stats.active_consultations_count,
        "finance_lines": "\n".join(lines) or "Начислений пока нет.",
    }


@inject
async def expert_profile_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None or profile.status != ExpertProfileStatus.ACTIVE:
        raise PermissionDeniedError
    return {
        "name": profile.display_name,
        "specialization": profile.specialization,
        "experience": profile.description,
        "expert_photo": (
            MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(profile.photo_file_id),
            )
            if profile.photo_file_id
            else None
        ),
        "has_expert_photo": bool(profile.photo_file_id),
    }


async def _get_selected_expert_price(
    dialog_manager: DialogManager,
    expert_dao: ExpertDao,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None or profile.status != ExpertProfileStatus.ACTIVE:
        raise PermissionDeniedError

    selected = str(dialog_manager.dialog_data.get("expert_price_selection", ""))
    duration_id_raw, separator, currency_raw = selected.partition(":")
    if not separator or not duration_id_raw.isdigit():
        raise ValueError("Expert price selection is missing")
    duration_id = int(duration_id_raw)
    currency = Currency.from_code(currency_raw)

    for plan in await expert_dao.get_available_plans(profile.id):
        for duration in plan.durations:
            if duration.id != duration_id:
                continue
            price = next((item for item in duration.prices if item.currency == currency), None)
            if price:
                return {
                    "plan_name": plan.name,
                    "duration_days": duration.days,
                    "duration_id": duration_id,
                    "currency": currency.value,
                    "current_price": f"{price.price:f}",
                }
    raise ValueError("Expert price is not available")


@inject
async def expert_prices_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None or profile.status != ExpertProfileStatus.ACTIVE:
        raise PermissionDeniedError

    prices = []
    for plan in await expert_dao.get_available_plans(profile.id):
        for duration in plan.durations:
            if duration.id is None:
                continue
            for price in duration.prices:
                if price.currency not in NEW_PLAN_CURRENCIES:
                    continue
                prices.append(
                    {
                        "id": f"{duration.id}:{price.currency.value}",
                        "label": (
                            f"{plan.name} · {duration.days} дн. · "
                            f"{price.price:f} {price.currency.value}"
                        ),
                    }
                )
    return {"prices": prices, "has_prices": bool(prices)}


@inject
async def expert_price_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    **kwargs: Any,
) -> dict[str, Any]:
    data = await _get_selected_expert_price(dialog_manager, expert_dao)
    if "expert_price_proposed" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["expert_price_proposed"] = data["current_price"]
    proposed = str(dialog_manager.dialog_data["expert_price_proposed"])
    return {**data, "proposed_price": proposed}


@inject
async def chat_getter(
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    consultation_dao: FromDishka[ConsultationDao],
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    consultation_id = int(dialog_manager.dialog_data["consultation_id"])
    consultation = await consultation_dao.get_by_id(consultation_id)
    if not consultation:
        raise ValueError("Consultation not found")
    profile = await expert_dao.get_by_id(consultation.expert_profile_id)
    client = await user_dao.get_by_telegram_id(consultation.client_telegram_id)
    return {
        "consultation_id": consultation.id,
        "expert_name": profile.display_name if profile else "—",
        "client_name": client.name if client else "—",
        "status": consultation.status,
        "expires_at": i18n_format_expire_time(consultation.access_expires_at),
        "is_active": (
            consultation.is_active
            and consultation.client_thread_id is not None
            and consultation.expert_thread_id is not None
        ),
    }
