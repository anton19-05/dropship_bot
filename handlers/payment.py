import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import YOOMONEY_WALLET, BOT_USERNAME, ADMIN_ID
from debug import info, error


async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount, order_id, description, order_info=None):
    """Создает платежную ссылку ЮMoney"""
    try:
        if update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat_id
            await query.answer()
        else:
            query = None
            chat_id = update.effective_chat.id
        
        user_id = update.effective_user.id
        
        if not YOOMONEY_WALLET:
            error("PAYMENT", "Кошелек ЮMoney не настроен!")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ *Ошибка: платежная система не настроена.*",
                parse_mode="Markdown"
            )
            return
        
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
        
        context.user_data[f"payment_{order_id}"] = {
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "user_id": user_id,
            "status": "pending",
            "created_at": time.time(),
            "order_info": order_info
        }
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить картой", url=payment_url)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_payment_{order_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="view_cart")]
        ])
        
        text = (
            f"💳 *ОПЛАТА ЗАКАЗА #{order_id}*\n\n"
            f"📦 *Товар:* {description}\n"
            f"💰 *Сумма:* {amount} руб\n\n"
            f"💳 *Способы оплаты:*\n"
            f"• Банковская карта (МИР, Mastercard, Visa)\n"
            f"• SberPay (СберБанк)\n\n"
            f"🔒 *Безопасная оплата через ЮMoney*\n\n"
            f"⏱️ *После оплаты нажмите:* «✅ Я оплатил»"
        )
        
        try:
            if query and query.message and query.message.text:
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
        except Exception as edit_error:
            error("PAYMENT", f"Не удалось отредактировать: {edit_error}")
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
        try:
            chat_id = update.effective_chat.id if hasattr(update, 'effective_chat') else update.callback_query.message.chat_id
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Ошибка:* {str(e)[:100]}",
                parse_mode="Markdown"
            )
        except:
            pass


async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Я оплатил'"""
    try:
        query = update.callback_query
        await query.answer()
        
        order_id = query.data.replace("check_payment_", "")
        user_id = query.from_user.id
        
        print(f"🔍 check_payment_status: order_id={order_id}")
        
        payment_info = context.user_data.get(f"payment_{order_id}")
        print(f"🔍 payment_info = {payment_info}")
        
        if not payment_info:
            await query.edit_message_text(
                text="❌ Платёж не найден.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
                ])
            )
            return
        
        # ✅ ПРИНУДИТЕЛЬНАЯ ОТПРАВКА АДМИНУ
        # Создаём заказ из данных, если order_info нет
        order_info = payment_info.get("order_info")
        
        if not order_info:
            # Если order_info нет, создаём из того, что есть
            print(f"⚠️ order_info отсутствует, создаём из payment_info")
            order_info = {
                "product": payment_info.get("description", "Товар"),
                "price": payment_info.get("amount", 0),
                "color": "не указан",
                "size": "не указан",
                "last_name": "не указана",
                "first_name": "не указано",
                "phone": "не указан",
                "country": "не указана",
                "region": "не указан",
                "city": "не указан",
                "postal_code": "не указан",
                "address": "не указан",
                "email": "не указан",
                "username": "не указан"
            }
        
                # ✅ ОТПРАВЛЯЕМ АДМИНУ (БЕЗ Markdown)
        admin_text = (
            f"🆕 НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!\n\n"
            f"📦 Заказ: #{order_id}\n"
            f"👟 {order_info.get('product', 'не указан')}\n"
            f"🎨 Цвет: {order_info.get('color', 'не указан')}\n"
            f"📏 Размер: {order_info.get('size', 'не указан')}\n"
            f"💰 Сумма: {order_info.get('price', 0)} руб\n\n"
            f"📋 Данные клиента:\n"
            f"• Фамилия: {order_info.get('last_name', 'не указана')}\n"
            f"• Имя: {order_info.get('first_name', 'не указано')}\n"
            f"• Телефон: {order_info.get('phone', 'не указан')}\n"
            f"• Страна: {order_info.get('country', 'не указана')}\n"
            f"• Регион: {order_info.get('region', 'не указан')}\n"
            f"• Город: {order_info.get('city', 'не указан')}\n"
            f"• Индекс: {order_info.get('postal_code', 'не указан')}\n"
            f"• Адрес: {order_info.get('address', 'не указан')}\n"
            f"• Email: {order_info.get('email', 'не указан')}\n\n"
            f"👤 @{order_info.get('username', 'не указан')}"
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text
            # parse_mode НЕ УКАЗЫВАЕМ!
        )
        print(f"✅ Уведомление админу ОТПРАВЛЕНО для заказа {order_id}")
        
        # Ответ пользователю
        await query.edit_message_text(
            text=(
                "✅ ЗАКАЗ ПРИНЯТ!\n\n"
                f"📦 Заказ #{order_id} принят в обработку.\n\n"
                "📬 Трек-номер придёт через 2-3 дня.\n"
                "📞 Менеджер свяжется с вами.\n\n"
                "🌟 Спасибо за покупку!"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
            ])
        )
        
    except Exception as e:
        print(f"❌ Ошибка в check_payment_status: {e}")
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"❌ Ошибка: {str(e)[:100]}"
        )


async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение платежа админом (/confirm order_id)"""
    try:
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
        
        payment_info = None
        for key in context.user_data:
            if key.startswith("payment_") and context.user_data[key].get("order_id") == order_id:
                payment_info = context.user_data[key]
                break
        
        if not payment_info:
            await update.message.reply_text("❌ Платёж с таким ID не найден.")
            return
        
        payment_info["status"] = "confirmed"
        
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
        
    except Exception as e:
        error("PAYMENT", f"Ошибка в confirm_payment: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты (возврат из ЮMoney)"""
    try:
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
            try:
                await query.edit_message_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            except:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
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
    except Exception as e:
        error("PAYMENT", f"Ошибка в payment_success: {e}")