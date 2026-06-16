import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOOMONEY_WALLET, BOT_USERNAME
from debug import info


async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount, order_id, description):
    """Создает платежную ссылку ЮMoney с красивым оформлением"""
    
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        await query.answer()
    else:
        query = None
        chat_id = update.effective_chat.id
    
    user_id = update.effective_user.id
    
    # Базовый URL для оплаты
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
    
    # Красивые кнопки с банками
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 СберБанк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("💳 Т-Банк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("💳 Альфа-Банк", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("💳 ВТБ", url=base_url + "&paymentType=AC")],
        [InlineKeyboardButton("📱 СБП (быстрая оплата)", url=base_url + "&paymentType=SB")],
        [InlineKeyboardButton("🔙 Назад", callback_data="view_cart")]
    ])
    
    text = (
        f"💳 *ОПЛАТА ЗАКАЗА #{order_id}*\n\n"
        f"📦 *Товар:* {description}\n"
        f"💰 *Сумма:* {amount} руб\n\n"
        f"🔒 *Безопасная оплата через ЮMoney*\n"
        f"✅ Принимаются все банковские карты\n"
        f"📱 Поддерживается СБП\n\n"
        f"💡 *Не хотите регистрироваться?*\n"
        f"Нажмите на банк и выберите *«Оплатить как гость»*\n\n"
        f"👇 *Выберите способ оплаты:*"
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
    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")
        # fallback
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    info("PAYMENT", f"Создан платеж для заказа {order_id}", {"user_id": user_id, "amount": amount})


async def payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает сообщение об успешной оплате"""
    query = update.callback_query
    
    order_id = "неизвестный"
    if query and query.data and query.data.startswith("payment_success_"):
        order_id = query.data.replace("payment_success_", "")
    
    text = (
        "✅ *ОПЛАТА ПРОШЛА УСПЕШНО!*\n\n"
        f"📦 Заказ #{order_id} принят в обработку.\n\n"
        "📬 Трек-номер придёт через 2-3 дня.\n"
        "📞 Менеджер свяжется с вами для уточнения деталей.\n\n"
        "🌟 *Спасибо за покупку в MEGA SHOP!*"
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