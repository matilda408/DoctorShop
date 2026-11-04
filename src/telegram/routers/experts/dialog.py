from typing import Any

from aiogram_dialog import Dialog, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Row, Select, Start, SwitchTo
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.enums import BannerName
from src.telegram.states import Experts, MainMenu
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate
from src.telegram.window import Window

from .getters import (
    catalog_getter,
    chat_getter,
    clients_getter,
    consultations_getter,
    expert_cabinet_getter,
    expert_details_getter,
    expert_finance_getter,
    expert_price_getter,
    expert_prices_getter,
    expert_profile_getter,
)
from .handlers import (
    on_buy_consultation,
    on_client_message,
    on_consultation_select,
    on_expert_price_custom,
    on_expert_price_decrease,
    on_expert_price_increase,
    on_expert_price_input,
    on_expert_price_save,
    on_expert_profile_field_input,
    on_expert_profile_photo_input,
    on_expert_profile_start,
    on_expert_select,
    on_expert_tariff_select,
    on_expert_tariffs,
    on_start_withdrawal,
)

catalog = Window(
    Banner(BannerName.EXPERTS),
    I18nFormat("msg-experts-catalog"),
    Column(
        Select(
            text=Format("{item[name]} — {item[specialization]}"),
            id="expert_select",
            item_id_getter=lambda item: item["id"],
            items="experts",
            type_factory=int,
            on_click=on_expert_select,
        ),
        when=F["has_experts"],
    ),
    Row(
        Start(
            text=I18nFormat("btn-back.menu-return"),
            id="back_menu",
            state=MainMenu.MAIN,
            mode=StartMode.RESET_STACK,
        )
    ),
    IgnoreUpdate(),
    state=Experts.CATALOG,
    getter=catalog_getter,
)

details = Window(
    DynamicMedia("expert_photo", when=F["has_expert_photo"]) | Banner(BannerName.EXPERTS),
    I18nFormat("msg-expert-details"),
    Row(
        Button(
            text=I18nFormat("btn-experts.buy"),
            id="buy",
            on_click=on_buy_consultation,
            when=F["has_plans"],
        )
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=Experts.CATALOG,
        )
    ),
    IgnoreUpdate(),
    state=Experts.DETAILS,
    getter=expert_details_getter,
)


def consultations_window(state: Any, getter: Any) -> Window:
    return Window(
        Banner(BannerName.CONSULTATIONS),
        I18nFormat("msg-consultations-list"),
        Column(
            Select(
                text=Format("{item[label]} · {item[status]}"),
                id=f"consultation_{state.state.replace(':', '_').lower()}",
                item_id_getter=lambda item: item["id"],
                items="consultations",
                type_factory=int,
                on_click=on_consultation_select,
            ),
            when=F["has_consultations"],
        ),
        Row(
            Start(
                text=I18nFormat("btn-back.menu-return"),
                id="back_menu",
                state=MainMenu.MAIN,
                mode=StartMode.RESET_STACK,
            )
        ),
        IgnoreUpdate(),
        state=state,
        getter=getter,
    )


chat = Window(
    Banner(BannerName.CONSULTATIONS),
    I18nFormat("msg-consultation-chat"),
    MessageInput(func=on_client_message),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=Experts.CONSULTATIONS,
        )
    ),
    state=Experts.CHAT,
    getter=chat_getter,
)

cabinet = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-cabinet"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-experts.clients"),
            id="cabinet_clients",
            state=Experts.CLIENTS,
        ),
        Button(
            text=I18nFormat("btn-experts.prices"),
            id="cabinet_prices",
            on_click=on_expert_tariffs,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-experts.profile-edit"),
            id="cabinet_profile",
            on_click=on_expert_profile_start,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-experts.finance"),
            id="cabinet_finance",
            state=Experts.FINANCE,
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-back.menu-return"),
            id="cabinet_menu",
            state=MainMenu.MAIN,
            mode=StartMode.RESET_STACK,
        )
    ),
    IgnoreUpdate(),
    state=Experts.CABINET,
    getter=expert_cabinet_getter,
)

