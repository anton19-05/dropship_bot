import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import msg_manager
from storage import save_user_data_sync, get_user_data

editing_state = {}


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    await msg_manager.clear(context.bot, chat_id, user_id)

    user_data = get_user_data(user_id, context)
    
    cart_count = sum(item["quantity"] for item in context.user_data.get(f"cart_{user_id}", {}).values())
    fav_count = len(context.user_data.get(f"favorites_{user_id}", []))

    is_profile_complete = all([
        user_data.get('last_name'),
        user_data.get('first_name'),
        user_data.get('phone'),
        user_data.get('country'),
        user_data.get('region'),
        user_data.get('city'),
        user_data.get('postal_code'),
        user_data.get('address'),
        user_data.get('email')
    ])

    profile_status = "✅ *Профиль полностью заполнен*" if is_profile_complete else "⚠️ *Профиль заполнен не полностью*"

    text = f"""
👤 *МОЙ ПРОФИЛЬ* 👤

{profile_status}

📋 *Личные данные:*
• Фамилия: {user_data.get('last_name', 'Не указано')}
• Имя: {user_data.get('first_name', 'Не указано')}
• Телефон: {user_data.get('phone', 'Не указан')}
• Страна: {user_data.get('country', 'Не указана')}
• Регион/Область: {user_data.get('region', 'Не указан')}
• Город: {user_data.get('city', 'Не указан')}
• Индекс: {user_data.get('postal_code', 'Не указан')}
• Адрес: {user_data.get('address', 'Не указан')}
• Email: {user_data.get('email', 'Не указан')}

📊 *Статистика:*
• 🛒 В корзине: {cart_count} товаров
• ❤️ В избранном: {fav_count} товаров
    """

    keyboard = [
        [InlineKeyboardButton("🛒 Корзина", callback_data="view_cart_from_profile"),
         InlineKeyboardButton("❤️ Избранное", callback_data="view_favorites")],
        [InlineKeyboardButton("📝 Заполнить профиль", callback_data="edit_profile_start")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
    ]

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def edit_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    await msg_manager.clear(context.bot, chat_id, user_id)

    editing_state[user_id] = {"step": "waiting_for_data"}

    callback_data = query.data
    is_change = callback_data == "edit_profile_change"

    instruction = """
📝 *ИНСТРУКЦИЯ ПО ЗАПОЛНЕНИЮ ПРОФИЛЯ*

Напишите одним сообщением через запятую ВСЕ данные в следующем порядке:

1️⃣ Фамилия
2️⃣ Имя
3️⃣ Телефон (в формате +7...)
4️⃣ Страна
5️⃣ Регион / Область
6️⃣ Город
7️⃣ Индекс
8️⃣ Адрес (улица, дом, корпус, квартира)
9️⃣ Email

📌 *Пример правильного заполнения:*
Смирнова, Ольга, +79077777777, Россия, Московская область, Красногорск, 143400, ул. Ленина, д. 10, кв. 25, olga@mail.ru

⚠️ *Важно:*
• Все 9 пунктов обязательны для заполнения
• Телефон должен начинаться с +7
• Email должен быть корректным
• Не используйте нецензурную лексику
    """

    if is_change:
        instruction += "\n\n✏️ *Напишите ниже новые данные для замены старых.*"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 В профиль", callback_data="profile")],
        [InlineKeyboardButton("🔄 Сменить данные", callback_data="edit_profile_change")]
    ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=instruction,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_profile_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if user_id not in editing_state:
        return
    
    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(",")]
    
    if len(parts) < 9:
        await update.message.reply_text(
            "❌ *Недостаточно данных!*\n\nПожалуйста, введите ВСЕ 9 пунктов через запятую.\n\n"
            "📌 *Пример:*\nСмирнова, Ольга, +79077777777, Россия, Московская область, Красногорск, 143400, ул. Ленина, д. 10, кв. 25, olga@mail.ru",
            parse_mode="Markdown"
        )
        return
    
    if len(parts) > 9:
        await update.message.reply_text(
            "❌ *Слишком много данных!*\n\nПожалуйста, введите ровно 9 пунктов через запятую.",
            parse_mode="Markdown"
        )
        return
    
    last_name = parts[0]
    first_name = parts[1]
    phone = parts[2]
    country = parts[3]
    region = parts[4]
    city = parts[5]
    postal_code = parts[6]
    address = parts[7]
    email = parts[8]
    
    bad_words = ['мат', 'хер', 'хуй', 'пизда', 'бля', 'залупа', 'мудак', 'сука', 'ёба', 'ебан']
    all_text = text.lower()
    for bad_word in bad_words:
        if bad_word in all_text:
            await update.message.reply_text(
                "❌ *Некорректные данные!*\n\nПожалуйста, используйте культурную лексику.",
                parse_mode="Markdown"
            )
            return
    
    phone_pattern = re.compile(r'^\+7\d{10}$')
    if not phone_pattern.match(phone):
        await update.message.reply_text(
            "❌ *Неверный формат телефона!*\n\nТелефон должен быть в формате +7XXXXXXXXXX (10 цифр после +7).\n\nПример: +79077777777",
            parse_mode="Markdown"
        )
        return
    
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(email):
        await update.message.reply_text(
            "❌ *Неверный формат email!*\n\nПример: example@mail.ru",
            parse_mode="Markdown"
        )
        return
    
    if not postal_code.isdigit():
        await update.message.reply_text(
            "❌ *Неверный формат индекса!*\n\nИндекс должен состоять только из цифр.",
            parse_mode="Markdown"
        )
        return
    
    user_data = {
        "last_name": last_name,
        "first_name": first_name,
        "phone": phone,
        "country": country,
        "region": region,
        "city": city,
        "postal_code": postal_code,
        "address": address,
        "email": email
    }
    
    save_user_data_sync(user_id, user_data, context)
    
    del editing_state[user_id]
    
    try:
        await update.message.delete()
    except:
        pass
    
    await msg_manager.clear(context.bot, chat_id, user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Перейти в профиль", callback_data="profile")]
    ])
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ *Данные профиля успешно сохранены!*\n\nВаша информация обновлена.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )