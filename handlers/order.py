import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager
from config import ADMIN_ID
from debug import info, debug, error, success, warning
from handlers.payment import create_payment

pending_orders = {}


async def get_profile_data(user_id, context):
    """Получает данные профиля пользователя"""
    return context.user_data.get(f"user_data_{user_id}", {})


async def is_profile_complete(user_id, context):
    """Проверяет, заполнен ли профиль полностью"""
    user_data = await get_profile_data(user_id, context)
    return all([
        user_data.get('last_name'),
        user_data.get('first_name'),
        user_data.get('phone'),
        user_data.get('address')
    ])


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_id = query.data.replace("order_", "")
    product = products_manager.get_by_id(product_id)
    
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    context.user_data[f"order_product_{user_id}"] = product_id
    
    attrs = product.get_attributes()
    keyboard = []
    
    # 1. РАЗМЕРЫ (если есть, с галочками)
    if product.has_sizes:
        sizes = product.get_sizes()
        size_row = []
        selected_size = context.user_data.get(f"order_size_{user_id}")
        for size in sizes:
            size_value = size["value"] if isinstance(size, dict) else size
            marker = "✅ " if str(selected_size) == str(size_value) else ""
            size_row.append(InlineKeyboardButton(
                f"{marker}{size_value}",
                callback_data=f"osz_{product_id}_{size_value}"
            ))
            if len(size_row) == 3:
                keyboard.append(size_row)
                size_row = []
        if size_row:
            keyboard.append(size_row)
    
    # 2. ОСТАЛЬНЫЕ АТРИБУТЫ (с галочками)
    for key, value in attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, list):
            row = []
            short_key = key[:3]
            for item in value:
                item_str = str(item)
                selected = context.user_data.get(f"order_attr_{key}_{user_id}") == item_str
                marker = "✅ " if selected else ""
                row.append(InlineKeyboardButton(
                    f"{marker}{item_str}",
                    callback_data=f"oat_{product_id}_{short_key}_{item_str}"
                ))
            if row:
                keyboard.append([InlineKeyboardButton(f"📌 {key}:", callback_data="noop")])
                for i in range(0, len(row), 3):
                    keyboard.append(row[i:i+3])
    
    # 3. КНОПКА "ДАЛЕЕ"
    if keyboard:
        keyboard.append([InlineKeyboardButton("✅ Далее", callback_data=f"ord_{product_id}")])
    else:
        await show_order_form(update, context, product, user_id)
        return
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product_id}")])
    
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"📝 *ОФОРМЛЕНИЕ ЗАКАЗА*\n\n"
             f"👟 {product.name}\n"
             f"💰 {product.price} руб\n\n"
             f"👇 Выберите параметры:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_order_size_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, product, user_id):
    """Показывает выбор размера перед заказом"""
    query = update.callback_query
    
    try:
        await query.message.delete()
    except:
        pass
    
    sizes = product.get_sizes()
    size_buttons = []
    row = []
    
    for i, size_data in enumerate(sizes):
        size_value = size_data["value"]
        available = size_data.get("available", True)
        
        if available:
            display = str(size_value)
            callback = f"order_size_{product.id}_{size_value}"
        else:
            display = f"❌ {size_value}"
            callback = "noop"
        
        row.append(InlineKeyboardButton(display, callback_data=callback))
        if (i + 1) % 3 == 0:
            size_buttons.append(row)
            row = []
    if row:
        size_buttons.append(row)
    
    size_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")])
    
    color = context.user_data.get(f"order_color_{user_id}", "белый")
    
    text = f"📝 *ОФОРМЛЕНИЕ ЗАКАЗА*\n\n"
    text += f"👟 *{product.name}*\n"
    text += f"🎨 Цвет: {color}\n"
    text += f"💰 Цена: {product.price} руб\n\n"
    text += f"👇 *Выберите размер:*"
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(size_buttons)
    )

