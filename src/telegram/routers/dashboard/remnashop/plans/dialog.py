from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Column,
    CopyText,
    ListGroup,
    Row,
    Select,
    Start,
    SwitchTo,
)
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.enums import BannerName, Currency, PlanAvailability
from src.telegram.keyboards import main_menu_button
from src.telegram.states import DashboardRemnashop, RemnashopPlans
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate

from .getters import (
    allowed_users_getter,
    availability_getter,
    configurator_getter,
    description_getter,
    durations_getter,
    export_getter,
    name_getter,
    plans_getter,
    price_getter,
    prices_getter,
    tag_getter,
)
from .handlers import (
    on_active_toggle,
    on_allowed_user_input,
    on_allowed_user_remove,
    on_availability_select,
    on_currency_select,
    on_description_input,
    on_description_remove,
    on_duration_input,
    on_duration_move,
    on_duration_remove,
    on_duration_select,
    on_export,
    on_export_plan_select,
    on_import_input,
    on_name_input,
    on_plan_confirm,
    on_plan_delete,
    on_plan_move,
    on_plan_select,
    on_price_input,
    on_tag_input,
    on_tag_remove,
    on_trial_toggle,
)

plans = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plans-main"),
    Row(
        SwitchTo(
            I18nFormat("btn-plans.create"),
            id="create",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    ListGroup(
        Row(
            Button(
                text=I18nFormat(
                    "btn-plans.title",
                    name=F["item"]["name"],
                    is_active=F["item"]["is_active"],
                ),
                id="plan_select",
                on_click=on_plan_select,
            ),
            Button(
                text=Format("🔼"),
                id="plan_move",
                on_click=on_plan_move,
            ),
        ),
        id="plans_list",
        item_id_getter=lambda item: item["id"],
        items="plans",
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.import"),
            id="import",
            state=RemnashopPlans.IMPORT,
            when=F["has_plans"],
        ),
        SwitchTo(
            text=I18nFormat("btn-plans.importing"),
            id="import",
            state=RemnashopPlans.IMPORT,
            when=~F["has_plans"],
        ),
        SwitchTo(
            text=I18nFormat("btn-plans.export"),
            id="export",
            state=RemnashopPlans.EXPORT,
            when=F["has_plans"],
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=DashboardRemnashop.MAIN,
            mode=StartMode.RESET_STACK,
        ),
        *main_menu_button,
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.MAIN,
    getter=plans_getter,
)

plans_import = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plans-import"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.MAIN,
        ),
    ),
    MessageInput(func=on_import_input),
    IgnoreUpdate(),
    state=RemnashopPlans.IMPORT,
)

