from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from handlers.db_sqlite import get_all_carts
import json


async def check_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для админа: показывает содержимое базы данных"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    carts = get_all_carts()
    
    if not carts:
        await update.message.reply_text("📦 *База данных корзин пуста*", parse_mode="Markdown")
        return
    
    message = "📦 *Содержимое базы данных (корзины):*\n\n"
    for cart in carts:
        message += f"👤 *User ID:* {cart['user_id']}\n"
        message += f"📅 *Обновлено:* {cart['updated_at']}\n"
        message += f"📋 *Данные:*\n```json\n{json.dumps(cart['cart_data'], ensure_ascii=False, indent=2)}\n```\n"
        message += "─" * 20 + "\n"
        
        if len(message) > 4000:
            await update.message.reply_text(message, parse_mode="Markdown")
            message = ""
    
    if message:
        await update.message.reply_text(message, parse_mode="Markdown")

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
    
    # ✅ ИЩЕМ ПЛАТЕЖ В user_data (не в bot_data!)
    payment_info = None
    for key in context.user_data:
        if key.startswith("payment_") and context.user_data[key].get("order_id") == order_id:
            payment_info = context.user_data[key]
            break
    
    if not payment_info:
        await update.message.reply_text("❌ Платёж с таким ID не найден.")
        return
    
    # Отправляем уведомление пользователю
    user_id = payment_info.get("user_id")
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Ваш заказ #{order_id} подтверждён!*\n\n"
                f"📦 Оплата прошла успешно.\n"
                f"📬 Трек-номер будет отправлен через 2-3 дня.\n\n"
                f"🌟 Спасибо за покупку!",
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ Платёж {order_id} подтверждён. Пользователь уведомлён.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Не удалось уведомить пользователя: {e}")
    else:
        await update.message.reply_text("❌ Не найден ID пользователя для уведомления.")