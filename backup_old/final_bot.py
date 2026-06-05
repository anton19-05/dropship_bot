# final_bot.py - Запуск бота

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers import *

TOKEN = "8883773859:AAGLg8D-AEGmKldn_6jNUYdV37DV0WZWJw4"

app = Application.builder().token(TOKEN).build()

# Команды
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("confirm", confirm_order))
app.add_handler(CommandHandler("clear", clear))

# Обработчики каталога
app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
app.add_handler(CallbackQueryHandler(show_subcategories, pattern="^cat_"))
app.add_handler(CallbackQueryHandler(
    show_products_by_subcategory, pattern="^sub_"))
app.add_handler(CallbackQueryHandler(
    product_detail, pattern="^product_detail_"))
app.add_handler(CallbackQueryHandler(products_page, pattern="^products_page_"))
app.add_handler(CallbackQueryHandler(noop_handler, pattern="^noop$"))
app.add_handler(CallbackQueryHandler(
    back_to_subcategory_menu, pattern="^back_to_subcategory_menu$"))

# Пустые категории
app.add_handler(CallbackQueryHandler(clothing, pattern="^clothing$"))
app.add_handler(CallbackQueryHandler(accessories, pattern="^accessories$"))
app.add_handler(CallbackQueryHandler(home, pattern="^home$"))
app.add_handler(CallbackQueryHandler(electronics, pattern="^electronics$"))

# Обработчики цвета
app.add_handler(CallbackQueryHandler(
    product_change_color, pattern="^product_change_color_"))

# Обработчики корзины
app.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
app.add_handler(CallbackQueryHandler(
    add_to_cart_with_options, pattern="^add_cart_"))
app.add_handler(CallbackQueryHandler(
    add_to_favorites_with_options, pattern="^add_fav_"))
app.add_handler(CallbackQueryHandler(select_quantity, pattern="^size_"))
app.add_handler(CallbackQueryHandler(confirm_add_to_cart, pattern="^qty_"))
app.add_handler(CallbackQueryHandler(
    confirm_add_to_favorites, pattern="^fav_size_"))
app.add_handler(CallbackQueryHandler(
    back_to_product, pattern="^back_to_product$"))
app.add_handler(CallbackQueryHandler(back_to_size, pattern="^back_to_size$"))
app.add_handler(CallbackQueryHandler(add_more_to_cart, pattern="^add_more_"))
app.add_handler(CallbackQueryHandler(
    remove_item_from_cart, pattern="^remove_item_"))
app.add_handler(CallbackQueryHandler(
    increase_size_quantity, pattern="^incr_size_"))
app.add_handler(CallbackQueryHandler(
    decrease_size_quantity, pattern="^decr_size_"))
app.add_handler(CallbackQueryHandler(add_size_to_cart, pattern="^add_size_"))
app.add_handler(CallbackQueryHandler(
    confirm_add_size, pattern="^confirm_add_size_"))
app.add_handler(CallbackQueryHandler(
    goto_product_from_cart, pattern="^goto_product_"))

# Обработчики избранного
app.add_handler(CallbackQueryHandler(
    view_favorites, pattern="^view_favorites$"))
app.add_handler(CallbackQueryHandler(
    remove_from_favorites_handler, pattern="^remove_fav_"))
app.add_handler(CallbackQueryHandler(fav_to_cart, pattern="^fav_to_cart_"))
app.add_handler(CallbackQueryHandler(fav_reviews, pattern="^fav_reviews_"))
app.add_handler(CallbackQueryHandler(fav_order, pattern="^fav_order_"))

# Обработчики профиля
app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
app.add_handler(CallbackQueryHandler(edit_profile, pattern="^edit_profile$"))
app.add_handler(CallbackQueryHandler(edit_index, pattern="^edit_index$"))
app.add_handler(CallbackQueryHandler(edit_city, pattern="^edit_city$"))
app.add_handler(CallbackQueryHandler(
    back_to_profile, pattern="^back_to_profile$"))

# Обработчики заказа
app.add_handler(CallbackQueryHandler(order_start, pattern="^order_start$"))
app.add_handler(CallbackQueryHandler(
    cancel_order, pattern="^back_to_product_from_order_"))
app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment_"))

# Обработчики отзывов
app.add_handler(CallbackQueryHandler(
    product_reviews_handler, pattern="^product_reviews_"))
app.add_handler(CallbackQueryHandler(reviews_next, pattern="^reviews_next$"))
app.add_handler(CallbackQueryHandler(reviews_prev, pattern="^reviews_prev$"))
app.add_handler(CallbackQueryHandler(
    back_to_product_from_reviews, pattern="^back_to_product_from_reviews_"))

# Обработчики переходов
app.add_handler(CallbackQueryHandler(goto_cart, pattern="^goto_cart$"))
app.add_handler(CallbackQueryHandler(
    goto_favorites, pattern="^goto_favorites$"))
app.add_handler(CallbackQueryHandler(back_to_product_from_cart,
                pattern="^back_to_product_from_cart_"))

# Обработчики навигации
app.add_handler(CallbackQueryHandler(howto, pattern="^howto$"))
app.add_handler(CallbackQueryHandler(contacts, pattern="^contacts$"))
app.add_handler(CallbackQueryHandler(main_back, pattern="^main_back$"))

# Обработчики поиска
app.add_handler(CallbackQueryHandler(search, pattern="^search$"))
app.add_handler(CallbackQueryHandler(handle_code_button, pattern="^code_"))
app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, direct_code_search))

# Обработчики текста
app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_size_input))
app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_profile_edit))

print("✅ Бот запущен! Все функции работают!")
app.run_polling()
