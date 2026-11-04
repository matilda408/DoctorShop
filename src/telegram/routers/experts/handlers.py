from decimal import Decimal
from typing import cast

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram import inject as inject_aiogram
from dishka.integrations.aiogram_dialog import inject

from src.application.common import Notifier
from src.application.common.dao import ConsultationDao, ExpertDao, ExpertFinanceDao
from src.application.common.uow import UnitOfWork
from src.application.dto import ConsultationDto, ExpertProfileDto, ExpertStatsDto, UserDto
from src.application.use_cases.consultation.commands import (
    EditExpertProfile,
    EditExpertProfileDto,
    RetryConsultationTopic,
    SetConsultationActive,
    SetConsultationActiveDto,
)
from src.application.use_cases.consultation.expert_business import (
    GetExpertStats,
    ModerateExpertApplication,
    ModerateExpertApplicationDto,
    ProcessExpertWithdrawal,
    ProcessExpertWithdrawalDto,
    RequestExpertWithdrawal,
    RequestExpertWithdrawalDto,
    SetExpertPrice,
    SetExpertPriceDto,
    SetServiceCommission,
    SetServiceCommissionDto,
    SubmitExpertApplication,
    SubmitExpertApplicationDto,
    parse_positive_amount,
)
from src.core.constants import USER_KEY
from src.core.enums import Currency, ExpertProfileStatus, PurchaseType, Role
from src.core.exceptions import ExpertApplicationAlreadyProcessedError, PermissionDeniedError
from src.core.utils.time import datetime_now
from src.telegram.states import ExpertApplication, Experts, ExpertWithdrawal, Subscription

router = Router(name=__name__)


async def begin_expert_application(
    state: FSMContext,
    user: UserDto,
    expert_dao: ExpertDao,
) -> str:
    """Prepare one pending expert application using the registration name."""
    await state.clear()
    if user.role == Role.EXPERT:
        return "Вы уже являетесь экспертом."
    if not user.is_registration_completed or not user.name.strip():
        return "Сначала завершите обычную регистрацию и укажите ФИО."

    profile = await expert_dao.get_by_user(user.telegram_id)
    if profile and profile.status == ExpertProfileStatus.MODERATION:
        return "Ваша заявка уже отправлена администратору и ожидает решения."
    if profile and profile.status == ExpertProfileStatus.ACTIVE:
        return "Ваша анкета эксперта уже активна."

    await state.update_data(display_name=" ".join(user.name.split()))
    await state.set_state(ExpertApplication.SPECIALIZATION)
    return "Укажите специальность, например: кардиолог."


@router.message(Command("expert_apply"))
@inject_aiogram
async def start_expert_application(
    message: Message,
    state: FSMContext,
    user: UserDto,
    expert_dao: FromDishka[ExpertDao],
) -> None:
    await message.answer(await begin_expert_application(state, user, expert_dao))


@inject
async def on_become_expert(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
) -> None:
    state = cast(FSMContext, dialog_manager.middleware_data["state"])
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    await dialog_manager.done()
    if isinstance(callback.message, Message):
        await callback.message.answer(await begin_expert_application(state, user, expert_dao))
    await callback.answer()


