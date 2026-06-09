from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.payments import PremiumPaymentOption


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Пост")
    builder.button(text="🪝 Хуки")
    builder.button(text="📅 План на 7 дней")
    builder.button(text="✍️ Подпись")
    builder.button(text="🎯 Моя ниша")
    builder.button(text="⭐ Премиум")
    builder.button(text="📊 Статус")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def premium_keyboard(options: tuple[PremiumPaymentOption, ...]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(
            text=option.button_label,
            callback_data=f"pay:{option.currency.value}",
        )
    builder.adjust(1)
    return builder.as_markup()
