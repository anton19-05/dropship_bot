from handlers.profile import profile, edit_profile, edit_name, edit_phone, edit_address, handle_profile_input
from handlers.favorites import add_to_favorites, view_favorites, fav_to_cart, fav_remove
from handlers.cart import (
    add_to_cart, cart_select_size, cart_confirm_quantity, view_cart,
    cart_increase, cart_decrease, cart_remove
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TOKEN

from handlers.order import order_start, order_handle
from handlers.start import start, main_back
from handlers.catalog import catalog, show_category, show_product_detail, change_color, change_page, back_to_catalog, show_reviews, review_next, review_prev, back_to_product, goto_product, back_to_category, back_to_product_from_reviews

app = Application.builder().token(TOKEN).build()

# Команды
app.add_handler(CommandHandler("start", start))

# Главное меню
app.add_handler(CallbackQueryHandler(main_back, pattern="^main_back$"))
app.add_handler(CallbackQueryHandler(profile, pattern="^menu_profile$"))
app.add_handler(CallbackQueryHandler(catalog, pattern="^menu_catalog$"))

# Каталог
app.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
app.add_handler(CallbackQueryHandler(change_page, pattern="^page_"))
app.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product_"))
app.add_handler(CallbackQueryHandler(change_color, pattern="^color_"))
app.add_handler(CallbackQueryHandler(
    back_to_catalog, pattern="^back_to_catalog$"))
app.add_handler(CallbackQueryHandler(
    back_to_product, pattern="^back_to_product_"))
app.add_handler(CallbackQueryHandler(goto_product, pattern="^goto_product_"))
app.add_handler(CallbackQueryHandler(
    back_to_category, pattern="^back_to_category_"))

# Отзывы
app.add_handler(CallbackQueryHandler(show_reviews, pattern="^reviews_"))
app.add_handler(CallbackQueryHandler(review_next, pattern="^review_next$"))
app.add_handler(CallbackQueryHandler(review_prev, pattern="^review_prev$"))
app.add_handler(CallbackQueryHandler(
    back_to_product_from_reviews, pattern="^back_to_product_from_reviews_"))
app.add_handler(CallbackQueryHandler(
    back_to_product, pattern="^back_to_product_"))

# Корзина
app.add_handler(CallbackQueryHandler(add_to_cart, pattern="^cart_add_"))
app.add_handler(CallbackQueryHandler(cart_select_size, pattern="^cart_size_"))
app.add_handler(CallbackQueryHandler(
    cart_confirm_quantity, pattern="^cart_qty_"))
app.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
app.add_handler(CallbackQueryHandler(cart_increase, pattern="^cart_incr_"))
app.add_handler(CallbackQueryHandler(cart_decrease, pattern="^cart_decr_"))
app.add_handler(CallbackQueryHandler(cart_remove, pattern="^cart_remove_"))

# Избранное
app.add_handler(CallbackQueryHandler(add_to_favorites, pattern="^fav_add_"))
app.add_handler(CallbackQueryHandler(
    view_favorites, pattern="^view_favorites$"))
app.add_handler(CallbackQueryHandler(fav_to_cart, pattern="^fav_to_cart_"))
app.add_handler(CallbackQueryHandler(fav_remove, pattern="^fav_remove_"))

# Заказать
app.add_handler(CallbackQueryHandler(order_start, pattern="^order_"))

# Профиль
app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
app.add_handler(CallbackQueryHandler(edit_profile, pattern="^edit_profile$"))
app.add_handler(CallbackQueryHandler(edit_name, pattern="^edit_name$"))
app.add_handler(CallbackQueryHandler(edit_phone, pattern="^edit_phone$"))
app.add_handler(CallbackQueryHandler(edit_address, pattern="^edit_address$"))

# Обработчики текста
app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_profile_input))

# Неактивные кнопки


async def noop(update, context):
    query = update.callback_query
    await query.answer("⛔ Эта кнопка неактивна", show_alert=True)
app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

print("✅ Бот запущен!")
app.run_polling()
