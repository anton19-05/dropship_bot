from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync


async def add_to_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("fav_add_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    fav_key = f"favorites_{user_id}"
    if fav_key not in context.user_data:
        context.user_data[fav_key] = []

    if product_code not in context.user_data[fav_key]:
        context.user_data[fav_key].append(product_code)

    # ✅ СОХРАНЯЕМ ИЗБРАННОЕ В ФАЙЛ
    from storage import save_user_data_sync
    save_user_data_sync(user_id, {fav_key: context.user_data[fav_key]}, context)

    try:
        await query.message.delete()
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("❤️ Перейти в избранное", callback_data="view_favorites"),
         InlineKeyboardButton("🔙 Назад к товару", callback_data=f"back_to_product_{product.id}")]
    ]

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"✅ *Товар добавлен в избранное!*\n\n👟 {product.name}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def view_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    favorites = context.user_data.get(f"favorites_{user_id}", [])

    await msg_manager.clear(context.bot, chat_id, user_id)

    if not favorites:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="❤️ *Избранное пусто*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 В профиль", callback_data="profile")]])
        )
        await msg_manager.add(context.bot, chat_id, user_id, msg)
        return

    for product_code in favorites:
        product = products_manager.get_by_code(product_code)
        if product:
            text = f"❤️ *{product.name}*\n💰 {product.price} руб"
            keyboard = [
                [InlineKeyboardButton("🛒 В корзину", callback_data=f"fav_to_cart_{product_code}"),
                 InlineKeyboardButton("❌ Удалить", callback_data=f"fav_remove_{product_code}")],
                [InlineKeyboardButton(
                    "🔗 К товару", callback_data=f"goto_product_{product.id}")]
            ]
            photo = product.get_photo()
            if photo:
                with open(photo, 'rb') as f:
                    msg = await context.bot.send_photo(chat_id=chat_id, photo=f, caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                    await msg_manager.add(context.bot, chat_id, user_id, msg)
            else:
                msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                await msg_manager.add(context.bot, chat_id, user_id, msg)

    await context.bot.send_message(
        chat_id=chat_id,
        text="━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 В профиль", callback_data="profile")]])
    )


async def fav_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("fav_to_cart_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.edit_message_text("❌ Товар не найден!")
        return

    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    item_key = product_code
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += 1
    else:
        context.user_data[cart_key][item_key] = {
            "product_code": product_code,
            "size": None,
            "quantity": 1,
            "name": product.name,
            "price": product.price
        }

    await query.answer(f"✅ {product.name} добавлен в корзину!", show_alert=True)
    await view_favorites(update, context)


async def fav_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("fav_remove_", "")
    fav_key = f"favorites_{user_id}"

    if fav_key in context.user_data and product_code in context.user_data[fav_key]:
        context.user_data[fav_key].remove(product_code)
        
        # ✅ СОХРАНЯЕМ ИЗБРАННОЕ В ФАЙЛ
        from storage import save_user_data_sync
        save_user_data_sync(user_id, {fav_key: context.user_data[fav_key]}, context)

    await view_favorites(update, context)
