from decimal import Decimal
from typing import Any, Optional

from adaptix import Retort
from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import TranslatorRunner
from src.application.common.dao import PlanDao
from src.application.dto import PlanDto, PlanDurationDto, PlanPriceDto
from src.application.services import BotService
from src.core.enums import Currency, PlanAvailability
from src.core.payment_policy import NEW_PLAN_CURRENCIES


@inject
async def plans_getter(
    dialog_manager: DialogManager,
    plan_dao: FromDishka[PlanDao],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    plans: list[PlanDto] = await plan_dao.get_all()

    formatted_plans = [
        {
            "id": plan.id,
            "name": i18n.get(plan.name),
            "is_active": plan.is_active,
        }
        for plan in plans
    ]

    return {
        "has_plans": bool(plans),
        "plans": formatted_plans,
    }


@inject
async def export_getter(
    dialog_manager: DialogManager,
    plan_dao: FromDishka[PlanDao],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    plans: list[PlanDto] = await plan_dao.get_all()
    selected_plans = dialog_manager.dialog_data.get("selected_plans", [])

    formatted_plans = [
        {
            "id": plan.id,
            "name": i18n.get(plan.name),
            "selected": plan.id in selected_plans,
        }
        for plan in plans
    ]

    return {
        "plans": formatted_plans,
    }


@inject
async def configurator_getter(
    dialog_manager: DialogManager,
    bot_service: FromDishka[BotService],
    i18n: FromDishka[TranslatorRunner],
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    raw_plan = dialog_manager.dialog_data.get(PlanDto.__name__)

    if raw_plan is None:
        plan = PlanDto(
            durations=[
                PlanDurationDto(
                    days=7,
                    prices=[
                        PlanPriceDto(currency=Currency.RUB, price=Decimal(50)),
                        PlanPriceDto(currency=Currency.XTR, price=Decimal(30)),
                    ],
                ),
                PlanDurationDto(
                    days=30,
                    prices=[
                        PlanPriceDto(currency=Currency.RUB, price=Decimal(100)),
                        PlanPriceDto(currency=Currency.XTR, price=Decimal(60)),
                    ],
                ),
                PlanDurationDto(
                    days=365,
                    prices=[
                        PlanPriceDto(currency=Currency.RUB, price=Decimal(1000)),
                        PlanPriceDto(currency=Currency.XTR, price=Decimal(600)),
                    ],
                ),
                PlanDurationDto(
                    days=0,
                    prices=[
                        PlanPriceDto(currency=Currency.RUB, price=Decimal(10000)),
                        PlanPriceDto(currency=Currency.XTR, price=Decimal(6000)),
                    ],
                ),
            ],
        )
        dialog_manager.dialog_data[PlanDto.__name__] = retort.dump(plan)
    else:
        plan = retort.load(raw_plan, PlanDto)

    helpers = {
        "name": i18n.get(plan.name),
        "is_edit": dialog_manager.dialog_data.get("is_edit", False),
        "availability_type": plan.availability,
        "plan_url": f"{await bot_service.get_plan_url(plan.public_code)}"
        if plan.public_code
        else False,
    }

    data: dict = retort.dump(plan)
    data.update(helpers)
    return data


@inject
async def name_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)
    return {"name": plan.name}


@inject
async def description_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)
    return {"description": plan.description}


@inject
async def tag_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)
    return {"tag": plan.tag}


async def availability_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    return {"availability": list(PlanAvailability)}


@inject
async def durations_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)

    durations = [retort.dump(duration) for duration in plan.durations]

    return {
        "deletable": len(durations) > 1,
        "durations": durations,
    }


def get_prices_for_duration(
    durations: list[PlanDurationDto],
    target_days: int,
) -> Optional[list[PlanPriceDto]]:
    for duration in durations:
        if duration.days == target_days:
            return duration.prices
    return []


@inject
async def prices_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)
    selected_duration = dialog_manager.dialog_data["selected_duration"]
    prices = get_prices_for_duration(plan.durations, selected_duration)
    currency_order = {currency: index for index, currency in enumerate(NEW_PLAN_CURRENCIES)}
    prices = sorted(
        (price for price in prices if price.currency in NEW_PLAN_CURRENCIES),
        key=lambda price: currency_order[price.currency],
    )
    prices_data = [retort.dump(price) for price in prices] if prices else []

    return {
        "duration": selected_duration,
        "prices": prices_data,
    }


async def price_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    selected_duration = dialog_manager.dialog_data.get("selected_duration")
    selected_currency = dialog_manager.dialog_data.get("selected_currency")
    return {
        "duration": selected_duration,
        "currency": selected_currency,
    }


@inject
async def allowed_users_getter(
    dialog_manager: DialogManager,
    retort: FromDishka[Retort],
    **kwargs: Any,
) -> dict[str, Any]:
    plan = retort.load(dialog_manager.dialog_data[PlanDto.__name__], PlanDto)
    return {"allowed_users": plan.allowed_user_ids if plan.allowed_user_ids else []}
