from aiogram.enums import ButtonStyle
from aiogram.fsm.state import State
from aiogram_dialog import Dialog, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Start,
)
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.application.common.policy import Permission
from src.core.constants import INLINE_QUERY_INVITE, PAYMENT_PREFIX
from src.core.enums import BannerName, PurchaseType
from src.telegram.keyboards import custom_buttons
from src.telegram.routers.dashboard.users.handlers import on_user_search
from src.telegram.routers.experts.handlers import (
    on_become_expert,
)
from src.telegram.states import Dashboard, Experts, MainMenu, Subscription
from src.telegram.utils import require_permission
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate
from src.telegram.widgets.icon_buttons import (
    IconButton,
    IconSwitchInlineQueryChosenChatButton,
    IconSwitchTo,
    IconUrl,
)
from src.telegram.widgets.icon_start import IconStart
from src.telegram.window import Window

from .getters import invite_getter, menu_getter
from .handlers import (
    on_get_trial,
    on_invite,
)

INSTRUCTION_EMPTY_LINK = "https://example.com"
INSTRUCTION_DOWNLOAD_URLS = {
    "ios": "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215",
    "iosru": "https://apps.apple.com/ru/app/happ-proxy-utility/id6783623643",
    "android": "https://play.google.com/store/apps/details?id=com.happproxy",
    "windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
    "macos": "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215",
    "macosru": "https://apps.apple.com/ru/app/happ-proxy-utility/id6783623643",
}

menu = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-main-menu"),
    Row(
        IconStart(
            text=I18nFormat("btn-experts.catalog"),
            id="experts_catalog",
            state=Experts.CATALOG,
            style=Style(ButtonStyle.PRIMARY),
            icon_custom_emoji_id="5258204546391351475",
        ),
    ),
    Row(
        IconButton(
            text=I18nFormat("btn-experts.become"),
            id="become_expert",
            on_click=on_become_expert,
            when=F["can_apply_expert"],
            icon_custom_emoji_id="5258204546391351475",
        ),
    ),
    Row(
        IconStart(
            text=I18nFormat("btn-experts.cabinet"),
            id="expert_cabinet",
            state=Experts.CABINET,
            when=F["is_expert"],
        ),
    ),
    Row(
        IconStart(
            text=I18nFormat("btn-experts.consultations"),
            id="my_consultations",
            state=Experts.CONSULTATIONS,
            icon_custom_emoji_id="5257969839313526622",
        ),
        IconStart(
            text=I18nFormat("btn-experts.clients"),
            id="expert_clients",
            state=Experts.CLIENTS,
            when=F["is_expert"],
            icon_custom_emoji_id="5258328383183396223",
        ),
    ),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-menu.support"),
            id="support",
            state=MainMenu.SUPPORT,
            icon_custom_emoji_id="5260249440450520061",
        ),
        IconButton(
            text=I18nFormat("btn-menu.invite"),
            id="invite",
            on_click=on_invite,
            when=F["referral_enabled"],
            icon_custom_emoji_id="5258362837411045098",
        ),
        IconSwitchInlineQueryChosenChatButton(
            text=I18nFormat("btn-menu.invite"),
            query=Format(INLINE_QUERY_INVITE),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            id="send",
            when=~F["referral_enabled"],
            icon_custom_emoji_id="5258362837411045098",
        ),
    ),
    *custom_buttons,
    Row(
        Start(
            text=I18nFormat("btn-menu.dashboard"),
            id="dashboard",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
            when=require_permission(Permission.VIEW_DASHBOARD),
        ),
    ),
    MessageInput(func=on_user_search),
    IgnoreUpdate(),
    state=MainMenu.MAIN,
    getter=menu_getter,
)

support = Window(
    Banner(BannerName.HELP),
    I18nFormat("msg-menu-support"),
    Row(
        IconUrl(
            text=I18nFormat("btn-support.user-agreement"),
            id="user_agreement",
            url=Format("{user_agreement_url}"),
            icon_custom_emoji_id="5257965810634202885",
        ),
    ),
    Row(
        IconUrl(
            text=I18nFormat("btn-support.privacy-policy"),
            id="privacy_policy",
            url=Format("{privacy_policy_url}"),
            icon_custom_emoji_id="5257965810634202885",
        ),
    ),
    Row(
        IconUrl(
            text=I18nFormat("btn-support.contact"),
            id="contact_support",
            url=Format("{support_url}"),
            icon_custom_emoji_id="5316727448644103237",
        ),
    ),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.MAIN,
            icon_custom_emoji_id="5258236805890710909",
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.SUPPORT,
    getter=menu_getter,
)

