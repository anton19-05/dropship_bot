import time
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOOMONEY_WALLET, BOT_USERNAME, ADMIN_ID
from debug import info, error


def generate_signature(shop_id, order_id, amount, secret):
    """Генерирует подпись для запроса к ЮMoney API"""
    message = f"{shop_id}{order_id}{amount}{secret}"
    return hashlib.sha256(message.encode()).hexdigest()


async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount, order_id, description):
    """Создает платеж через API ЮMoney"""
    
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        await query.answer()
    else:
        query = None
        chat_id = update.effective_chat.id
    
    user_id = update.effective_user.id
    
    # Формируем ссылку для оплаты
    payment_url = (
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
    
    # Сохраняем информацию о платеже
    context.user_data[f"payment_{order_id}"] = {
        "order_id": order_id,
        "amount": amount,
        "description": description,
        "user_id": user_id,
        "status": "pending",
        "created_at": time.time()
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_payment_{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="view_cart")]
    ])
    
    text = (
        f"💳 *ОПЛАТА ЗАКАЗА #{order_id}*\n\n"
        f"📦 *Товар:* {description}\n"
        f"💰 *Сумма:* {amount} руб\n\n"
        f"🔒 *Безопасная оплата через ЮMoney*\n"
        f"💳 Принимаются все банковские карты\n"
        f"📱 Поддерживается СБП\n\n"
        f"⏱️ *После оплаты нажмите:* «✅ Я оплатил»"
    )
    
    try:
        if query and query.message:
            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        
        info("PAYMENT", f"Создан платеж для заказа {order_id}", {"user_id": user_id, "amount": amount})
        
    except Exception as e:
        error("PAYMENT", f"Ошибка создания платежа: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ *Произошла ошибка при создании платежа.*\nПожалуйста, попробуйте позже.",
            parse_mode="Markdown"
        )


async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Я оплатил'"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace("check_payment_", "")
    user_id = query.from_user.id
    
    payment_info = context.user_data.get(f"payment_{order_id}")
    
    if not payment_info:
        await query.edit_message_text(
            "❌ *Платёж не найден.*\nПожалуйста, создайте новый заказ.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
            ])
        )
        return
    
    # Отправляем уведомление админу
    admin_text = (
        f"🔄 *Платёж требует подтверждения!*\n\n"
        f"📦 Заказ: #{order_id}\n"
        f"👤 Пользователь: @{update.effective_user.username}\n"
        f"💰 Сумма: {payment_info['amount']} руб\n"
        f"📝 Товар: {payment_info['description']}\n\n"
        f"✅ Для подтверждения отправьте команду:\n"
        f"/confirm {order_id}"
    )
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode="Markdown"
    )
    
    await query.edit_message_text(
        "✅ *Запрос на подтверждение отправлен менеджеру!*\n\n"
        "Менеджер проверит оплату и подтвердит заказ.\n"
        "Обычно это занимает 5-10 минут.\n\n"
        "📬 Трек-номер придёт после подтверждения.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
        ])
    )


async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение платежа админом (/confirm order_id)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ *Использование:*\n"
            "/confirm order_id\n\n"
            "Пример: /confirm 1941249302_1234567890",
            parse_mode="Markdown"
        )
        return
    
    order_id = args[0]
    
    # Ищем платеж
    payment_info = None
    for key in context.user_data:
        if key.startswith("payment_") and context.user_data[key].get("order_id") == order_id:
            payment_info = context.user_data[key]
            break
    
    if not payment_info:
        await update.message.reply_text("❌ Платёж с таким ID не найден.")
        return
    
    payment_info["status"] = "confirmed"
    
    # Отправляем уведомление пользователю
    user_id = payment_info["user_id"]
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ *Ваш заказ #{order_id} подтверждён!*\n\n"
            f"📦 Оплата прошла успешно.\n"
            f"📬 Трек-номер будет отправлен через 2-3 дня.\n\n"
            f"🌟 Спасибо за покупку!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Не удалось уведомить пользователя: {e}")
    
    await update.message.reply_text(f"✅ Платёж {order_id} успешно подтверждён. Пользователь уведомлён.")


async def payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты (возврат из ЮMoney)"""
    query = update.callback_query
    
    order_id = "неизвестный"
    if query and query.data and query.data.startswith("payment_success_"):
        order_id = query.data.replace("payment_success_", "")
    
    text = (
        "✅ *ОПЛАТА ПРОШЛА УСПЕШНО!*\n\n"
        f"📦 Заказ #{order_id} принят в обработку.\n\n"
        "📬 Трек-номер придёт через 2-3 дня.\n"
        "📞 Менеджер свяжется с вами.\n\n"
        "🌟 *Спасибо за покупку!*"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
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