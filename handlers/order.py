from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager
from config import ADMIN_ID
from debug import info, debug, error, success, warning


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало оформления заказа — сначала выбор размера (если есть)"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    product_id = query.data.replace("order_", "")

    info("ORDER", f"Начало оформления заказа", {
         "user_id": user_id, "product_id": product_id})

    product = products_manager.get_by_id(product_id)
    if not product:
        error("ORDER", f"Товар {product_id} не найден")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Сохраняем ID товара
    context.user_data[f"order_product_{user_id}"] = product_id
    
    # Сохраняем текущий цвет (из карточки товара)
    current_color = context.user_data.get(f"color_{user_id}", "белый")
    context.user_data[f"order_color_{user_id}"] = current_color
    
    # Проверяем, есть ли у товара размеры
    if product.has_sizes:
        # Показываем выбор размера
        await show_order_size_selection(update, context, product, user_id)
    else:
        # Если нет размеров — сразу переходим к форме
        await show_order_form(update, context, product, user_id, size=None)


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
            # 👇 ДОБАВЬТЕ ЭТУ СТРОКУ ДЛЯ ДИАГНОСТИКИ
            print(f"🔘 Создана кнопка: {display} -> callback: {callback}")
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
    print("🎯 order_select_size ВЫЗВАНА!")
    query = update.callback_query
    await query.answer()
    
    print(f"📦 query.data = {query.data}")
    
    user_id = query.from_user.id
    data = query.data.replace("order_size_", "")
    
    print(f"📦 data после replace = {data}")
    
    last_underscore = data.rfind("_")
    print(f"📦 last_underscore = {last_underscore}")
    
    if last_underscore == -1:
        print("❌ Нет подчёркивания!")
        await query.answer("❌ Ошибка выбора размера!", show_alert=True)
        return
    
    product_id = data[:last_underscore]
    size = data[last_underscore + 1:]
    
    print(f"📦 product_id = {product_id}, size = {size}")
    
    product = products_manager.get_by_id(product_id)
    if not product:
        print(f"❌ Товар {product_id} не найден!")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    print(f"✅ Товар найден: {product.name}")
    
    if not product.is_size_available(size):
        print(f"❌ Размер {size} отсутствует в наличии!")
        await query.answer("❌ Этот размер отсутствует в наличии!", show_alert=True)
        return
    
    print(f"✅ Размер {size} доступен")
    
    # Сохраняем выбранный размер
    context.user_data[f"order_size_{user_id}"] = size
    print(f"✅ Размер сохранён в user_data")
    
    # Переходим к форме заказа
    print("🔄 Вызываем show_order_form...")
    try:
        await show_order_form(update, context, product, user_id, size)
        print("✅ show_order_form выполнена успешно")
    except Exception as e:
        print(f"❌ Ошибка в show_order_form: {e}")


async def show_order_form(update: Update, context: ContextTypes.DEFAULT_TYPE, product, user_id, size=None):
    """Показывает форму для ввода данных или использует данные из профиля"""
    query = update.callback_query
    
    if size:
        context.user_data[f"order_size_{user_id}"] = size
    
    final_size = context.user_data.get(f"order_size_{user_id}")
    final_color = context.user_data.get(f"order_color_{user_id}")
    
    try:
        await query.message.delete()
    except:
        pass
    
    # Проверяем, заполнен ли профиль
    from handlers.profile import is_profile_complete
    profile_complete = await is_profile_complete(user_id, context)
    
    if profile_complete:
        # Если профиль заполнен — автоматически оформляем заказ
        await auto_order_from_profile(update, context, product, user_id, final_size, final_color)
    else:
        # Если профиль не заполнен — показываем форму
        context.user_data[f"ordering_{user_id}"] = True
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад к выбору размера", callback_data=f"back_to_size_{product.id}")]
        ])
        
        attributes_text = ""
        if final_color:
            attributes_text += f"🎨 Цвет: {final_color}\n"
        if final_size:
            attributes_text += f"📏 Размер: {final_size}\n"
        
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


