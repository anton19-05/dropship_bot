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
        
        # Форматируем отображение
        display = str(size_value) if available else f"❌ {size_value}"
        
        # Если нет в наличии — кнопка неактивна
        callback = f"order_size_{product.id}_{size_value}" if available else "noop"
        
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
    text += f"👇 *Выберите размер:*\n"
    text += f"❌ — размер отсутствует в наличии"
    
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
    parts = data.split("_")
    product_id = parts[0]
    size = parts[1]
    
    # Проверяем, есть ли размер в наличии
    product = products_manager.get_by_id(product_id)
    if not product.is_size_available(size):
        await query.answer("❌ Этот размер отсутствует в наличии!", show_alert=True)
        return
    
    # Сохраняем выбранный размер
    context.user_data[f"order_size_{user_id}"] = size
    
    # Переходим к форме заказа
    await show_order_form(update, context, product, user_id, size)


async def show_order_form(update: Update, context: ContextTypes.DEFAULT_TYPE, product, user_id, size=None):
    """Показывает форму для ввода данных с уже выбранными атрибутами"""
    query = update.callback_query
    
    # Сохраняем размер, если он есть
    if size:
        context.user_data[f"order_size_{user_id}"] = size
    
    # Получаем сохранённые атрибуты
    final_size = context.user_data.get(f"order_size_{user_id}")
    final_color = context.user_data.get(f"order_color_{user_id}")
    
    # Удаляем сообщение с выбором размера
    try:
        await query.message.delete()
    except:
        pass
    
    # Устанавливаем флаг, что пользователь в процессе заказа
    context.user_data[f"ordering_{user_id}"] = True
    
    # Данные из профиля
    user_data = context.user_data.get(f"user_data_{user_id}", {})
    
    # Формируем подсказку с выбранными атрибутами
    attributes_text = ""
    if final_color:
        attributes_text += f"🎨 Цвет: {final_color}\n"
    if final_size:
        attributes_text += f"📏 Размер: {final_size}\n"
    
    profile_hint = ""
    if user_data.get('name'):
        profile_hint += f"👤 ФИО: {user_data['name']}\n"
    if user_data.get('phone'):
        profile_hint += f"📞 Телефон: {user_data['phone']}\n"
    if user_data.get('address'):
        profile_hint += f"📍 Адрес: {user_data['address']}\n"

    hint = f"\n\n📋 *Ваши сохранённые данные:*\n{profile_hint}\n💡 Вы можете изменить их в профиле." if profile_hint else ""

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"📝 *ОФОРМЛЕНИЕ ЗАКАЗА*\n\n"
        f"👟 Товар: {product.name}\n"
        f"{attributes_text}"
        f"💰 Цена: {product.price} руб\n\n"
        f"Напишите одним сообщением через запятую:\n\n"
        f"1️⃣ ФИО\n"
        f"2️⃣ Индекс\n"
        f"3️⃣ Город\n"
        f"4️⃣ Адрес\n"
        f"5️⃣ Телефон\n\n"
        f"📌 *Пример:* Иван Иванов, 123456, Москва, ул. Ленина 5, +79991234567{hint}",
        parse_mode="Markdown"
    )


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
    # Цвет не очищаем, он может понадобиться для других товаров