from typing import Any, Awaitable, Callable, cast

from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    TelegramObject,
)
from dishka import AsyncContainer

from src.application.dto import UserDto
from src.application.use_cases.user.commands.registration import (
    CompleteUserRegistration,
    CompleteUserRegistrationDto,
)
from src.core.constants import CONTAINER_KEY, USER_KEY
from src.core.enums import MiddlewareEventType
from src.telegram.states import Registration

from .base import EventTypedMiddleware


class RegistrationMiddleware(EventTypedMiddleware):
    """Keep every incomplete profile inside the mandatory registration flow."""

    __event_types__ = [MiddlewareEventType.MESSAGE, MiddlewareEventType.CALLBACK_QUERY]

    async def middleware_logic(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = cast(UserDto | None, data.get(USER_KEY))
        if user is None or user.is_registration_completed:
            return await handler(event, data)

        state = cast(FSMContext, data["state"])
        current_state = await state.get_state()

        if isinstance(event, CallbackQuery):
            await event.answer("Сначала завершите регистрацию", show_alert=True)
            bot = event.bot
            if bot is None:
                return None
            await bot.send_message(
                user.telegram_id,
                "Введите ФИО:"
                if current_state != Registration.PHONE.state
                else "Отправьте номер телефона:",
                reply_markup=self._phone_keyboard()
                if current_state == Registration.PHONE.state
                else None,
            )
            if current_state not in {Registration.NAME.state, Registration.PHONE.state}:
                await state.set_state(Registration.NAME)
            return None

        if not isinstance(event, Message):
            return None

        if current_state == Registration.NAME.state:
            return await self._accept_name(event, state)
        if current_state == Registration.PHONE.state:
            return await self._accept_phone(event, state, data, user)

        await state.clear()
        await state.set_state(Registration.NAME)
        await event.answer(
            "Добро пожаловать! Для доступа к консультациям сначала укажите ваше ФИО.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return None

    async def _accept_name(self, message: Message, state: FSMContext) -> None:
        full_name = " ".join((message.text or "").split())
        if len(full_name) < 3 or len(full_name) > 128 or any(char.isdigit() for char in full_name):
            await message.answer("Введите корректное ФИО текстом (от 3 до 128 символов).")
            return
        await state.update_data(registration_full_name=full_name)
        await state.set_state(Registration.PHONE)
        await message.answer(
            "Теперь отправьте номер телефона. Можно нажать кнопку ниже или ввести номер вручную.",
            reply_markup=self._phone_keyboard(),
        )

    async def _accept_phone(
        self,
        message: Message,
        state: FSMContext,
        middleware_data: dict[str, Any],
        user: UserDto,
    ) -> None:
        if message.contact and message.contact.user_id not in {None, user.telegram_id}:
            await message.answer("Отправьте, пожалуйста, именно свой номер телефона.")
            return
        phone = message.contact.phone_number if message.contact else (message.text or "")
        digits = "".join(character for character in phone if character.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            await message.answer("Номер не распознан. Введите его в формате +79991234567.")
            return

        state_data = await state.get_data()
        full_name = str(state_data.get("registration_full_name", "")).strip()
        if not full_name:
            await state.set_state(Registration.NAME)
            await message.answer("Сначала введите ФИО.", reply_markup=ReplyKeyboardRemove())
            return

        container = cast(AsyncContainer, middleware_data[CONTAINER_KEY])
        complete_registration = await container.get(CompleteUserRegistration)
        updated_user = await complete_registration(
            user, CompleteUserRegistrationDto(full_name=full_name, phone=f"+{digits}")
        )
        middleware_data[USER_KEY] = updated_user
        await state.clear()
        await message.answer(
            "Регистрация завершена. Теперь вам доступны консультации с экспертами. Нажмите /start.",
            reply_markup=ReplyKeyboardRemove(),
        )

    @staticmethod
    def _phone_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