finance = Window(
    Banner(BannerName.FINANCE),
    I18nFormat("msg-expert-finance"),
    Row(
        Button(
            text=I18nFormat("btn-experts.withdraw"),
            id="finance_withdraw",
            on_click=on_start_withdrawal,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="finance_back",
            state=Experts.CABINET,
        )
    ),
    IgnoreUpdate(),
    state=Experts.FINANCE,
    getter=expert_finance_getter,
)

prices = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-prices"),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="expert_tariff_select",
            item_id_getter=lambda item: item["id"],
            items="prices",
            on_click=on_expert_tariff_select,
        ),
        when=F["has_prices"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="prices_back",
            state=Experts.CABINET,
        )
    ),
    IgnoreUpdate(),
    state=Experts.PRICES,
    getter=expert_prices_getter,
)

price = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-price"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-experts.price-edit"),
            id="price_edit",
            state=Experts.PRICE_EDIT,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="price_back",
            state=Experts.PRICES,
        )
    ),
    IgnoreUpdate(),
    state=Experts.PRICE,
    getter=expert_price_getter,
)

price_edit = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-price-edit"),
    Row(
        Button(
            text=I18nFormat("btn-experts.price-decrease"),
            id="price_decrease",
            on_click=on_expert_price_decrease,
        ),
        Button(
            text=I18nFormat("btn-experts.price-increase"),
            id="price_increase",
            on_click=on_expert_price_increase,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-experts.price-custom"),
            id="price_custom",
            on_click=on_expert_price_custom,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-experts.price-save"),
            id="price_save",
            on_click=on_expert_price_save,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="price_edit_back",
            state=Experts.PRICE,
        )
    ),
    IgnoreUpdate(),
    state=Experts.PRICE_EDIT,
    getter=expert_price_getter,
)

price_input = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-price-input"),
    MessageInput(func=on_expert_price_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="price_input_back",
            state=Experts.PRICE_EDIT,
        )
    ),
    state=Experts.PRICE_INPUT,
    getter=expert_price_getter,
)

profile = Window(
    DynamicMedia("expert_photo", when=F["has_expert_photo"]) | Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-profile"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-experts.profile-name"),
            id="profile_name",
            state=Experts.PROFILE_NAME,
        ),
        SwitchTo(
            text=I18nFormat("btn-experts.profile-specialization"),
            id="profile_specialization",
            state=Experts.PROFILE_SPECIALIZATION,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-experts.profile-experience"),
            id="profile_experience",
            state=Experts.PROFILE_EXPERIENCE,
        ),
        SwitchTo(
            text=I18nFormat("btn-experts.profile-photo"),
            id="profile_photo",
            state=Experts.PROFILE_PHOTO,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="profile_back",
            state=Experts.CABINET,
        )
    ),
    IgnoreUpdate(),
    state=Experts.PROFILE,
    getter=expert_profile_getter,
)


def profile_input_window(state: Any, message_key: str) -> Window:
    cancel_id = f"{state.state.replace(':', '_').lower()}_cancel"
    return Window(
        Banner(BannerName.EXPERT_CABINET),
        I18nFormat(message_key),
        MessageInput(func=on_expert_profile_field_input),
        Row(
            SwitchTo(
                text=I18nFormat("btn-common.cancel"),
                id=cancel_id,
                state=Experts.PROFILE,
            )
        ),
        state=state,
        getter=expert_profile_getter,
    )


profile_photo = Window(
    Banner(BannerName.EXPERT_CABINET),
    I18nFormat("msg-expert-profile-photo"),
    MessageInput(func=on_expert_profile_photo_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-common.cancel"),
            id="profile_photo_cancel",
            state=Experts.PROFILE,
        )
    ),
    state=Experts.PROFILE_PHOTO,
    getter=expert_profile_getter,
)

router = Dialog(
    catalog,
    details,
    consultations_window(Experts.CONSULTATIONS, consultations_getter),
    consultations_window(Experts.CLIENTS, clients_getter),
    chat,
    cabinet,
    finance,
    prices,
    price,
    price_edit,
    price_input,
    profile,
    profile_input_window(Experts.PROFILE_NAME, "msg-expert-profile-name"),
    profile_input_window(Experts.PROFILE_SPECIALIZATION, "msg-expert-profile-specialization"),
    profile_input_window(Experts.PROFILE_EXPERIENCE, "msg-expert-profile-experience"),
    profile_photo,
)
