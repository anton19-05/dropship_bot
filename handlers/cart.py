import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from handlers.db import save_cart


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("cart_add_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    context.user_data[f"temp_product_{user_id}"] = product_code

    try:
        await query.message.delete()
    except:
        pass

    if product.has_sizes:
        sizes = product.get_sizes()
        
        size_buttons = []
        row = []
        for i, size_data in enumerate(sizes):
            size_value = size_data["value"]
            available = size_data.get("available", True)
            
            # Форматируем отображение
            if available:
                display = str(size_value)
                callback = f"cart_size_{product_code}_{size_value}"
            else:
                display = f"❌ {size_value}"
                callback = "noop"  # Неактивная кнопка
            
            row.append(InlineKeyboardButton(display, callback_data=callback))
            if (i + 1) % 3 == 0:
                size_buttons.append(row)
                row = []
        if row:
            size_buttons.append(row)
        
        size_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")])

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📏 *Выберите размер для {product.name}*\n\n❌ — размер отсутствует в наличии",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(size_buttons)
        )
    else:
        await add_quantity_selection(update, context, product_code)


async def cart_select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.replace("cart_size_", "")
    parts = data.split("_")
    product_code = parts[0]
    size = int(parts[1])
    context.user_data[f"temp_size_{user_id}"] = size
    await add_quantity_selection(update, context, product_code)


