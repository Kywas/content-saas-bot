from __future__ import annotations

import logging
from enum import StrEnum

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.config import Settings, load_settings
from app.content import ContentType, generate_content
from app.database import Database
from app.keyboards import main_menu_keyboard, premium_keyboard
from app.payments import (
    PayCurrency,
    available_payment_options,
    get_payment_option,
    parse_premium_payload,
    premium_payload,
)
from app.premium import PREMIUM_PERIOD_DAYS, format_premium_until

logger = logging.getLogger(__name__)


class UserState(StatesGroup):
    waiting_niche = State()


class MenuAction(StrEnum):
    POST = "📝 Пост"
    HOOKS = "🪝 Хуки"
    PLAN = "📅 План на 7 дней"
    CAPTION = "✍️ Подпись"
    IDEAS = "💡 Идеи"
    REELS = "🎬 Reels"
    STORIES = "📲 Сторис"
    NICHE = "🎯 Моя ниша"
    PREMIUM = "⭐ Премиум"
    STATUS = "📊 Статус"


GENERATE_ACTIONS = frozenset({
    MenuAction.POST,
    MenuAction.HOOKS,
    MenuAction.PLAN,
    MenuAction.CAPTION,
    MenuAction.IDEAS,
    MenuAction.REELS,
    MenuAction.STORIES,
})


WELCOME_TEXT = (
    "👋 <b>Content Factory</b> — бот, который пишет контент за тебя.\n\n"
    "Что умею:\n"
    "• посты, хуки, подписи\n"
    "• план на 7 дней\n"
    "• 10 идей для контента\n"
    "• сценарии Reels и Stories\n\n"
    "Сначала укажи нишу — кнопка «🎯 Моя ниша».\n"
    "Бесплатно: {limit} генераций в день.\n"
    "Премиум: безлимит на 30 дней."
)


def _content_type_for_action(action: str) -> ContentType | None:
    mapping = {
        MenuAction.POST: ContentType.POST,
        MenuAction.HOOKS: ContentType.HOOKS,
        MenuAction.PLAN: ContentType.PLAN,
        MenuAction.CAPTION: ContentType.CAPTION,
        MenuAction.IDEAS: ContentType.IDEAS,
        MenuAction.REELS: ContentType.REELS,
        MenuAction.STORIES: ContentType.STORIES,
    }
    return mapping.get(action)  # type: ignore[arg-type]


async def _ensure_user(db: Database, message: Message) -> None:
    if message.from_user is None:
        return
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )


async def _check_limit(db: Database, settings: Settings, user_id: int) -> str | None:
    if await db.is_premium(user_id):
        return None
    used = await db.get_daily_usage(user_id)
    if used >= settings.free_daily_limit:
        return (
            f"Лимит на сегодня исчерпан ({settings.free_daily_limit} генераций).\n"
            "Оформи ⭐ Премиум — безлимит на 30 дней."
        )
    return None