instruction = Window(
    Banner(BannerName.HELP),
    I18nFormat("msg-menu-instruction"),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-instruction.ios"),
            id="instruction_ios",
            state=MainMenu.INSTRUCTION_IOS,
            when=F["has_active_subscription"],
            icon_custom_emoji_id="5775870512127283512",
        ),
        IconSwitchTo(
            text=I18nFormat("btn-instruction.android"),
            id="instruction_android",
            state=MainMenu.INSTRUCTION_ANDROID,
            when=F["has_active_subscription"],
            icon_custom_emoji_id="5100720104375583787",
        ),
    ),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-instruction.windows"),
            id="instruction_windows",
            state=MainMenu.INSTRUCTION_WINDOWS,
            when=F["has_active_subscription"],
            icon_custom_emoji_id="4976701317385814718",
        ),
        IconSwitchTo(
            text=I18nFormat("btn-instruction.macos"),
            id="instruction_macos",
            state=MainMenu.INSTRUCTION_MACOS,
            when=F["has_active_subscription"],
            icon_custom_emoji_id="5775870512127283512",
        ),
    ),
    Row(
        IconStart(
            text=I18nFormat("btn-subscription.new"),
            id=f"{PAYMENT_PREFIX}instruction_new",
            state=Subscription.PLANS,
            data={"purchase_type": PurchaseType.NEW},
            when=~F["has_active_subscription"],
            icon_custom_emoji_id="5258204546391351475",
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu.trial"),
            id="instruction_trial",
            on_click=on_get_trial,
            when=~F["has_active_subscription"] & F["trial_available"],
            style=Style(ButtonStyle.SUCCESS),
        ),
    ),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-instruction.back"),
            id="back",
            state=MainMenu.MAIN,
            icon_custom_emoji_id="5258236805890710909",
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INSTRUCTION,
    getter=menu_getter,
)


def instruction_platform_window(
    state: State,
    download_buttons: tuple[tuple[str, str, str], ...],
) -> Window:
    return Window(
        Banner(BannerName.HELP),
        I18nFormat("msg-menu-instruction-platform"),
        *[
            Row(
                IconUrl(
                    text=I18nFormat(text_key),
                    id=button_id,
                    url=Format(download_url),
                    icon_custom_emoji_id="5258336354642697821",
                ),
            )
            for button_id, text_key, download_url in download_buttons
        ],
        Row(
            IconUrl(
                text=I18nFormat("btn-instruction.connect"),
                id="connect_app",
                url=Format("{happ_connection_url}"),
                when=F["happ_connection_url"],
                icon_custom_emoji_id="5884428842780594914",
            ),
        ),
        Row(
            IconSwitchTo(
                text=I18nFormat("btn-instruction.back"),
                id="back",
                state=MainMenu.INSTRUCTION,
                icon_custom_emoji_id="5258236805890710909",
            ),
        ),
        IgnoreUpdate(),
        state=state,
        getter=menu_getter,
    )


instruction_ios = instruction_platform_window(
    state=MainMenu.INSTRUCTION_IOS,
    download_buttons=(
        (
            "download_app_ios_ru",
            "btn-instruction.download_ru",
            INSTRUCTION_DOWNLOAD_URLS["iosru"],
        ),
        (
            "download_app_ios_global",
            "btn-instruction.download_global",
            INSTRUCTION_DOWNLOAD_URLS["ios"],
        ),
    ),
)
instruction_android = instruction_platform_window(
    state=MainMenu.INSTRUCTION_ANDROID,
    download_buttons=(
        (
            "download_app_android",
            "btn-instruction.download",
            INSTRUCTION_DOWNLOAD_URLS["android"],
        ),
    ),
)
instruction_windows = instruction_platform_window(
    state=MainMenu.INSTRUCTION_WINDOWS,
    download_buttons=(
        (
            "download_app_windows",
            "btn-instruction.download",
            INSTRUCTION_DOWNLOAD_URLS["windows"],
        ),
    ),
)
instruction_macos = instruction_platform_window(
    state=MainMenu.INSTRUCTION_MACOS,
    download_buttons=(
        (
            "download_app_macos_ru",
            "btn-instruction.download_ru",
            INSTRUCTION_DOWNLOAD_URLS["macosru"],
        ),
        (
            "download_app_macos_global",
            "btn-instruction.download_global",
            INSTRUCTION_DOWNLOAD_URLS["macos"],
        ),
    ),
)

invite = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-invite"),
    Row(
        IconUrl(
            text=I18nFormat("btn-invite.send"),
            id="send",
            url=Format("{share_url}"),
            icon_custom_emoji_id="5258362837411045098",
        ),
    ),
    Row(
        IconSwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.MAIN,
            icon_custom_emoji_id="5258236805890710909",
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INVITE,
    getter=invite_getter,
)

router = Dialog(
    menu,
    support,
    instruction,
    instruction_ios,
    instruction_android,
    instruction_windows,
    instruction_macos,
    invite,
)
