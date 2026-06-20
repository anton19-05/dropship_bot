import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes  # ← добавить ContextTypes
)
from config import TOKEN

# Импорты всех ваших хендлеров
from handlers.profile import profile, edit_profile_start, handle_profile_input, editing_state
from handlers.favorites import add_to_favorites, view_favorites, fav_to_cart, fav_remove
from handlers.cart import (
    add_to_cart, cart_select_size, cart_confirm_quantity, view_cart,
    cart_increase, cart_decrease, cart_remove, view_cart_from_profile, view_cart_from_product, cart_remove_group
)
from handlers.order import order_start, order_handle, order_select_size, back_to_size, show_order_form
from handlers.start import start, main_back
from handlers.catalog import (
    catalog, show_category, show_product_detail, change_color, change_page,
    back_to_catalog, show_reviews, review_next, review_prev, back_to_product,
    goto_product, back_to_category, back_to_product_from_reviews, 
    show_category_by_id, show_subcategory_products, back_to_catalog_from_products, select_attribute
)
from handlers.payment import payment_success, check_payment_status, confirm_payment
from storage import load_user_data
from handlers.admin import check_db


# ✅ ОБЪЕДИНЁННЫЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все текстовые сообщения"""
    user_id = update.effective_user.id
    print(f"🔍 handle_all_text ВЫЗВАНА! user_id={user_id}")
    
    # Проверяем, в процессе ли редактирования профиля
    if user_id in editing_state:
        print(f"✅ Режим редактирования профиля, вызываем handle_profile_input")
        await handle_profile_input(update, context)
        return
    
    # Проверяем, в процессе ли оформления заказа
    if context.user_data.get(f"ordering_{user_id}"):
        print(f"✅ Режим оформления заказа, вызываем order_handle")
        await order_handle(update, context)
        return
    
    # Если ничего не активно — игнорируем
    print(f"❌ Ничего не активно, игнорируем")
    await update.message.reply_text("❌ Неизвестная команда. Используйте кнопки меню.")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # --- Регистрация всех хендлеров ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("checkdb", check_db))
    application.add_handler(CommandHandler("confirm", confirm_payment))
    application.add_handler(CallbackQueryHandler(main_back, pattern="^main_back$"))
    application.add_handler(CallbackQueryHandler(profile, pattern="^menu_profile$"))
    application.add_handler(CallbackQueryHandler(catalog, pattern="^menu_catalog$"))
    application.add_handler(CallbackQueryHandler(order_select_size, pattern="^order_size_"))
    application.add_handler(CallbackQueryHandler(order_start, pattern="^order_"))
    application.add_handler(CallbackQueryHandler(view_cart_from_product, pattern="^view_cart_from_product$"))
    application.add_handler(CallbackQueryHandler(view_cart_from_profile, pattern="^view_cart_from_profile$"))
    application.add_handler(CallbackQueryHandler(back_to_size, pattern="^back_to_size_"))
    application.add_handler(CallbackQueryHandler(check_payment_status, pattern="^check_payment_"))
    
    # Каталог
    application.add_handler(CallbackQueryHandler(change_page, pattern="^page_"))
    application.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(change_color, pattern="^color_"))
    application.add_handler(CallbackQueryHandler(back_to_catalog, pattern="^back_to_catalog$"))
    application.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product_"))
    application.add_handler(CallbackQueryHandler(goto_product, pattern="^goto_product_"))
    application.add_handler(CallbackQueryHandler(back_to_category, pattern="^back_to_category_"))
    application.add_handler(CallbackQueryHandler(back_to_catalog_from_products, pattern="^back_to_catalog_from_products$"))
    application.add_handler(CallbackQueryHandler(select_attribute, pattern="^attr_"))
    
    # Категории и подкатегории
    application.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
    application.add_handler(CallbackQueryHandler(show_category_by_id, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(show_subcategory_products, pattern="^subcat_"))
    
    # Отзывы
    application.add_handler(CallbackQueryHandler(show_reviews, pattern="^reviews_"))
    application.add_handler(CallbackQueryHandler(review_next, pattern="^review_next$"))
    application.add_handler(CallbackQueryHandler(review_prev, pattern="^review_prev$"))
    application.add_handler(CallbackQueryHandler(back_to_product_from_reviews, pattern="^back_to_product_from_reviews_"))
    
    # Корзина
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^cart_add_"))
    application.add_handler(CallbackQueryHandler(cart_select_size, pattern="^cart_size_"))
    application.add_handler(CallbackQueryHandler(cart_confirm_quantity, pattern="^cart_qty_"))
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(cart_increase, pattern="^cart_incr_"))
    application.add_handler(CallbackQueryHandler(cart_decrease, pattern="^cart_decr_"))
    application.add_handler(CallbackQueryHandler(cart_remove, pattern="^cart_remove_"))
    application.add_handler(CallbackQueryHandler(cart_remove_group, pattern="^cart_remove_group_"))
    
    # Избранное
    application.add_handler(CallbackQueryHandler(add_to_favorites, pattern="^fav_add_"))
    application.add_handler(CallbackQueryHandler(view_favorites, pattern="^view_favorites$"))
    application.add_handler(CallbackQueryHandler(fav_to_cart, pattern="^fav_to_cart_"))
    application.add_handler(CallbackQueryHandler(fav_remove, pattern="^fav_remove_"))
    
    # Профиль
    application.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile_start$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile_change$"))
    application.add_handler(CallbackQueryHandler(payment_success, pattern="^payment_success$"))
    
    # ✅ ТОЛЬКО ОДИН ОБРАБОТЧИК ТЕКСТА
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))

    # Неактивные кнопки
    async def noop(update: Update, context):
        query = update.callback_query
        await query.answer("⛔ Эта кнопка неактивна", show_alert=True)
    application.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    # ✅ ВОССТАНАВЛИВАЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ ИЗ JSON
    all_data = load_user_data()
    for user_id_str, user_data in all_data.items():
        user_id = int(user_id_str)
        application.user_data[user_id] = user_data
    print(f"✅ Восстановлено {len(all_data)} профилей пользователей")

        # --- Запуск через вебхуки ---
    port = int(os.environ.get('PORT', 10000))
    
    # Проверяем, запущено ли на Render
    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_hostname:
        # На Render — используем вебхук
        webhook_url = f'https://{render_hostname}/webhook/{TOKEN}'
        print(f'🔄 Устанавливаем вебхук на {webhook_url}')
        application.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=f'/webhook/{TOKEN}',
            webhook_url=webhook_url
        )
    else:
        # Локально — используем polling
        print("🔄 Локальный запуск, используем polling...")
        application.run_polling()


if __name__ == '__main__':
    main()