async def auto_order_from_profile(update, context, product, user_id, size, color):
    """Автоматическое оформление заказа из данных профиля"""
    query = update.callback_query
    
    from handlers.profile import get_profile_data
    profile = await get_profile_data(user_id, context)
    
    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "size": size,
        "color": color,
        "last_name": profile.get('last_name'),
        "first_name": profile.get('first_name'),
        "phone": profile.get('phone'),
        "country": profile.get('country'),
        "region": profile.get('region'),
        "city": profile.get('city'),
        "postal_code": profile.get('postal_code'),
        "address": profile.get('address'),
        "email": profile.get('email'),
        "user_id": user_id,
        "username": update.effective_user.username
    }
    
    # Формируем текст для админа
    admin_text = f"🆕 *НОВЫЙ ЗАКАЗ!*\n\n"
    admin_text += f"👟 {order_info['product']}\n"
    if order_info.get('color'):
        admin_text += f"🎨 Цвет: {order_info['color']}\n"
    if order_info.get('size'):
        admin_text += f"📏 Размер: {order_info['size']}\n"
    admin_text += f"💰 Сумма: {order_info['price']} руб\n\n"
    admin_text += f"📋 Данные клиента (из профиля):\n"
    admin_text += f"• Фамилия: {order_info['last_name']}\n"
    admin_text += f"• Имя: {order_info['first_name']}\n"
    admin_text += f"• Телефон: {order_info['phone']}\n"
    admin_text += f"• Страна: {order_info['country']}\n"
    admin_text += f"• Регион: {order_info['region']}\n"
    admin_text += f"• Город: {order_info['city']}\n"
    admin_text += f"• Индекс: {order_info['postal_code']}\n"
    admin_text += f"• Адрес: {order_info['address']}\n"
    admin_text += f"• Email: {order_info['email']}\n\n"
    admin_text += f"👤 @{order_info['username']}"
    
    await context.bot.send_message(
        chat_id=1941249302,
        text=admin_text,
        parse_mode="Markdown"
    )
    
    await query.edit_message_text(
        text=f"✅ *ЗАКАЗ ПРИНЯТ!*\n\n"
        f"📦 Менеджер свяжется с вами\n"
        f"📬 Трек-номер придёт через 2-3 дня\n\n"
        f"🌟 Спасибо за покупку!",
        parse_mode="Markdown"
    )
    
    # Очищаем данные заказа
    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_product_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)


async def order_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введённых данных заказа"""
    user_id = update.effective_user.id
    if not context.user_data.get(f"ordering_{user_id}"):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(",")]

    if len(parts) < 5:
        await update.message.reply_text(
            "❌ *Недостаточно данных!*\n\nПожалуйста, введите все 5 пунктов через запятую:\n\nФИО, Индекс, Город, Адрес, Телефон",
            parse_mode="Markdown"
        )
        return

    product_id = context.user_data.get(f"order_product_{user_id}")
    product = products_manager.get_by_id(product_id)

    if not product:
        await update.message.reply_text("❌ Товар не найден!")
        return

    # Получаем выбранные атрибуты
    size = context.user_data.get(f"order_size_{user_id}")
    color = context.user_data.get(f"order_color_{user_id}")

    # Сохраняем заказ
    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "size": size,
        "color": color,
        "fio": parts[0],
        "index": parts[1],
        "city": parts[2],
        "address": parts[3],
        "phone": parts[4],
        "user_id": user_id,
        "username": update.effective_user.username
    }

    # Формируем текст для админа
    admin_text = f"🆕 *НОВЫЙ ЗАКАЗ!*\n\n"
    admin_text += f"👟 {order_info['product']}\n"
    if order_info.get('color'):
        admin_text += f"🎨 Цвет: {order_info['color']}\n"
    if order_info.get('size'):
        admin_text += f"📏 Размер: {order_info['size']}\n"
    admin_text += f"💰 Сумма: {order_info['price']} руб\n\n"
    admin_text += f"📋 Данные клиента:\n"
    admin_text += f"• ФИО: {order_info['fio']}\n"
    admin_text += f"• Телефон: {order_info['phone']}\n"
    admin_text += f"• Индекс: {order_info['index']}\n"
    admin_text += f"• Город: {order_info['city']}\n"
    admin_text += f"• Адрес: {order_info['address']}\n\n"
    admin_text += f"👤 @{order_info['username']}"

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ *ЗАКАЗ ПРИНЯТ!*\n\n"
        "📦 Менеджер свяжется с вами\n"
        "📬 Трек-номер придёт через 2-3 дня\n\n"
        "🌟 Спасибо за покупку!",
        parse_mode="Markdown"
    )

    # Очищаем данные заказа
    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_product_{user_id}", None)
    context.user_data.pop(f"order_size_{user_id}", None)

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
    # Цвет сохраняем, он нужен
    
    # Показываем выбор размера
    await show_order_size_selection(update, context, product, user_id)