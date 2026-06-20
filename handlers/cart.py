import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync
from config import ADMIN_ID


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("cart_add_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Получаем цвет
    color = context.user_data.get(f"color_{user_id}", "белый")
    
    # Получаем ВСЕ выбранные атрибуты (кроме colors)
    attrs = product.get_attributes()
    selected_attrs = {}
    for key, value in attrs.items():
        if key == "colors":
            continue
        if isinstance(value, dict) and value.get("type") == "main":
            attr_value = context.user_data.get(f"attr_{key}_{user_id}")
            if attr_value:
                selected_attrs[key] = attr_value
        elif isinstance(value, list):
            # Для обычных атрибутов (списков) пока не сохраняем, они будут при заказе
            pass

    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    item_key = product_code
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += 1
    else:
        item_data = {
            "product_code": product_code,
            "quantity": 1,
            "name": product.name,
            "price": product.price,
            "color": color,
        }
        # Добавляем все выбранные атрибуты
        for key, value in selected_attrs.items():
            item_data[key] = value
        
        context.user_data[cart_key][item_key] = item_data

    # Формируем текст с выбранными атрибутами
    attrs_text = f"\n🎨 Цвет: {color}"
    for key, value in selected_attrs.items():
        attrs_text += f"\n📌 {key}: {value}"

    await query.edit_message_text(
        f"✅ *{product.name} добавлен в корзину!*{attrs_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart")]
        ])
    )


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

    # ✅ ВСЕГДА ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ (НЕ РЕДАКТИРУЕМ!)
    # Удаляем сообщение с выбором размера
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"📏 *Выберите количество для {product.name}* {size_text}",
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
    color = context.user_data.get(f"color_{user_id}", "белый") # Цвет сохраняется здесь

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
            "color": color,
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
        text=f"✅ *Товар добавлен в корзину!*\n\n👟 {product.name}\n{f'📏 Размер: {size}' if size else ''}\n{f'🎨 Цвет: {color}' if color else ''}\n📦 Количество: {quantity} шт",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    if not cart:
        await query.edit_message_text("🛒 *Корзина пуста*", parse_mode="Markdown")
        return
    
    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for item in cart.values():
        text += f"• {item['name']} — {item['quantity']} шт"
        if item.get('color'):
            text += f" (цвет: {item['color']})"
        if item.get('main_attr'):
            text += f" ({item['main_attr']})"
        text += f" — {item['price'] * item['quantity']} руб\n"
        total += item['price'] * item['quantity']
    
    text += f"\n💰 *ИТОГО: {total} руб*"
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")]
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
        save_user_data_sync(user_id, {cart_key: context.user_data[cart_key]}, context)
    
    await view_cart(update, context)


async def view_cart_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_cart(update, context, from_product_card=False)


async def view_cart_from_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_cart(update, context, from_product_card=True)

async def cart_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все варианты одного товара из корзины"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("cart_remove_group_", "")
    cart_key = f"cart_{user_id}"
    cart = context.user_data.get(cart_key, {})
    
    items_to_remove = [key for key in cart.keys() if cart[key]["product_code"] == product_code]
    for key in items_to_remove:
        del cart[key]
    
    if cart:
        context.user_data[cart_key] = cart
    else:
        context.user_data.pop(cart_key, None)
    
    from storage import save_user_data_sync
    save_user_data_sync(user_id, {cart_key: context.user_data.get(cart_key, {})}, context)
    
    await view_cart(update, context)