@router.message(Command("cancel"), StateFilter(ExpertApplication))
async def cancel_expert_application(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Регистрация эксперта отменена.")


@router.message(StateFilter(ExpertApplication.SPECIALIZATION))
async def application_specialization(message: Message, state: FSMContext) -> None:
    value = " ".join((message.text or "").split())
    if not 2 <= len(value) <= 128:
        await message.answer("Введите специальность длиной от 2 до 128 символов.")
        return
    await state.update_data(specialization=value)
    await state.set_state(ExpertApplication.EXPERIENCE)
    await message.answer("Кратко опишите опыт")


@router.message(StateFilter(ExpertApplication.EXPERIENCE))
async def application_experience(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not 10 <= len(value) <= 2000:
        await message.answer("Описание должно содержать от 10 до 2000 символов.")
        return
    await state.update_data(description=value)
    await state.set_state(ExpertApplication.PHOTO)
    await message.answer("Отправьте фотографию для карточки эксперта:")


@router.message(StateFilter(ExpertApplication.PHOTO))
@inject_aiogram
async def application_photo(
    message: Message,
    state: FSMContext,
    user: UserDto,
    submit_application: FromDishka[SubmitExpertApplication],
) -> None:
    if not message.photo:
        await message.answer("Пожалуйста, отправьте именно фотографию для карточки эксперта.")
        return
    form = await state.get_data()
    profile = await submit_application(
        user,
        SubmitExpertApplicationDto(
            display_name=str(form["display_name"]),
            specialization=str(form["specialization"]),
            description=str(form["description"]),
            experience_years=0,
            photo_file_id=message.photo[-1].file_id,
        ),
    )
    await state.clear()
    await message.answer(
        f"Заявка #{profile.id} отправлена администратору. Мы сообщим решение в этом чате."
    )


def format_expert_stats(data: ExpertStatsDto) -> str:
    lines = [
        "📊 Статистика эксперта",
        f"Клиентов: {data.clients_count}",
        f"Консультаций: {data.consultations_count}",
        f"Активных: {data.active_consultations_count}",
        "",
    ]
    finances = data.finances
    if not finances:
        lines.append("Начислений пока нет.")
    for item in finances:
        lines.extend(
            [
                f"{item.currency.value}:",
                f"  оплачено клиентами: {item.gross}",
                f"  комиссия сервиса: {item.commission}",
                f"  доступно к выводу: {item.available}",
                f"  ожидает решения: {item.reserved}",
                f"  выплачено: {item.withdrawn}",
            ]
        )
    return "\n".join(lines)


@router.message(Command("expert_stats"))
@inject_aiogram
async def expert_stats_command(
    message: Message,
    user: UserDto,
    get_stats: FromDishka[GetExpertStats],
) -> None:
    await message.answer(format_expert_stats(await get_stats(user)))


@inject
async def on_expert_stats(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    get_stats: FromDishka[GetExpertStats],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    if isinstance(callback.message, Message):
        await callback.message.answer(format_expert_stats(await get_stats(user)))
    await callback.answer()


async def on_expert_tariffs(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.switch_to(state=Experts.PRICES)
    await callback.answer()


async def on_expert_profile_start(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.switch_to(state=Experts.PROFILE)
    await callback.answer()


def _profile_field_for_state(dialog_manager: DialogManager) -> str | None:
    return {
        Experts.PROFILE_NAME.state: "name",
        Experts.PROFILE_SPECIALIZATION.state: "specialization",
        Experts.PROFILE_EXPERIENCE.state: "description",
    }.get(dialog_manager.current_context().state)


def _validate_profile_value(field: str, raw_value: str) -> str:
    value = " ".join(raw_value.split()) if field != "description" else raw_value.strip()
    if field == "name":
        if not 3 <= len(value) <= 128 or any(character.isdigit() for character in value):
            raise ValueError("Введите корректное ФИО текстом (от 3 до 128 символов).")
    elif field == "specialization":
        if not 2 <= len(value) <= 128:
            raise ValueError("Введите специальность длиной от 2 до 128 символов.")
    elif field == "description" and not 10 <= len(value) <= 2000:
        raise ValueError("Опыт работы должен содержать от 10 до 2000 символов.")
    return value


@inject
async def on_expert_profile_field_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    edit_profile: FromDishka[EditExpertProfile],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    field = _profile_field_for_state(dialog_manager)
    if field is None:
        raise ValueError("Unknown expert profile field")
    try:
        value = _validate_profile_value(field, message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None:
        raise PermissionDeniedError
    try:
        await edit_profile(
            user,
            EditExpertProfileDto(expert_profile_id=profile.id, field=field, value=value),
        )
    except ValueError as error:
        await message.answer(str(error))
        return
    await dialog_manager.switch_to(state=Experts.PROFILE)


@inject
async def on_expert_profile_photo_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    expert_dao: FromDishka[ExpertDao],
    edit_profile: FromDishka[EditExpertProfile],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    if not message.photo:
        await message.answer("Пожалуйста, отправьте именно фотографию.")
        return
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    profile = await expert_dao.get_by_user(user.telegram_id)
    if not profile or profile.id is None:
        raise PermissionDeniedError
    await edit_profile(
        user,
        EditExpertProfileDto(
            expert_profile_id=profile.id,
            field="photo",
            value=message.photo[-1].file_id,
        ),
    )
    await dialog_manager.switch_to(state=Experts.PROFILE)


async def on_expert_tariff_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_price: str,
) -> None:
    dialog_manager.dialog_data["expert_price_selection"] = selected_price
    dialog_manager.dialog_data.pop("expert_price_proposed", None)
    await dialog_manager.switch_to(state=Experts.PRICE)
    await callback.answer()


def _validate_expert_price(value: Decimal) -> Decimal:
    price = parse_positive_amount(str(value))
    if price > Decimal("10000000"):
        raise ValueError("Цена должна быть больше нуля и не выше 10 000 000")
    return price


def _get_proposed_price(dialog_manager: DialogManager) -> Decimal:
    raw_price = dialog_manager.dialog_data.get("expert_price_proposed")
    if raw_price is None:
        raise ValueError("Сначала выберите тариф")
    return _validate_expert_price(Decimal(str(raw_price)))


async def _adjust_expert_price(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    delta: Decimal,
) -> None:
    try:
        price = _validate_expert_price(_get_proposed_price(dialog_manager) + delta)
    except (ArithmeticError, ValueError) as error:
        await callback.answer(str(error), show_alert=True)
        return
    dialog_manager.dialog_data["expert_price_proposed"] = str(price)
    await callback.answer()


async def on_expert_price_decrease(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _adjust_expert_price(callback, dialog_manager, Decimal("-100"))


async def on_expert_price_increase(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _adjust_expert_price(callback, dialog_manager, Decimal("100"))


async def on_expert_price_custom(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.switch_to(state=Experts.PRICE_INPUT)
    await callback.answer()


@inject
async def on_expert_price_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    try:
        price = _validate_expert_price(Decimal(message.text or ""))
    except (ArithmeticError, ValueError):
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return
    dialog_manager.dialog_data["expert_price_proposed"] = str(price)
    await dialog_manager.switch_to(state=Experts.PRICE_EDIT)


@inject
async def on_expert_price_save(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    set_price: FromDishka[SetExpertPrice],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    selected = str(dialog_manager.dialog_data.get("expert_price_selection", ""))
    duration_id_raw, separator, currency_raw = selected.partition(":")
    if not separator or not duration_id_raw.isdigit():
        await callback.answer("Сначала выберите тариф", show_alert=True)
        return
    try:
        result = await set_price(
            user,
            SetExpertPriceDto(
                plan_duration_id=int(duration_id_raw),
                currency=Currency.from_code(currency_raw),
                price=_get_proposed_price(dialog_manager),
            ),
        )
    except (ArithmeticError, ValueError) as error:
        await callback.answer(str(error), show_alert=True)
        return
    dialog_manager.dialog_data["expert_price_proposed"] = str(result.price)
    await dialog_manager.switch_to(state=Experts.PRICE)
    await callback.answer("Стоимость сохранена")


@router.message(Command("withdraw"))
async def start_withdrawal(message: Message, state: FSMContext, user: UserDto) -> None:
    if user.role != Role.EXPERT:
        raise PermissionDeniedError
    await state.clear()
    await state.set_state(ExpertWithdrawal.AMOUNT)
    await message.answer("Введите сумму вывода:")


@inject
async def on_start_withdrawal(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    state = cast(FSMContext, dialog_manager.middleware_data["state"])
    await dialog_manager.done()
    await state.clear()
    await state.set_state(ExpertWithdrawal.AMOUNT)
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите сумму вывода:")
    await callback.answer()


@router.message(StateFilter(ExpertWithdrawal.AMOUNT))
async def withdrawal_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = parse_positive_amount(message.text or "")
    except ValueError as error:
        await message.answer(str(error))
        return
    await state.update_data(withdrawal_amount=str(amount))
    await state.set_state(ExpertWithdrawal.CURRENCY)
    await message.answer("Укажите валюту баланса: RUB, USD или XTR.")


@router.message(StateFilter(ExpertWithdrawal.CURRENCY))
async def withdrawal_currency(message: Message, state: FSMContext) -> None:
    try:
        currency = Currency.from_code(message.text or "")
    except ValueError:
        await message.answer("Допустимые валюты: RUB, USD или XTR.")
        return
    await state.update_data(withdrawal_currency=currency.value)
    await state.set_state(ExpertWithdrawal.BANK)
    await message.answer("Укажите название банка для вывода средств.")


@router.message(StateFilter(ExpertWithdrawal.BANK))
@inject_aiogram
async def withdrawal_bank(
    message: Message,
    state: FSMContext,
    user: UserDto,
    request_withdrawal: FromDishka[RequestExpertWithdrawal],
) -> None:
    bank = " ".join((message.text or "").split())
    if not 2 <= len(bank) <= 128:
        await message.answer("Укажите название банка длиной от 2 до 128 символов.")
        return
    form = await state.get_data()
    withdrawal = await request_withdrawal(
        user,
        RequestExpertWithdrawalDto(
            amount=Decimal(str(form["withdrawal_amount"])),
            currency=Currency.from_code(str(form["withdrawal_currency"])),
            bank_name=bank,
        ),
    )
    await state.clear()
    await message.answer(
        f"Заявка #{withdrawal.id} на вывод {withdrawal.amount} "
        f"{withdrawal.currency.value} отправлена администратору."
    )


@router.callback_query(F.data.startswith("expert_application:"))
@inject_aiogram
async def moderate_expert_application_callback(
    callback: CallbackQuery,
    user: UserDto,
    moderate: FromDishka[ModerateExpertApplication],
    notifier: FromDishka[Notifier],
) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"approve", "reject"} or not parts[2].isdigit():
        await callback.answer("Некорректная заявка", show_alert=True)
        return
    approve = parts[1] == "approve"
    try:
        profile = await moderate(
            user,
            ModerateExpertApplicationDto(expert_profile_id=int(parts[2]), approve=approve),
        )
    except ExpertApplicationAlreadyProcessedError:
        await callback.answer("Эта заявка уже обработана", show_alert=True)
        return
    if isinstance(callback.message, Message):
        await notifier.delete_notification(
            callback.message.chat.id,
            callback.message.message_id,
        )
    await callback.answer(
        f"Анкета {profile.display_name} {'одобрена' if approve else 'отклонена'}",
        show_alert=True,
    )


@router.message(Command("expert_approve"))
@router.message(Command("expert_reject"))
@inject_aiogram
async def moderate_expert_application_command(
    message: Message,
    command: CommandObject,
    user: UserDto,
    moderate: FromDishka[ModerateExpertApplication],
) -> None:
    parts = command.args.split(maxsplit=1) if command.args else []
    if not parts or not parts[0].isdigit():
        await message.answer("Использование: /expert_approve ID или /expert_reject ID причина")
        return
    approve = bool(message.text and message.text.startswith("/expert_approve"))
    reason = parts[1] if len(parts) > 1 else None
    try:
        profile = await moderate(
            user,
            ModerateExpertApplicationDto(int(parts[0]), approve, reason),
        )
    except ExpertApplicationAlreadyProcessedError:
        await message.answer("Эта заявка уже обработана.")
        return
    await message.answer(
        f"Анкета «{profile.display_name}» {'одобрена' if approve else 'отклонена'}."
    )


@router.message(Command("commission"))
@inject_aiogram
async def commission_command(
    message: Message,
    command: CommandObject,
    user: UserDto,
    finance_dao: FromDishka[ExpertFinanceDao],
    set_commission: FromDishka[SetServiceCommission],
) -> None:
    if not user.role.includes(Role.ADMIN):
        raise PermissionDeniedError
    if not command.args:
        settings = await finance_dao.get_settings()
        await message.answer(f"Комиссия сервиса: {settings.commission_percent}%")
        return
    try:
        percent = Decimal(command.args.replace(",", "."))
    except Exception:
        await message.answer("Использование: /commission 20")
        return
    settings = await set_commission(user, SetServiceCommissionDto(percent))
    await message.answer(
        f"Комиссия изменена на {settings.commission_percent}%. "
        "Новые условия применяются только к следующим платежам."
    )


@router.message(Command("withdrawals"))
@inject_aiogram
async def withdrawals_command(
    message: Message,
    user: UserDto,
    finance_dao: FromDishka[ExpertFinanceDao],
) -> None:
    if not user.role.includes(Role.ADMIN):
        raise PermissionDeniedError
    withdrawals = await finance_dao.get_pending_withdrawals()
    if not withdrawals:
        await message.answer("Ожидающих заявок на вывод нет.")
        return
    await message.answer(
        "\n\n".join(
            f"#{item.id} · эксперт {item.expert_profile_id}\n"
            f"{item.amount} {item.currency.value}\nБанк: {item.bank_name}"
            for item in withdrawals
        )
    )


@router.callback_query(F.data.startswith("expert_withdrawal:"))
@inject_aiogram
async def process_withdrawal_callback(
    callback: CallbackQuery,
    user: UserDto,
    process: FromDishka[ProcessExpertWithdrawal],
) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer("Некорректная заявка", show_alert=True)
        return
    approve = parts[1] == "approve"
    withdrawal = await process(
        user,
        ProcessExpertWithdrawalDto(int(parts[2]), approve),
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(
        f"Заявка #{withdrawal.id} {'одобрена' if approve else 'отклонена'}",
        show_alert=True,
    )


@router.message(Command("withdraw_approve"))
@router.message(Command("withdraw_reject"))
@inject_aiogram
async def process_withdrawal_command(
    message: Message,
    command: CommandObject,
    user: UserDto,
    process: FromDishka[ProcessExpertWithdrawal],
) -> None:
    parts = command.args.split(maxsplit=1) if command.args else []
    if not parts or not parts[0].isdigit():
        await message.answer("Использование: /withdraw_approve ID или /withdraw_reject ID причина")
        return
    approve = bool(message.text and message.text.startswith("/withdraw_approve"))
    reason = parts[1] if len(parts) > 1 else None
    withdrawal = await process(
        user,
        ProcessExpertWithdrawalDto(int(parts[0]), approve, reason),
    )
    await message.answer(f"Заявка #{withdrawal.id} {'одобрена' if approve else 'отклонена'}.")


def can_access_consultation(
    user: UserDto,
    consultation: ConsultationDto,
    profile: ExpertProfileDto | None,
) -> bool:
    return (
        consultation.client_telegram_id == user.telegram_id
        or bool(profile and profile.user_telegram_id == user.telegram_id)
        or user.role.includes(Role.ADMIN)
    )


@router.message(Command("expert_edit"))
@inject_aiogram
async def edit_expert_profile(
    message: Message,
    command: CommandObject,
    user: UserDto,
    edit_profile: FromDishka[EditExpertProfile],
) -> None:
    parts = command.args.split(maxsplit=2) if command.args else []
    if len(parts) != 3 or not parts[0].isdigit():
        await message.answer(
            "Использование: /expert_edit ID "
            "name|specialization|short|description|experience|photo ЗНАЧЕНИЕ"
        )
        return
    profile = await edit_profile(
        user,
        EditExpertProfileDto(
            expert_profile_id=int(parts[0]),
            field=parts[1],
            value=parts[2],
        ),
    )
    await message.answer(f"Анкета «{profile.display_name}» обновлена.")


async def _set_consultation_active(
    message: Message,
    command: CommandObject,
    user: UserDto,
    use_case: SetConsultationActive,
    *,
    active: bool,
) -> None:
    if not command.args or not command.args.isdigit():
        command_name = "consultation_restore" if active else "consultation_close"
        await message.answer(f"Использование: /{command_name} ID")
        return
    consultation = await use_case(
        user,
        SetConsultationActiveDto(
            consultation_id=int(command.args),
            active=active,
        ),
    )
    state = "восстановлена" if active else "завершена"
    await message.answer(f"Консультация #{consultation.id} {state}.")


@router.message(Command("consultation_close"))
@inject_aiogram
async def close_consultation(
    message: Message,
    command: CommandObject,
    user: UserDto,
    use_case: FromDishka[SetConsultationActive],
) -> None:
    await _set_consultation_active(message, command, user, use_case, active=False)


@router.message(Command("consultation_restore"))
@inject_aiogram
async def restore_consultation(
    message: Message,
    command: CommandObject,
    user: UserDto,
    use_case: FromDishka[SetConsultationActive],
) -> None:
    await _set_consultation_active(message, command, user, use_case, active=True)


@router.message(Command("retry_consultation"))
@inject_aiogram
async def retry_consultation_topic(
    message: Message,
    command: CommandObject,
    user: UserDto,
    retry_topic: FromDishka[RetryConsultationTopic],
) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /retry_consultation ID")
        return
    consultation = await retry_topic(user, int(command.args))
    await message.answer(f"Тема консультации #{consultation.id} создана.")


@inject
async def on_expert_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_expert: int,
) -> None:
    dialog_manager.dialog_data["expert_profile_id"] = selected_expert
    await dialog_manager.switch_to(Experts.DETAILS)


@inject
async def on_buy_consultation(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    expert_profile_id = int(dialog_manager.dialog_data["expert_profile_id"])
    await dialog_manager.start(
        Subscription.PLANS,
        data={
            "expert_profile_id": expert_profile_id,
            "purchase_type": PurchaseType.NEW,
            "open_purchase_flow": True,
        },
        mode=StartMode.NORMAL,
    )


@inject
async def on_consultation_select(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_consultation: int,
    consultation_dao: FromDishka[ConsultationDao],
    expert_dao: FromDishka[ExpertDao],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    consultation = await consultation_dao.get_by_id(selected_consultation)
    if not consultation:
        raise ValueError("Consultation not found")
    profile = await expert_dao.get_by_id(consultation.expert_profile_id)
    if not can_access_consultation(user, consultation, profile):
        raise PermissionError("Consultation access denied")
    dialog_manager.dialog_data["consultation_id"] = selected_consultation
    await dialog_manager.switch_to(Experts.CHAT)


@inject
async def on_client_message(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    consultation_dao: FromDishka[ConsultationDao],
    expert_dao: FromDishka[ExpertDao],
    uow: FromDishka[UnitOfWork],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    consultation_id = int(dialog_manager.dialog_data["consultation_id"])
    consultation = await consultation_dao.get_by_id(consultation_id)
    if not consultation:
        raise ValueError("Consultation not found")
    expert = await expert_dao.get_by_id(consultation.expert_profile_id)
    is_client = consultation.client_telegram_id == user.telegram_id
    if not can_access_consultation(user, consultation, expert):
        raise PermissionError("Consultation access denied")
    is_expert = bool(expert and expert.user_telegram_id == user.telegram_id)
    if not is_client and not is_expert:
        await message.answer("Администратор может просматривать данные, но не вести консультацию.")
        return
    if not consultation.is_active:
        await message.answer("Консультация сейчас недоступна для сообщений.")
        return
    own_thread_id = consultation.client_thread_id if is_client else consultation.expert_thread_id
    target_chat_id = (
        expert.user_telegram_id if is_client and expert else consultation.client_telegram_id
    )
    target_thread_id = consultation.expert_thread_id if is_client else consultation.client_thread_id
    if own_thread_id is None or target_thread_id is None:
        await message.answer("Темы консультации ещё не созданы. Обратитесь в поддержку.")
        return
    bot = message.bot
    if bot is None:
        raise RuntimeError("Bot instance is unavailable")
    await bot.copy_message(
        chat_id=user.telegram_id,
        message_thread_id=own_thread_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await bot.copy_message(
        chat_id=target_chat_id,
        message_thread_id=target_thread_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    async with uow:
        consultation.last_message_at = datetime_now()
        await consultation_dao.update(consultation)
        await uow.commit()
    await message.answer(
        "Сообщение передано эксперту." if is_client else "Сообщение передано клиенту."
    )


@router.message((F.chat.type == ChatType.PRIVATE) & F.is_topic_message)
@inject_aiogram
async def relay_private_topic_message(
    message: Message,
    user: UserDto,
    consultation_dao: FromDishka[ConsultationDao],
    expert_dao: FromDishka[ExpertDao],
    uow: FromDishka[UnitOfWork],
) -> None:
    if message.message_thread_id is None or message.from_user is None:
        return
    consultation = await consultation_dao.get_by_participant_thread(
        message.chat.id, message.message_thread_id
    )
    if not consultation:
        return
    if not consultation.is_active:
        await message.reply("Срок доступа к этой консультации завершён.")
        return
    expert = await expert_dao.get_by_id(consultation.expert_profile_id)
    if not expert:
        return
    is_client = (
        message.chat.id == consultation.client_telegram_id
        and message.from_user.id == consultation.client_telegram_id
    )
    is_expert = (
        message.chat.id == expert.user_telegram_id
        and message.from_user.id == expert.user_telegram_id
    )
    if not is_client and not is_expert:
        await message.reply("У вас нет доступа к этой консультации.")
        return
    target_chat_id = expert.user_telegram_id if is_client else consultation.client_telegram_id
    target_thread_id = consultation.expert_thread_id if is_client else consultation.client_thread_id
    if target_thread_id is None:
        await message.reply("Связанная тема ещё не создана. Обратитесь в поддержку.")
        return
    bot = message.bot
    if bot is None:
        raise RuntimeError("Bot instance is unavailable")
    await bot.copy_message(
        chat_id=target_chat_id,
        message_thread_id=target_thread_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    async with uow:
        consultation.last_message_at = datetime_now()
        await consultation_dao.update(consultation)
        await uow.commit()