async def add_quantity_selection(update, context, product_code):
    query = update.callback_query
    user_id = query.from_user.id
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    quantity_buttons = [
        [InlineKeyboardButton("1 шт", callback_data=f"cart_qty_{product_code}_1"),
         InlineKeyboardButton("2 шт", callback_data=f"cart_qty_{product_code}_2"),
         InlineKeyboardButton("3 шт", callback_data=f"cart_qty_{product_code}_3")],
        [InlineKeyboardButton("4 шт", callback_data=f"cart_qty_{product_code}_4"),
         InlineKeyboardButton("5 шт", callback_data=f"cart_qty_{product_code}_5"),
         InlineKeyboardButton("6 шт", callback_data=f"cart_qty_{product_code}_6")],
        [InlineKeyboardButton("7 шт", callback_data=f"cart_qty_{product_code}_7"),
         InlineKeyboardButton("8 шт", callback_data=f"cart_qty_{product_code}_8"),
         InlineKeyboardButton("9 шт", callback_data=f"cart_qty_{product_code}_9")],
        [InlineKeyboardButton("10 шт", callback_data=f"cart_qty_{product_code}_10")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")]
    ]

    size = context.user_data.get(f"temp_size_{user_id}")
    size_text = f"размер {size}" if size else ""

    await query.edit_message_text(
        f"📏 *Выберите количество для {product.name}* {size_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(quantity_buttons)
    )


async def cart_confirm_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.replace("cart_qty_", "")
    parts = data.split("_")
    product_code = parts[0]
    quantity = int(parts[1])

    product = products_manager.get_by_code(product_code)
    size = context.user_data.get(f"temp_size_{user_id}")

    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    item_key = f"{product_code}_{size}" if size else product_code
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += quantity
    else:
        context.user_data[cart_key][item_key] = {
            "product_code": product_code,
            "size": size,
            "quantity": quantity,
            "name": product.name,
            "price": product.price
        }

    context.user_data.pop(f"temp_size_{user_id}", None)
    context.user_data.pop(f"temp_product_{user_id}", None)

    try:
        await query.message.delete()
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart"),
         InlineKeyboardButton("🔙 Назад к товару", callback_data=f"back_to_product_{product.id}")]
    ]

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"✅ *Товар добавлен в корзину!*\n\n👟 {product.name}\n{f'📏 Размер: {size}' if size else ''}\n📦 Количество: {quantity} шт",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Сохраняем корзину в SQLite
    save_cart(user_id, context.user_data[f"cart_{user_id}"])


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
    """Просмотр корзины с возможностью вернуться к товару"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    cart = context.user_data.get(f"cart_{user_id}", {})

    await msg_manager.clear(context.bot, chat_id, user_id)

    # Сохраняем контекст, откуда пришли
    context.user_data[f"cart_from_product_{user_id}"] = from_product_card

    if not cart:
        # Корзина пуста
        print(f"🔍 view_cart: from_product_card={from_product_card}, user_id={user_id}")
        
        if from_product_card:
            # Пришли из карточки товара → кнопка "Назад к товару"
            product_id = context.user_data.get(f"last_product_id_{user_id}")
            print(f"🔍 last_product_id_{user_id} = {product_id}")
            
            if product_id:
                back_button = [InlineKeyboardButton("🔙 Назад к товару", callback_data=f"back_to_product_{product_id}")]
                print(f"🔘 Создана кнопка с callback: back_to_product_{product_id}")
            else:
                back_button = [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
                print(f"🔘 product_id не найден, кнопка Назад на главную")
        else:
            # Пришли из профиля → кнопка "В профиль"
            back_button = [InlineKeyboardButton("🔙 В профиль", callback_data="profile")]
        
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🛒 *Корзина пуста*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([back_button])
        )
        await msg_manager.add(context.bot, chat_id, user_id, msg)
        return

    # Корзина не пуста
    total = 0
    for item_key, item in cart.items():
        product = products_manager.get_by_code(item["product_code"])
        if product:
            subtotal = item["price"] * item["quantity"]
            total += subtotal
            
            # Формируем текст с размером
            if item.get('size'):
                size_text = f"📏 Размер: {item['size']}"
            else:
                size_text = ""
            
            text = f"👟 *{product.name}*\n📦 {item['quantity']} шт\n{size_text}\n💰 {subtotal} руб"
            
            keyboard = [
                [InlineKeyboardButton("➖", callback_data=f"cart_decr_{item_key}"),
                 InlineKeyboardButton(f"{item['quantity']} шт", callback_data="noop"),
                 InlineKeyboardButton("➕", callback_data=f"cart_incr_{item_key}")],
                [InlineKeyboardButton("❌ Удалить", callback_data=f"cart_remove_{item_key}")],
                [InlineKeyboardButton("🔗 К товару", callback_data=f"goto_product_{product.id}")]
            ]
            photo = product.get_photo()
            try:
                if photo and os.path.exists(photo):
                    with open(photo, 'rb') as f:
                        msg = await context.bot.send_photo(
                            chat_id=chat_id, 
                            photo=f, 
                            caption=text, 
                            parse_mode="Markdown", 
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        await msg_manager.add(context.bot, chat_id, user_id, msg)
                else:
                    msg = await context.bot.send_message(
                        chat_id=chat_id, 
                        text=text, 
                        parse_mode="Markdown", 
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    await msg_manager.add(context.bot, chat_id, user_id, msg)
            except Exception as e:
                print(f"Ошибка отправки товара в корзине: {e}")
                msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text=text, 
                    parse_mode="Markdown", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await msg_manager.add(context.bot, chat_id, user_id, msg)

    # Кнопка оформления заказа
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💰 *ИТОГО: {total} руб*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
        ])
    )


async def cart_increase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_key = query.data.replace("cart_incr_", "")
    cart_key = f"cart_{user_id}"
    cart = context.user_data.get(cart_key, {})
    
    if item_key in cart:
        cart[item_key]["quantity"] += 1
        
        # ✅ СОХРАНЯЕМ КОРЗИНУ В ФАЙЛ
        from storage import save_user_data_sync
        save_user_data_sync(user_id, {cart_key: context.user_data[cart_key]}, context)
    
    await view_cart(update, context)


async def cart_decrease(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_key = query.data.replace("cart_decr_", "")
    cart_key = f"cart_{user_id}"
    cart = context.user_data.get(cart_key, {})
    
    if item_key in cart:
        if cart[item_key]["quantity"] > 1:
            cart[item_key]["quantity"] -= 1
        else:
            del cart[item_key]
        
        # ✅ СОХРАНЯЕМ КОРЗИНУ В ФАЙЛ
        from storage import save_user_data_sync
        save_user_data_sync(user_id, {cart_key: context.user_data[cart_key]}, context)
    
    await view_cart(update, context)


async def cart_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_key = query.data.replace("cart_remove_", "")
    cart_key = f"cart_{user_id}"
    cart = context.user_data.get(cart_key, {})
    
    if item_key in cart:
        del cart[item_key]
        
        # ✅ СОХРАНЯЕМ КОРЗИНУ В ФАЙЛ
        from storage import save_user_data_sync
        save_user_data_sync(user_id, {cart_key: context.user_data[cart_key]}, context)
    
    await view_cart(update, context)

async def view_cart_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр корзины из профиля"""
    await view_cart(update, context, from_product_card=False)


async def view_cart_from_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр корзины из карточки товара"""
    await view_cart(update, context, from_product_card=True)