async def run_bot() -> None:
    settings = load_settings()
    db = Database(settings.database_path)
    await db.init()

    session = AiohttpSession(proxy=settings.proxy_url) if settings.proxy_url else None
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _ensure_user(db, message)
        await message.answer(
            WELCOME_TEXT.format(limit=settings.free_daily_limit),
            reply_markup=main_menu_keyboard(),
        )

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        if message.from_user is None or message.from_user.id not in settings.admin_ids:
            return
        stats = await db.get_stats()
        await message.answer(
            "📈 <b>Статистика</b>\n\n"
            f"Пользователей: {stats['total_users']}\n"
            f"Активный премиум: {stats['active_premium']}\n"
            f"Платежей: {stats['total_payments']}\n"
            f"Выручка (мин. ед.): {stats['total_revenue']}\n"
            f"Запросов сегодня: {stats['today_requests']}"
        )

    @dp.message(F.text == MenuAction.STATUS)
    async def show_status(message: Message) -> None:
        if message.from_user is None:
            return
        await _ensure_user(db, message)
        user = await db.get_user(message.from_user.id)
        premium = await db.is_premium(message.from_user.id)
        used = await db.get_daily_usage(message.from_user.id)
        niche = user.niche if user and user.niche else "не указана"
        until = format_premium_until(user.premium_until if user else None)

        if premium:
            limit_line = "Лимит: безлимит (премиум)"
        else:
            left = max(0, settings.free_daily_limit - used)
            limit_line = f"Лимит сегодня: {left} из {settings.free_daily_limit}"

        await message.answer(
            f"📊 <b>Твой статус</b>\n\n"
            f"Ниша: {niche}\n"
            f"Премиум: {'да' if premium else 'нет'}\n"
            f"Действует до: {until if premium else '—'}\n"
            f"{limit_line}"
        )

    @dp.message(F.text == MenuAction.NICHE)
    async def ask_niche(message: Message, state: FSMContext) -> None:
        await _ensure_user(db, message)
        await state.set_state(UserState.waiting_niche)
        await message.answer(
            "Напиши свою нишу одним сообщением.\n"
            "Например: <i>фитнес-коучинг</i>, <i>недвижимость</i>, <i>SMM</i>"
        )

    @dp.message(UserState.waiting_niche)
    async def save_niche(message: Message, state: FSMContext) -> None:
        if message.from_user is None or not message.text:
            return
        niche = message.text.strip()[:80]
        await db.set_niche(message.from_user.id, niche)
        await state.clear()
        await message.answer(f"✅ Ниша сохранена: <b>{niche}</b>\nТеперь жми любую кнопку генерации.")

    @dp.message(F.text == MenuAction.PREMIUM)
    async def show_premium(message: Message) -> None:
        if message.from_user is None:
            return
        options = available_payment_options(settings)
        if not options:
            await message.answer(
                "Оплата пока не подключена.\n"
                "Админу: включи ENABLE_PAYMENTS=true и настрой токены в .env"
            )
            return
        await message.answer(
            f"⭐ <b>Премиум на {PREMIUM_PERIOD_DAYS} дней</b>\n\n"
            "• безлимит генераций\n"
            "• приоритетные шаблоны\n"
            "• без рекламы\n\n"
            "Выбери способ оплаты:",
            reply_markup=premium_keyboard(options),
        )

    @dp.callback_query(F.data.startswith("pay:"))
    async def start_payment(callback: CallbackQuery, bot: Bot) -> None:
        if callback.from_user is None or callback.message is None:
            return
        currency_raw = callback.data.split(":", 1)[1]
        try:
            currency = PayCurrency(currency_raw)
        except ValueError:
            await callback.answer("Неизвестный способ оплаты", show_alert=True)
            return

        option = get_payment_option(settings, currency)
        if option is None:
            await callback.answer("Оплата недоступна", show_alert=True)
            return

        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title="Content Factory Premium",
            description=f"Безлимит генераций на {PREMIUM_PERIOD_DAYS} дней",
            payload=premium_payload(currency),
            provider_token=option.provider_token,
            currency=option.telegram_currency,
            prices=[LabeledPrice(label="Premium 30 days", amount=option.invoice_amount)],
        )
        await callback.answer()

    @dp.pre_checkout_query()
    async def pre_checkout(query: PreCheckoutQuery) -> None:
        currency = parse_premium_payload(query.invoice_payload)
        if currency is None:
            await query.answer(ok=False, error_message="Неверный платёж")
            return
        if get_payment_option(settings, currency) is None:
            await query.answer(ok=False, error_message="Оплата недоступна")
            return
        await query.answer(ok=True)

    @dp.message(F.successful_payment)
    async def successful_payment(message: Message) -> None:
        if message.from_user is None or message.successful_payment is None:
            return
        currency = parse_premium_payload(message.successful_payment.invoice_payload)
        if currency is None:
            return
        await db.grant_premium(message.from_user.id)
        await db.record_payment(
            message.from_user.id,
            currency.value,
            message.successful_payment.total_amount,
        )
        user = await db.get_user(message.from_user.id)
        until = format_premium_until(user.premium_until if user else None)
        await message.answer(
            f"🎉 Премиум активирован до <b>{until}</b>!\n"
            "Теперь генерации без лимита."
        )

    @dp.message(F.text.in_(GENERATE_ACTIONS))
    async def generate(message: Message) -> None:
        if message.from_user is None or message.text is None:
            return
        await _ensure_user(db, message)
        user = await db.get_user(message.from_user.id)
        if not user or not user.niche:
            await message.answer("Сначала укажи нишу — кнопка «🎯 Моя ниша».")
            return

        limit_msg = await _check_limit(db, settings, message.from_user.id)
        if limit_msg:
            await message.answer(limit_msg)
            return

        content_type = _content_type_for_action(message.text)
        if content_type is None:
            return

        wait_msg = await message.answer("⏳ Генерирую...")
        try:
            result = await generate_content(settings, content_type, user.niche)
            await db.increment_usage(message.from_user.id)
            await wait_msg.edit_text(result)
        except Exception:
            logger.exception("Content generation failed for user %s", message.from_user.id)
            await wait_msg.edit_text("Не удалось сгенерировать. Попробуй ещё раз через минуту.")

    logger.info("Content Factory bot started")
    await dp.start_polling(bot)