async def show_order_form(update: Update, context: ContextTypes.DEFAULT_TYPE, product, user_id, size=None):
    """Показывает форму для ввода данных или использует данные из профиля"""
    query = update.callback_query
    
    if size:
        context.user_data[f"order_size_{user_id}"] = size
    
    final_size = context.user_data.get(f"order_size_{user_id}")
    final_color = context.user_data.get(f"order_color_{user_id}")
    final_attrs = context.user_data.get(f"order_attrs_{user_id}", {})

    try:
        await query.message.delete()
    except:
        pass
    
    # Проверяем, заполнен ли профиль
    profile_complete = await is_profile_complete(user_id, context)
    
    if profile_complete:
        await auto_order_from_profile(update, context, product, user_id, final_size, final_color)
    else:
        context.user_data[f"ordering_{user_id}"] = True
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад к выбору размера", callback_data=f"back_to_size_{product.id}")]
        ])
        
        attributes_text = ""
        if final_color:
            attributes_text += f"🎨 Цвет: {final_color}\n"
        if final_size:
            attributes_text += f"📏 Размер: {final_size}\n"
        for key, value in final_attrs.items():
            attributes_text += f"📌 {key}: {value}\n"
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📝 *ОФОРМЛЕНИЕ ЗАКАЗА*\n\n"
            f"👟 Товар: {product.name}\n"
            f"{attributes_text}"
            f"💰 Цена: {product.price} руб\n\n"
            f"⚠️ *Ваш профиль не заполнен!*\n\n"
            f"Пожалуйста, заполните профиль в разделе 👤 *Мой профиль* или введите данные сейчас.\n\n"
            f"Напишите одним сообщением через запятую:\n\n"
            f"1️⃣ Фамилия\n"
            f"2️⃣ Имя\n"
            f"3️⃣ Телефон (+7...)\n"
            f"4️⃣ Страна\n"
            f"5️⃣ Регион / Область\n"
            f"6️⃣ Город\n"
            f"7️⃣ Индекс\n"
            f"8️⃣ Адрес\n"
            f"9️⃣ Email\n\n"
            f"📌 *Пример:* Смирнова, Ольга, +79077777777, Россия, Московская область, Красногорск, 143400, ул. Ленина, д. 10, кв. 25, olga@mail.ru",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def auto_order_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, product, user_id, size, color):
    """Автоматическое оформление заказа из данных профиля"""
    query = update.callback_query
    
    profile = await get_profile_data(user_id, context)
    final_attrs = context.user_data.get(f"order_attrs_{user_id}", {})
    
    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "size": size,
        "color": color,
        "last_name": profile.get('last_name', 'не указана'),
        "first_name": profile.get('first_name', 'не указано'),
        "phone": profile.get('phone', 'не указан'),
        "country": profile.get('country', 'не указана'),
        "region": profile.get('region', 'не указан'),
        "city": profile.get('city', 'не указан'),
        "postal_code": profile.get('postal_code', 'не указан'),
        "address": profile.get('address', 'не указан'),
        "email": profile.get('email', 'не указан'),
        "user_id": user_id,
        "username": update.effective_user.username
    }
    
    # ✅ Добавляем все атрибуты из заказа
    for key, value in final_attrs.items():
        order_info[key] = value
    
    # ✅ СОХРАНЯЕМ ЗАКАЗ ДЛЯ ОТПРАВКИ ПОСЛЕ ОПЛАТЫ
    import time
    order_id = f"{user_id}_{int(time.time())}"
    
    context.user_data[f"payment_{order_id}"] = {
        "order_id": order_id,
        "amount": product.price,
        "description": product.name,
        "user_id": user_id,
        "status": "pending",
        "created_at": time.time(),
        "order_info": order_info
    }
    
    print(f"✅ auto_order_from_profile: order_info сохранён: {order_info}")
    
    # ✅ СОЗДАЁМ ПЛАТЁЖ
    from handlers.payment import create_payment
    
    await create_payment(
        update=update,
        context=context,
        amount=product.price,
        order_id=order_id,
        description=product.name,
        order_info=order_info
    )
    
    context.user_data.pop(f"order_product_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)
    context.user_data.pop(f"order_attrs_{user_id}", None)


async def back_to_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к выбору размера из формы заказа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_id = query.data.replace("back_to_size_", "")
    
    product = products_manager.get_by_id(product_id)
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    # Очищаем данные заказа
    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)
    
    # Показываем выбор размера
    await show_order_size_selection(update, context, product, user_id)


async def order_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get(f"ordering_{user_id}"):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(",")]

    if len(parts) < 3:
        await update.message.reply_text(
            "❌ *Недостаточно данных!*\n\nНапишите ФИО, телефон и адрес через запятую",
            parse_mode="Markdown"
        )
        return

    product_id = context.user_data.get(f"order_product_{user_id}")
    product = products_manager.get_by_id(product_id)

    if not product:
        await update.message.reply_text("❌ Товар не найден!")
        return

    # Получаем выбранные атрибуты
    color = context.user_data.get(f"color_{user_id}", "белый")
    size = context.user_data.get(f"order_size_{user_id}")
    
    # Получаем все выбранные атрибуты
    attrs = product.get_attributes()
    selected_attrs = {}
    for key in attrs.keys():
        if key not in ["colors", "sizes"]:
            attr_value = context.user_data.get(f"order_attr_{key}_{user_id}")
            if attr_value:
                selected_attrs[key] = attr_value

    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "color": color,
        "size": size,
        **selected_attrs,
        "fio": parts[0],
        "phone": parts[1],
        "address": parts[2],
        "user_id": user_id,
        "username": update.effective_user.username
    }

    order_id = f"{user_id}_{int(time.time())}"
    context.user_data[f"payment_{order_id}"] = {
        "order_id": order_id,
        "amount": product.price,
        "description": product.name,
        "user_id": user_id,
        "status": "pending",
        "created_at": time.time(),
        "order_info": order_info
    }
    
    await create_payment(
        update=update,
        context=context,
        amount=product.price,
        order_id=order_id,
        description=product.name,
        order_info=order_info
    )

    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_product_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)

async def order_select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.replace("osz_", "")
    parts = data.split("_")
    
    product_id = parts[0]
    size = parts[1]
    
    context.user_data[f"order_size_{user_id}"] = size
    
    await order_start(update, context)


async def order_select_attr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.replace("oat_", "")
    parts = data.split("_")
    
    product_id = parts[0]
    attr_key = parts[1]
    attr_value = "_".join(parts[2:])
    
    context.user_data[f"order_attr_{attr_key}_{user_id}"] = attr_value
    
    await order_start(update, context)


async def order_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_id = query.data.replace("ord_", "")
    product = products_manager.get_by_id(product_id)
    
    if product:
        await show_order_form(update, context, product, user_id)