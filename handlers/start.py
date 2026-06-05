import os
from telegram import Update
from telegram.ext import ContextTypes
from keyboards import get_main_menu
from models import msg_manager


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await msg_manager.clear(context.bot, chat_id, user_id)

    # Отправляем только текст (без фото)
    await update.message.reply_text(
        "🌸 *ДОБРО ПОЖАЛОВАТЬ В MEGA SHOP!* 🌸\n\n"
        "🇨🇳 *Товары из Китая*\n\n"
        "💰 *Цены ниже рынка на 30-50%*\n"
        "📦 *Срок доставки:* 15-25 дней\n"
        "🌞 *Летняя распродажа!*\n"
        "🔥 *Скидки до 60% на все товары*\n\n"
        "👇 *Выберите действие:* 👇",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


async def main_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    await msg_manager.clear(context.bot, chat_id, user_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="🌸 *ДОБРО ПОЖАЛОВАТЬ В MEGA SHOP!* 🌸\n\n👇 Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
