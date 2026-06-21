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
    
    # ✅ СОБИРАЕМ ВСЕ АТРИБУТЫ
    attrs = product.get_attributes()
    attrs_text = ""
    
    # 1. Цвет
    color = context.user_data.get(f"color_{user_id}", "белый")
    attrs_text += f"🎨 Цвет: {color}\n"
    
    # 2. Главный атрибут
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            main_value = context.user_data.get(f"attr_{key}_{user_id}")
            if main_value:
                attrs_text += f"📌 {key}: {main_value}\n"
            break
    
    # 3. Остальные атрибуты (списки)
    for key, value in attrs.items():
        if key == "colors":
            continue
        if isinstance(value, list):
            attrs_text += f"📌 {key}: {', '.join(value)}\n"
    
    # ✅ УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"📝 *ОФОРМЛЕНИЕ ЗАКАЗА*\n\n"
            f"👟 Товар: {product.name}\n"
            f"{attrs_text}"
            f"💰 Цена: {product.price} руб\n\n"
            f"Напишите ФИО, телефон и адрес через запятую"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")]
        ])
    )
    
    # Устанавливаем флаг, что пользователь в процессе заказа
    context.user_data[f"ordering_{user_id}"] = True
    context.user_data[f"order_product_{user_id}"] = product_id


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


async def order_select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора размера для заказа"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.replace("order_size_", "")
    
    last_underscore = data.rfind("_")
    
    if last_underscore == -1:
        await query.answer("❌ Ошибка выбора размера!", show_alert=True)
        return
    
    product_id = data[:last_underscore]
    size = data[last_underscore + 1:]
    
    product = products_manager.get_by_id(product_id)
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    if not product.is_size_available(size):
        await query.answer("❌ Этот размер отсутствует в наличии!", show_alert=True)
        return
    
    context.user_data[f"order_size_{user_id}"] = size
    
    await show_order_form(update, context, product, user_id, size)


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
    """Обработка введённых данных заказа (если профиль не заполнен)"""
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
    
    # Получаем главный атрибут
    attrs = product.get_attributes()
    main_attr_value = None
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            main_attr_value = context.user_data.get(f"attr_{key}_{user_id}")
            break

    # Сохраняем заказ
    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "color": color,
        "main_attr": main_attr_value,
        "fio": parts[0],
        "phone": parts[1],
        "address": parts[2],
        "user_id": user_id,
        "username": update.effective_user.username
    }

    # ✅ СОХРАНЯЕМ ЗАКАЗ ДЛЯ ОТПРАВКИ ПОСЛЕ ОПЛАТЫ
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
    
    print(f"✅ order_info сохранён: {order_info}")

    # ✅ СОЗДАЁМ ПЛАТЁЖ
    await create_payment(
        update=update,
        context=context,
        amount=product.price,
        order_id=order_id,
        description=product.name,
        order_info=order_info
    )

    # Очищаем данные заказа
    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_product_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)