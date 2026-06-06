import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TOKEN

# Импортируем всех ваших хендлеров (они остаются без изменений)
from handlers.profile import profile, edit_profile, edit_name, edit_phone, edit_address, handle_profile_input
from handlers.favorites import add_to_favorites, view_favorites, fav_to_cart, fav_remove
from handlers.cart import (
    add_to_cart, cart_select_size, cart_confirm_quantity, view_cart,
    cart_increase, cart_decrease, cart_remove
)
from handlers.order import order_start, order_handle
from handlers.start import start, main_back
from handlers.catalog import catalog, show_category, show_product_detail, change_color, change_page, back_to_catalog, show_reviews, review_next, review_prev, back_to_product, goto_product, back_to_category, back_to_product_from_reviews

# 1. СОЗДАЁМ FLASK-ПРИЛОЖЕНИЕ (ВЕБ-СЕРВЕР)
flask_app = Flask(__name__)

# 2. СОЗДАЁМ И НАСТРАИВАЕМ ВАШЕГО БОТА (ТАК ЖЕ, КАК РАНЬШЕ)
telegram_app = Application.builder().token(TOKEN).build()

# --- ВСЕ ВАШИ ХЕНДЛЕРЫ (КОПИРУЕМ ИЗ main.py) ---

# Команды
telegram_app.add_handler(CommandHandler("start", start))

# Главное меню
telegram_app.add_handler(CallbackQueryHandler(main_back, pattern="^main_back$"))
telegram_app.add_handler(CallbackQueryHandler(profile, pattern="^menu_profile$"))
telegram_app.add_handler(CallbackQueryHandler(catalog, pattern="^menu_catalog$"))

# Каталог
telegram_app.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
telegram_app.add_handler(CallbackQueryHandler(change_page, pattern="^page_"))
telegram_app.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product_"))
telegram_app.add_handler(CallbackQueryHandler(change_color, pattern="^color_"))
telegram_app.add_handler(CallbackQueryHandler(back_to_catalog, pattern="^back_to_catalog$"))
telegram_app.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product_"))
telegram_app.add_handler(CallbackQueryHandler(goto_product, pattern="^goto_product_"))
telegram_app.add_handler(CallbackQueryHandler(back_to_category, pattern="^back_to_category_"))

# Отзывы
telegram_app.add_handler(CallbackQueryHandler(show_reviews, pattern="^reviews_"))
telegram_app.add_handler(CallbackQueryHandler(review_next, pattern="^review_next$"))
telegram_app.add_handler(CallbackQueryHandler(review_prev, pattern="^review_prev$"))
telegram_app.add_handler(CallbackQueryHandler(back_to_product_from_reviews, pattern="^back_to_product_from_reviews_"))
telegram_app.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product_"))

# Корзина
telegram_app.add_handler(CallbackQueryHandler(add_to_cart, pattern="^cart_add_"))
telegram_app.add_handler(CallbackQueryHandler(cart_select_size, pattern="^cart_size_"))
telegram_app.add_handler(CallbackQueryHandler(cart_confirm_quantity, pattern="^cart_qty_"))
telegram_app.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
telegram_app.add_handler(CallbackQueryHandler(cart_increase, pattern="^cart_incr_"))
telegram_app.add_handler(CallbackQueryHandler(cart_decrease, pattern="^cart_decr_"))
telegram_app.add_handler(CallbackQueryHandler(cart_remove, pattern="^cart_remove_"))

# Избранное
telegram_app.add_handler(CallbackQueryHandler(add_to_favorites, pattern="^fav_add_"))
telegram_app.add_handler(CallbackQueryHandler(view_favorites, pattern="^view_favorites$"))
telegram_app.add_handler(CallbackQueryHandler(fav_to_cart, pattern="^fav_to_cart_"))
telegram_app.add_handler(CallbackQueryHandler(fav_remove, pattern="^fav_remove_"))

# Заказать
telegram_app.add_handler(CallbackQueryHandler(order_start, pattern="^order_"))

# Профиль
telegram_app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
telegram_app.add_handler(CallbackQueryHandler(edit_profile, pattern="^edit_profile$"))
telegram_app.add_handler(CallbackQueryHandler(edit_name, pattern="^edit_name$"))
telegram_app.add_handler(CallbackQueryHandler(edit_phone, pattern="^edit_phone$"))
telegram_app.add_handler(CallbackQueryHandler(edit_address, pattern="^edit_address$"))

# Обработчики текста
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_input))

# Неактивные кнопки
async def noop(update, context):
    query = update.callback_query
    await query.answer("⛔ Эта кнопка неактивна", show_alert=True)
telegram_app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

# 3. КОРНЕВОЙ МАРШРУТ ДЛЯ HEALTH CHECK RENDER
@flask_app.route('/')
def hello():
    return "✅ Бот работает!", 200

# 4. МАРШРУТ, КУДА TELEGRAM БУДЕТ ПРИСЫЛАТЬ ОБНОВЛЕНИЯ
@flask_app.route(f'/webhook/{TOKEN}', methods=['POST'])
async def webhook():
    json_data = request.get_json()
    if not json_data:
        return jsonify({'status': 'error', 'message': 'No JSON received'}), 400
    
    update = Update.de_json(json_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return jsonify({'status': 'ok'}), 200

# 5. ФУНКЦИЯ ДЛЯ ЗАПУСКА WEBHOOK-СЕРВЕРА
def start_webhook():
    port = int(os.environ.get('PORT', 10000))
    from waitress import serve
    serve(flask_app, host='0.0.0.0', port=port)

# 6. ЗАПУСК
if __name__ == '__main__':
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Правильная инициализация через loop
    loop.run_until_complete(telegram_app.initialize())   # <-- это правильно!
    
    # Устанавливаем вебхук
    render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if render_hostname:
        webhook_url = f'https://{render_hostname}/webhook/{TOKEN}'
    else:
        webhook_url = f'https://dropship-bot-706z.onrender.com/webhook/{TOKEN}'
    
    print(f'🔄 Устанавливаем вебхук: {webhook_url}')
    loop.run_until_complete(telegram_app.bot.set_webhook(webhook_url))
    print("✅ Вебхук успешно установлен!")
    
    print(f'🚀 Запускаем веб-сервер на порту {os.environ.get("PORT", 10000)}...')
    start_webhook()