from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from handlers.db_sqlite import get_all_carts
import json


async def check_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для админа: показывает содержимое базы данных"""
    user_id = update.effective_user.id
    
    # Только админ может использовать эту команду
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
        
        # Разбиваем длинные сообщения
        if len(message) > 4000:
            await update.message.reply_text(message, parse_mode="Markdown")
            message = ""
    
    if message:
        await update.message.reply_text(message, parse_mode="Markdown")

async def test_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки платежа"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return
    
    from handlers.payment import create_payment
    import time
    
    order_id = f"test_{int(time.time())}"
    
    await create_payment(
        update=update,
        context=context,
        amount=100,
        order_id=order_id,
        description="Тестовый товар"
    )