plans_export = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plans-export"),
    Column(
        Select(
            text=I18nFormat(
                "btn-plans.export-choice",
                name=F["item"]["name"],
                selected=F["item"]["selected"],
            ),
            id="plan_select",
            item_id_getter=lambda item: item["id"],
            items="plans",
            type_factory=int,
            on_click=on_export_plan_select,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-plans.exporting"),
            id="export",
            on_click=on_export,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.EXPORT,
    getter=export_getter,
)

configurator = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-configurator"),
    Row(
        Button(
            text=I18nFormat("btn-plans.active", is_active=F["is_active"]),
            id="toggle_active",
            on_click=on_active_toggle,
        ),
        Button(
            text=I18nFormat("btn-plans.trial", is_trial=F["is_trial"]),
            id="trial",
            on_click=on_trial_toggle,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.name"),
            id="name",
            state=RemnashopPlans.NAME,
        ),
        SwitchTo(
            text=I18nFormat("btn-plans.description"),
            id="description",
            state=RemnashopPlans.DESCRIPTION,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.availability"),
            id="availability",
            state=RemnashopPlans.AVAILABILITY,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.tag"),
            id="tag",
            state=RemnashopPlans.TAG,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.allowed"),
            id="allowed",
            state=RemnashopPlans.ALLOWED,
            when=F["availability"] == PlanAvailability.ALLOWED,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.durations-prices"),
            id="durations_prices",
            state=RemnashopPlans.DURATIONS,
        ),
    ),
    Row(
        CopyText(
            text=I18nFormat("btn-plans.url"),
            copy_text=Format("{plan_url}"),
        ),
        when=F["public_code"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-plans.create"),
            id="create",
            on_click=on_plan_confirm,
            style=Style(ButtonStyle.SUCCESS),
        ),
        when=~F["is_edit"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-plans.save"),
            id="save",
            on_click=on_plan_confirm,
            style=Style(ButtonStyle.SUCCESS),
        ),
        Button(
            text=I18nFormat("btn-plans.delete"),
            id="delete_plan",
            on_click=on_plan_delete,
            style=Style(ButtonStyle.DANGER),
        ),
        when=F["is_edit"],
    ),
    Row(
        Start(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.MAIN,
            mode=StartMode.RESET_STACK,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.CONFIGURATOR,
    getter=configurator_getter,
)

name = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-name"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    MessageInput(func=on_name_input),
    IgnoreUpdate(),
    state=RemnashopPlans.NAME,
    getter=name_getter,
)

description = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-description"),
    Row(
        Button(
            text=I18nFormat("btn-plans.description-remove"),
            id="remove",
            on_click=on_description_remove,
        ),
        when=F["description"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    MessageInput(func=on_description_input),
    IgnoreUpdate(),
    state=RemnashopPlans.DESCRIPTION,
    getter=description_getter,
)

tag = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-tag"),
    Row(
        Button(
            text=I18nFormat("btn-plans.tag-remove"),
            id="remove",
            on_click=on_tag_remove,
        ),
        when=F["tag"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    MessageInput(func=on_tag_input),
    IgnoreUpdate(),
    state=RemnashopPlans.TAG,
    getter=tag_getter,
)

availability = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-availability"),
    Column(
        Select(
            text=I18nFormat("btn-plans.availability-choice", type=F["item"]),
            id="select_availability",
            item_id_getter=lambda item: item.value,
            items="availability",
            type_factory=PlanAvailability,
            on_click=on_availability_select,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.AVAILABILITY,
    getter=availability_getter,
)

durations = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-durations"),
    ListGroup(
        Row(
            Button(
                text=I18nFormat("btn-common.duration", value=F["item"]["days"]),
                id="duration_select",
                on_click=on_duration_select,
            ),
            Button(
                text=Format("🔼"),
                id="duration_move",
                on_click=on_duration_move,
            ),
            Button(
                text=Format("❌"),
                id="duration_remove",
                on_click=on_duration_remove,
                when=F["data"]["deletable"],
            ),
        ),
        id="duration_list",
        item_id_getter=lambda item: item["days"],
        items="durations",
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-plans.duration-add"),
            id="duration_add",
            state=RemnashopPlans.DURATION_ADD,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.DURATIONS,
    getter=durations_getter,
)

durations_add = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-duration"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.DURATIONS,
        ),
    ),
    MessageInput(func=on_duration_input),
    IgnoreUpdate(),
    state=RemnashopPlans.DURATION_ADD,
)

prices = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-prices", value=F["duration"]),
    Column(
        Select(
            text=I18nFormat(
                "btn-plans.price-choice",
                price=F["item"]["price"],
                currency=F["item"]["currency"],
            ),
            id="price_select",
            item_id_getter=lambda item: item["currency"],
            items="prices",
            type_factory=Currency,
            on_click=on_currency_select,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.DURATIONS,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopPlans.PRICES,
    getter=prices_getter,
)

price = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-price", value=F["duration"], currency=F["currency"]),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.PRICES,
        ),
    ),
    MessageInput(func=on_price_input),
    IgnoreUpdate(),
    state=RemnashopPlans.PRICE,
    getter=price_getter,
)

allowed_users = Window(
    Banner(BannerName.TARIFF),
    I18nFormat("msg-plan-allowed-users"),
    ListGroup(
        Row(
            CopyText(
                text=Format("{item}"),
                copy_text=Format("{item}"),
            ),
            Button(
                text=Format("❌"),
                id="allowed_user_remove",
                on_click=on_allowed_user_remove,
            ),
        ),
        id="allowed_users_list",
        item_id_getter=lambda item: item,
        items="allowed_users",
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopPlans.CONFIGURATOR,
        ),
    ),
    MessageInput(func=on_allowed_user_input),
    IgnoreUpdate(),
    state=RemnashopPlans.ALLOWED,
    getter=allowed_users_getter,
)

router = Dialog(
    plans,
    plans_import,
    plans_export,
    configurator,
    name,
    description,
    tag,
    availability,
    durations,
    durations_add,
    prices,
    price,
    allowed_users,
)
