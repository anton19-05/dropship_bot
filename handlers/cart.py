import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔍 add_to_cart ВЫЗВАНА! data={update.callback_query.data}")
    query = update.callback_query
    await query.answer()
    # ... остальной код
    user_id = query.from_user.id
    product_code = query.data.replace("cart_add_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Сохраняем выбранные атрибуты
    color = context.user_data.get(f"color_{user_id}", "белый")
    
    attrs = product.get_attributes()
    selected_attrs = {}
    for key in attrs.keys():
        if key != "colors":
            attr_value = context.user_data.get(f"attr_{key}_{user_id}")
            if attr_value:
                selected_attrs[key] = attr_value

    context.user_data[f"temp_product_{user_id}"] = product_code
    context.user_data[f"temp_color_{user_id}"] = color
    context.user_data[f"temp_attrs_{user_id}"] = selected_attrs

    # ... остальной код (выбор размера)

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
            
            if available:
                display = str(size_value)
                callback = f"cart_size_{product_code}_{size_value}"
            else:
                display = f"❌ {size_value}"
                callback = "noop"
            
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
    color = context.user_data.get(f"temp_color_{user_id}", "белый")
    selected_attrs = context.user_data.get(f"temp_attrs_{user_id}", {})

    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    item_key = f"{product_code}_{size}" if size else product_code
    
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += quantity
    else:
        item_data = {
            "product_code": product_code,
            "quantity": quantity,
            "name": product.name,
            "price": product.price,
            "size": size,
            "color": color,
        }
        # Добавляем все выбранные атрибуты
        for key, value in selected_attrs.items():
            item_data[key] = value
        
        context.user_data[cart_key][item_key] = item_data

    context.user_data.pop(f"temp_size_{user_id}", None)
    context.user_data.pop(f"temp_color_{user_id}", None)
    context.user_data.pop(f"temp_attrs_{user_id}", None)

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

    from storage import save_user_data_sync
    save_user_data_sync(user_id, {cart_key: context.user_data[cart_key]}, context)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
    """Показывает корзину с группировкой по товарам и динамическими атрибутами"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    cart = context.user_data.get(f"cart_{user_id}", {})

    await msg_manager.clear(context.bot, chat_id, user_id)

    context.user_data[f"cart_from_product_{user_id}"] = from_product_card

    if not cart:
        if from_product_card:
            product_id = context.user_data.get(f"last_product_id_{user_id}")
            if product_id:
                back_button = [InlineKeyboardButton("🔙 Назад к товару", callback_data=f"back_to_product_{product_id}")]
            else:
                back_button = [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
        else:
            back_button = [InlineKeyboardButton("🔙 В профиль", callback_data="profile")]
        
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🛒 *Корзина пуста*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([back_button])
        )
        await msg_manager.add(context.bot, chat_id, user_id, msg)
        return

    # ✅ ГРУППИРУЕМ ТОВАРЫ ПО product_code
    grouped_cart = {}
    for item_key, item in cart.items():
        product_code = item["product_code"]
        if product_code not in grouped_cart:
            grouped_cart[product_code] = {
                "product_code": product_code,
                "name": item["name"],
                "price": item["price"],
                "variants": [],
                "total_quantity": 0,
                "total_price": 0
            }
        grouped_cart[product_code]["variants"].append({
            "size": item.get("size"),
            "color": item.get("color"),
            "quantity": item["quantity"],
            "item_key": item_key,
            **{k: v for k, v in item.items() if k not in ["product_code", "name", "price", "quantity", "item_key", "size", "color"]}
        })
        grouped_cart[product_code]["total_quantity"] += item["quantity"]
        grouped_cart[product_code]["total_price"] += item["price"] * item["quantity"]

    # Показываем каждый товар с его вариантами
    for product_code, group in grouped_cart.items():
        product = products_manager.get_by_code(product_code)
        
        text = f"👟 *{group['name']}*\n"
        text += f"💰 {group['price']} руб/шт\n"
        text += f"📦 Всего: {group['total_quantity']} шт\n"
        text += f"💵 Итого: {group['total_price']} руб\n\n"
        
        # ✅ ДИНАМИЧЕСКИЕ АТРИБУТЫ
        text += "📋 *Варианты:*\n"
        for variant in group["variants"]:
            attrs = []
            
            # Основные атрибуты с русскими названиями
            attr_map = {
                "color": "цвет",
                "size": "размер",
                "length": "длина",
                "capacity": "емкость",
                "weight": "вес",
                "material": "материал",
                "volume": "объем",
                "power": "мощность",
                "screen": "экран",
                "memory": "память",
                "type": "тип",
                "model": "модель",
                "brand": "бренд"
            }
            
            for key, label in attr_map.items():
                if variant.get(key):
                    attrs.append(f"{label}: {variant[key]}")
            
            if not attrs:
                exclude = ["product_code", "name", "price", "quantity", "item_key", "product_id"]
                for key, value in variant.items():
                    if key not in exclude and value:
                        attrs.append(f"{key}: {value}")
            
            attrs_text = ", ".join(attrs) if attrs else "стандартный"
            text += f"• {attrs_text} — {variant['quantity']} шт\n"
        
        # Кнопки управления
        keyboard = []
        for variant in group["variants"]:
            # Формируем подпись для кнопки
            label_parts = []
            if variant.get("color"):
                label_parts.append(variant["color"])
            if variant.get("size"):
                label_parts.append(f"р-р {variant['size']}")
            if variant.get("length"):
                label_parts.append(variant["length"])
            if variant.get("capacity"):
                label_parts.append(variant["capacity"])
            if variant.get("model"):
                label_parts.append(variant["model"])
            
            label = " ".join(label_parts) if label_parts else "товар"
            
            keyboard.append([
                InlineKeyboardButton("➖", callback_data=f"cart_decr_{variant['item_key']}"),
                InlineKeyboardButton(f"{variant['quantity']} шт", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"cart_incr_{variant['item_key']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🗑️ Удалить все", callback_data=f"cart_remove_group_{product_code}")
        ])
        
        if product:
            keyboard.append([
                InlineKeyboardButton("🔗 К товару", callback_data=f"goto_product_{product.id}")
            ])
        
        photo = product.get_photo() if product else None
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

    # Итоговая сумма
    total_sum = sum(group["total_price"] for group in grouped_cart.values())
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💰 *ИТОГО К ОПЛАТЕ: {total_sum} руб*",
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