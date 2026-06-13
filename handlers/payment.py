import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOOMONEY_WALLET, BOT_USERNAME
from debug import info


async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount, order_id, description):
    """Создает платежную ссылку ЮMoney"""
    query = update.callback_query
    user_id = query.from_user.id
    
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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить картой", url=payment_url)],
        [InlineKeyboardButton("📱 Оплатить через СБП", url=payment_url + "&paymentType=SB")],
        [InlineKeyboardButton("🔙 Назад в корзину", callback_data="view_cart")]
    ])
    
    await query.edit_message_text(
        text=f"💸 *Оплата заказа #{order_id}*\n\n"
        f"📦 {description}\n"
        f"💰 Сумма: {amount} руб\n\n"
        f"Выберите способ оплаты:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    info("PAYMENT", f"Создан платеж для заказа {order_id}", {"user_id": user_id, "amount": amount})


async def payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает сообщение об успешной оплате (после возврата из ЮMoney)"""
    # Проверяем, есть ли параметр в callback_data
    query = update.callback_query
    
    # Получаем номер заказа из данных (если есть)
    order_id = "неизвестный"
    if query and query.data.startswith("payment_success_"):
        order_id = query.data.replace("payment_success_", "")
    
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