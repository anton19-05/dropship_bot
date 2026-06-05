from telegram import Update
from telegram.ext import ContextTypes
from models import products_manager
from config import ADMIN_ID
from debug import info, debug, error, success, warning


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    context.user_data[f"order_product_{user_id}"] = product_id
    context.user_data[f"ordering_{user_id}"] = True

    try:
        await query.message.delete()
        debug("ORDER", "Сообщение с карточкой товара удалено")
    except Exception as e:
        warning("ORDER", f"Не удалось удалить сообщение: {e}")

    user_data = context.user_data.get(f"user_data_{user_id}", {})
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
        f"💰 Цена: {product.price} руб\n\n"
        f"Напишите одним сообщением через запятую:\n\n"
        f"1️⃣ ФИО\n"
        f"2️⃣ Размер\n"
        f"3️⃣ Индекс\n"
        f"4️⃣ Город\n"
        f"5️⃣ Адрес\n"
        f"6️⃣ Телефон\n\n"
        f"📌 *Пример:* Иван Иванов, 42, 123456, Москва, ул. Ленина 5, +79991234567{hint}",
        parse_mode="Markdown"
    )
    success("ORDER", f"Форма заказа отправлена для товара {product.name}")


async def order_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введённых данных заказа"""
    user_id = update.effective_user.id
    if not context.user_data.get(f"ordering_{user_id}"):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(",")]

    if len(parts) < 6:
        await update.message.reply_text(
            "❌ *Недостаточно данных!*\n\nПожалуйста, введите все 6 пунктов через запятую.",
            parse_mode="Markdown"
        )
        return

    product_id = context.user_data.get(f"order_product_{user_id}")
    product = products_manager.get_by_id(product_id)

    if not product:
        await update.message.reply_text("❌ Товар не найден!")
        return

    # Сохраняем заказ
    order_info = {
        "product": product.name,
        "product_code": product.code,
        "price": product.price,
        "fio": parts[0],
        "size": parts[1],
        "index": parts[2],
        "city": parts[3],
        "address": parts[4],
        "phone": parts[5],
        "user_id": user_id,
        "username": update.effective_user.username
    }

    # Отправляем админу
    from config import ADMIN_ID
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 *НОВЫЙ ЗАКАЗ!*\n\n"
        f"👟 {order_info['product']}\n"
        f"📏 Размер: {order_info['size']}\n"
        f"💰 Сумма: {order_info['price']} руб\n\n"
        f"📋 Данные клиента:\n"
        f"• ФИО: {order_info['fio']}\n"
        f"• Телефон: {order_info['phone']}\n"
        f"• Индекс: {order_info['index']}\n"
        f"• Город: {order_info['city']}\n"
        f"• Адрес: {order_info['address']}\n\n"
        f"👤 @{order_info['username']}",
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ *ЗАКАЗ ПРИНЯТ!*\n\n"
        "📦 Менеджер свяжется с вами\n"
        "📬 Трек-номер придёт через 2-3 дня\n\n"
        "🌟 Спасибо за покупку!",
        parse_mode="Markdown"
    )

    context.user_data.pop(f"ordering_{user_id}", None)
    context.user_data.pop(f"order_product_{user_id}", None)
