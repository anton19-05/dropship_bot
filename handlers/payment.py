import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOOMONEY_WALLET, BOT_USERNAME, ADMIN_ID
from debug import info


async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount, order_id, description):
    """Создает платежную ссылку ЮMoney с кнопками банков"""
    
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        await query.answer()
    else:
        query = None
        chat_id = update.effective_chat.id
    
    user_id = update.effective_user.id
    
    base_url = (
        f"https://yoomoney.ru/quickpay/confirm?"
        f"receiver={YOOMONEY_WALLET}"
        f"&quickpay-form=shop"
        f"&targets={description}"
        f"&sum={amount}"
        f"&label=order_{order_id}_{user_id}"
        f"&successURL=https://t.me/{BOT_USERNAME}"
        f"&need-fio=false"
        f"&need-email=false"
        f"&need-phone=false"
        f"&need-address=false"
    )
    
    # Сохраняем ID заказа в user_data для проверки оплаты
    context.user_data[f"payment_order_{user_id}"] = order_id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 СберБанк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("🏦 Т-Банк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("🏦 Альфа-Банк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("🏦 ВТБ", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("📱 СБП (Система быстрых платежей)", url=base_url + "&paymentType=SB")],
        [InlineKeyboardButton("🔙 Назад", callback_data="view_cart")]
    ])
    
    text = (
        f"💸 *Оплата заказа #{order_id}*\n\n"
        f"📦 {description}\n"
        f"💰 Сумма: {amount} руб\n\n"
        f"👇 Выберите банк для оплаты:"
    )
    
    try:
        if query and query.message:
            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    info("PAYMENT", f"Создан платеж для заказа {order_id}", {"user_id": user_id, "amount": amount})


async def payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты — отправляем заказ админу"""
    query = update.callback_query
    
    order_id = "неизвестный"
    user_id = None
    
    if query and query.data and query.data.startswith("payment_success_"):
        order_id = query.data.replace("payment_success_", "")
        # Извлекаем user_id из order_id (формат: user_id_timestamp)
        parts = order_id.split("_")
        if len(parts) >= 1:
            try:
                user_id = int(parts[0])
            except:
                pass
    
    # Если не нашли user_id, пробуем из данных платежа
    if not user_id and query:
        user_id = query.from_user.id
    
    # Проверяем, есть ли сохранённый заказ
    order_info = None
    if user_id:
        order_info = context.user_data.get(f"pending_order_{user_id}")
    
    # Если заказ найден — отправляем админу
    if order_info:
        admin_text = f"🆕 *НОВЫЙ ЗАКАЗ!*\n\n"
        admin_text += f"👟 {order_info.get('product', 'Неизвестно')}\n"
        if order_info.get('color'):
            admin_text += f"🎨 Цвет: {order_info['color']}\n"
        if order_info.get('size'):
            admin_text += f"📏 Размер: {order_info['size']}\n"
        admin_text += f"💰 Сумма: {order_info.get('price', 0)} руб\n\n"
        admin_text += f"📋 Данные клиента (из профиля):\n"
        admin_text += f"• Фамилия: {order_info.get('last_name', 'Не указано')}\n"
        admin_text += f"• Имя: {order_info.get('first_name', 'Не указано')}\n"
        admin_text += f"• Телефон: {order_info.get('phone', 'Не указан')}\n"
        admin_text += f"• Страна: {order_info.get('country', 'Не указана')}\n"
        admin_text += f"• Регион: {order_info.get('region', 'Не указан')}\n"
        admin_text += f"• Город: {order_info.get('city', 'Не указан')}\n"
        admin_text += f"• Индекс: {order_info.get('postal_code', 'Не указан')}\n"
        admin_text += f"• Адрес: {order_info.get('address', 'Не указан')}\n"
        admin_text += f"• Email: {order_info.get('email', 'Не указан')}\n\n"
        admin_text += f"👤 @{order_info.get('username', 'неизвестен')}"
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="Markdown"
        )
        
        # Удаляем временный заказ
        context.user_data.pop(f"pending_order_{user_id}", None)
        
        # Показываем клиенту успех
        text = (
            "✅ *Оплата прошла успешно!*\n\n"
            f"📦 Заказ #{order_id} принят в обработку.\n\n"
            "📬 Трек-номер придёт через 2-3 дня.\n"
            "📞 Менеджер свяжется с вами для уточнения деталей.\n\n"
            "🌟 *Спасибо за покупку!*"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")],
            [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")]
        ])
        
        if query:
            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    else:
        # Если заказ не найден — просто показываем успех
        text = "✅ *Оплата прошла успешно!*\n\nСпасибо за покупку!"
        if query:
            await query.edit_message_text(text=text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text=text, parse_mode="Markdown")