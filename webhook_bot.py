import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from config import TOKEN

# Импорты всех хендлеров
from handlers.profile import profile, edit_profile_start, handle_profile_input, editing_state
from handlers.favorites import add_to_favorites, view_favorites, fav_to_cart, fav_remove
from handlers.cart import (
    cart_callback_handler,    # ✅ универсальный обработчик cart_*
    view_cart,                # ✅ просмотр корзины
    cart_increase,            # ✅ увеличение количества
    cart_decrease,            # ✅ уменьшение количества
    cart_remove,              # ✅ удаление позиции
    view_cart_from_profile,   # ✅ корзина из профиля
    view_cart_from_product,   # ✅ корзина из карточки товара
    cart_remove_group,        # ✅ удаление группы (если используется)
    cart_select_size,         # ✅ выбор размера
    cart_confirm_quantity,    # ✅ подтверждение количества
    cart_incr_color,          # ✅ увеличение по цвету
    cart_decr_color,          # ✅ уменьшение по цвету
    cart_remove_color,        # ✅ удаление цвета
    clear_cart,
    cart_incr_group,
    cart_decr_group,
    cart_change_variant,
    cart_remove_all_variants
)
from handlers.order import order_start, order_handle, order_select_size, back_to_size, show_order_form, order_select_attr, order_confirm
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

    # --- КОМАНДЫ ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("checkdb", check_db))
    application.add_handler(CommandHandler("confirm", confirm_payment))
    
    # --- ГЛАВНОЕ МЕНЮ ---
    application.add_handler(CallbackQueryHandler(main_back, pattern="^main_back$"))
    application.add_handler(CallbackQueryHandler(profile, pattern="^menu_profile$"))
    application.add_handler(CallbackQueryHandler(catalog, pattern="^menu_catalog$"))
    
    # --- ЗАКАЗ ---
    application.add_handler(CallbackQueryHandler(order_select_size, pattern="^order_size_"))
    application.add_handler(CallbackQueryHandler(order_start, pattern="^order_"))
    application.add_handler(CallbackQueryHandler(back_to_size, pattern="^back_to_size_"))
    application.add_handler(CallbackQueryHandler(order_select_attr, pattern="^order_attr_"))
    application.add_handler(CallbackQueryHandler(order_select_size, pattern="^osz_"))
    application.add_handler(CallbackQueryHandler(order_select_attr, pattern="^oat_"))
    application.add_handler(CallbackQueryHandler(order_confirm, pattern="^ord_"))
    
    # ============================================================
    # ✅ КОРЗИНА — ПРАВИЛЬНЫЙ ПОРЯДОК
    # ============================================================
    
    # 1. УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК для cart_* (cart_attr_, cart_confirm_, cart_add_)
    application.add_handler(CallbackQueryHandler(cart_callback_handler, pattern="^cart_"))
    
    # 2. ОТДЕЛЬНЫЕ ОБРАБОТЧИКИ (не начинаются с cart_)
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(view_cart_from_product, pattern="^view_cart_from_product$"))
    application.add_handler(CallbackQueryHandler(view_cart_from_profile, pattern="^view_cart_from_profile$"))
    application.add_handler(CallbackQueryHandler(cart_increase, pattern="^cart_incr_"))
    application.add_handler(CallbackQueryHandler(cart_decrease, pattern="^cart_decr_"))
    application.add_handler(CallbackQueryHandler(cart_remove, pattern="^cart_remove_"))
    application.add_handler(CallbackQueryHandler(cart_remove_group, pattern="^cart_remove_group_"))
    application.add_handler(CallbackQueryHandler(cart_change_variant, pattern="^cart_change_"))
    application.add_handler(CallbackQueryHandler(cart_remove_all_variants, pattern="^cart_remove_all_"))
    
    # 3. ДЛЯ РАЗМЕРОВ (если не используются через универсальный)
    application.add_handler(CallbackQueryHandler(cart_select_size, pattern="^cart_size_"))
    application.add_handler(CallbackQueryHandler(cart_confirm_quantity, pattern="^cart_qty_"))
    
    # --- КАТАЛОГ ---
    application.add_handler(CallbackQueryHandler(change_page, pattern="^page_"))
    application.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(change_color, pattern="^color_"))
    application.add_handler(CallbackQueryHandler(back_to_catalog, pattern="^back_to_catalog$"))
    application.add_handler(CallbackQueryHandler(back_to_product, pattern="^back_to_product_"))
    application.add_handler(CallbackQueryHandler(goto_product, pattern="^goto_product_"))
    application.add_handler(CallbackQueryHandler(back_to_category, pattern="^back_to_category_"))
    application.add_handler(CallbackQueryHandler(back_to_catalog_from_products, pattern="^back_to_catalog_from_products$"))
    application.add_handler(CallbackQueryHandler(select_attribute, pattern="^attr_"))
    
    # --- КАТЕГОРИИ ---
    application.add_handler(CallbackQueryHandler(show_category_by_id, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(show_subcategory_products, pattern="^subcat_"))

        # ============================================================
    # КОРЗИНА (группировка по цвету)
    # ============================================================
    
    # 1. УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК для cart_*
    application.add_handler(CallbackQueryHandler(cart_callback_handler, pattern="^cart_"))
    
    # 2. ОТДЕЛЬНЫЕ ОБРАБОТЧИКИ
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(view_cart_from_product, pattern="^view_cart_from_product$"))
    application.add_handler(CallbackQueryHandler(view_cart_from_profile, pattern="^view_cart_from_profile$"))
    application.add_handler(CallbackQueryHandler(cart_increase, pattern="^cart_incr_"))
    application.add_handler(CallbackQueryHandler(cart_decrease, pattern="^cart_decr_"))
    application.add_handler(CallbackQueryHandler(cart_remove, pattern="^cart_remove_"))
    
    # 3. ДЛЯ РАЗМЕРОВ
    application.add_handler(CallbackQueryHandler(cart_select_size, pattern="^cart_size_"))
    application.add_handler(CallbackQueryHandler(cart_confirm_quantity, pattern="^cart_qty_"))
    
    # 4. ДЛЯ ГРУППИРОВКИ ПО ЦВЕТУ (НОВЫЕ)
    application.add_handler(CallbackQueryHandler(cart_incr_color, pattern="^cart_incr_color_"))
    application.add_handler(CallbackQueryHandler(cart_decr_color, pattern="^cart_decr_color_"))
    application.add_handler(CallbackQueryHandler(cart_remove_color, pattern="^cart_remove_color_"))
    application.add_handler(CallbackQueryHandler(clear_cart, pattern="^clear_cart$"))
    application.add_handler(CallbackQueryHandler(cart_incr_group, pattern="^cart_incr_group_"))
    application.add_handler(CallbackQueryHandler(cart_decr_group, pattern="^cart_decr_group_"))
    application.add_handler(CallbackQueryHandler(cart_remove_group, pattern="^cart_remove_group_"))
    
    # --- ОТЗЫВЫ ---
    application.add_handler(CallbackQueryHandler(show_reviews, pattern="^reviews_"))
    application.add_handler(CallbackQueryHandler(review_next, pattern="^review_next$"))
    application.add_handler(CallbackQueryHandler(review_prev, pattern="^review_prev$"))
    application.add_handler(CallbackQueryHandler(back_to_product_from_reviews, pattern="^back_to_product_from_reviews_"))
    
    # --- ИЗБРАННОЕ ---
    application.add_handler(CallbackQueryHandler(add_to_favorites, pattern="^fav_add_"))
    application.add_handler(CallbackQueryHandler(view_favorites, pattern="^view_favorites$"))
    application.add_handler(CallbackQueryHandler(fav_to_cart, pattern="^fav_to_cart_"))
    application.add_handler(CallbackQueryHandler(fav_remove, pattern="^fav_remove_"))
    
    # --- ПРОФИЛЬ ---
    application.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile_start$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile$"))
    application.add_handler(CallbackQueryHandler(edit_profile_start, pattern="^edit_profile_change$"))
    
    # --- ПЛАТЕЖИ ---
    application.add_handler(CallbackQueryHandler(payment_success, pattern="^payment_success$"))
    application.add_handler(CallbackQueryHandler(check_payment_status, pattern="^check_payment_"))
    
    # --- ТЕКСТ ---
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))

    # --- НЕАКТИВНЫЕ КНОПКИ ---
    async def noop(update: Update, context):
        query = update.callback_query
        await query.answer("⛔ Эта кнопка неактивна", show_alert=True)
    application.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))

    # --- ВОССТАНОВЛЕНИЕ ДАННЫХ ---
    all_data = load_user_data()
    for user_id_str, user_data in all_data.items():
        user_id = int(user_id_str)
        application.user_data[user_id] = user_data
    print(f"✅ Восстановлено {len(all_data)} профилей пользователей")

    # --- ЗАПУСК ---
    port = int(os.environ.get('PORT', 10000))
    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_hostname:
        webhook_url = f'https://{render_hostname}/webhook/{TOKEN}'
        print(f'🔄 Устанавливаем вебхук на {webhook_url}')
        application.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=f'/webhook/{TOKEN}',
            webhook_url=webhook_url
        )
    else:
        print("🔄 Локальный запуск, используем polling...")
        application.run_polling()


if __name__ == '__main__':
    main()