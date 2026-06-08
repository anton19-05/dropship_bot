from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import msg_manager


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    await msg_manager.clear(context.bot, chat_id, user_id)

    user_data = context.user_data.get(f"user_data_{user_id}", {})
    cart_count = sum(item["quantity"] for item in context.user_data.get(
        f"cart_{user_id}", {}).values())
    fav_count = len(context.user_data.get(f"favorites_{user_id}", []))

    text = f"""
👤 *МОЙ ПРОФИЛЬ* 👤

📋 *Личные данные:*
• Имя: {user_data.get('name', 'Не указано')}
• Телефон: {user_data.get('phone', 'Не указан')}
• Адрес: {user_data.get('address', 'Не указан')}

📊 *Статистика:*
• 🛒 В корзине: {cart_count} товаров
• ❤️ В избранном: {fav_count} товаров
    """

    keyboard = [
        [InlineKeyboardButton("🛒 Корзина", callback_data="view_cart_from_profile"),
         InlineKeyboardButton("❤️ Избранное", callback_data="view_favorites")],
        [InlineKeyboardButton("📝 Редактировать профиль",
                              callback_data="edit_profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
    ]

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    keyboard = [
        [InlineKeyboardButton("👤 Имя", callback_data="edit_name")],
        [InlineKeyboardButton("📞 Телефон", callback_data="edit_phone")],
        [InlineKeyboardButton("📍 Адрес", callback_data="edit_address")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]

    await msg_manager.clear(context.bot, chat_id, user_id)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📝 *РЕДАКТИРОВАНИЕ ПРОФИЛЯ*\n\nВыберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    context.user_data["editing_field"] = "name"
    await msg_manager.clear(context.bot, chat_id, user_id)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📝 *Введите ваше имя*\n\nПример: Иван Иванов",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]])
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    context.user_data["editing_field"] = "phone"
    await msg_manager.clear(context.bot, chat_id, user_id)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📞 *Введите ваш номер телефона*\n\nФормат: +79991234567",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]])
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    context.user_data["editing_field"] = "address"
    await msg_manager.clear(context.bot, chat_id, user_id)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📍 *Введите ваш адрес*\n\nПример: Москва, ул. Ленина 5",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]])
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def handle_profile_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get("editing_field")
    if not field:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    value = update.message.text.strip()

    user_data_key = f"user_data_{user_id}"
    if user_data_key not in context.user_data:
        context.user_data[user_data_key] = {}
    context.user_data[user_data_key][field] = value
    context.user_data.pop("editing_field", None)

    try:
        await update.message.delete()
    except:
        pass

    await msg_manager.clear(context.bot, chat_id, user_id)
    await profile(update, context)
