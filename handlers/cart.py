import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync
from config import ADMIN_ID


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор атрибутов для добавления в корзину"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product_code = query.data.replace("cart_add_", "")
    product = products_manager.get_by_code(product_code)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Получаем все атрибуты (кроме главных, они уже выбраны в карточке)
    extra_attrs = product.get_extra_attributes()
    main_attrs = product.get_main_attributes()
    
    keyboard = []
    
    # ============================================================
    # 1. Показываем уже выбранные главные атрибуты (информация)
    # ============================================================
    if main_attrs:
        selected_info = []
        for attr_key in main_attrs.keys():
            value = context.user_data.get(f"attr_{attr_key}_{user_id}")
            if value:
                selected_info.append(f"{attr_key.capitalize()}: {value}")
        
        if selected_info:
            keyboard.append([InlineKeyboardButton(
                f"✅ Выбрано: {', '.join(selected_info)}",
                callback_data="noop"
            )])
    
    # ============================================================
    # 2. РАЗМЕРЫ (если есть)
    # ============================================================
    if product.has_sizes:
        sizes = product.get_sizes()
        size_row = []
        selected_size = context.user_data.get(f"cart_size_{user_id}")
        
        keyboard.append([InlineKeyboardButton("📏 Размер:", callback_data="noop")])
        
        for size in sizes:
            size_value = size["value"] if isinstance(size, dict) else size
            marker = "✅ " if str(selected_size) == str(size_value) else ""
            size_row.append(InlineKeyboardButton(
                f"{marker}{size_value}",
                callback_data=f"cart_size_{product_code}_{size_value}"
            ))
            if len(size_row) == 3:
                keyboard.append(size_row)
                size_row = []
        if size_row:
            keyboard.append(size_row)
    
    # ============================================================
    # 3. ОСТАЛЬНЫЕ АТРИБУТЫ (кроме main и sizes)
    # ============================================================
    for key, value in extra_attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, list):
            row = []
            short_key = key[:3]
            selected = context.user_data.get(f"cart_attr_{key}_{user_id}")
            
            keyboard.append([InlineKeyboardButton(f"📌 {key.capitalize()}:", callback_data="noop")])
            
            for item in value:
                item_str = str(item)
                marker = "✅ " if selected == item_str else ""
                row.append(InlineKeyboardButton(
                    f"{marker}{item_str}",
                    callback_data=f"cart_attr_{product_code}_{short_key}_{item_str}"
                ))
            
            for i in range(0, len(row), 3):
                keyboard.append(row[i:i+3])
    
    # ============================================================
    # 4. КНОПКИ
    # ============================================================
    keyboard.append([InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"cart_confirm_{product_code}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")])
    
    # Сохраняем product_code для последующего добавления
    context.user_data[f"cart_product_{user_id}"] = product_code
    
    await query.edit_message_text(
        text=f"🛒 *ДОБАВЛЕНИЕ В КОРЗИНУ*\n\n"
             f"👟 {product.name}\n"
             f"💰 {product.price} руб\n\n"
             f"👇 Выберите параметры:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cart_select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор размера при добавлении в корзину"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.replace("cart_size_", "")
    parts = data.split("_")
    product_code = parts[0]
    size = parts[1]
    
    context.user_data[f"cart_size_{user_id}"] = size
    
    # Обновляем окно выбора атрибутов
    await add_to_cart(update, context)


async def cart_select_attr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор атрибута при добавлении в корзину"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.replace("cart_attr_", "")
    parts = data.split("_")
    
    product_code = parts[0]
    
    if parts[1] == "size":
        size = parts[2]
        context.user_data[f"cart_size_{user_id}"] = size
    else:
        attr_key = parts[1]
        attr_value = "_".join(parts[2:])
        context.user_data[f"cart_attr_{attr_key}_{user_id}"] = attr_value
    
    # Обновляем окно выбора атрибутов
    await add_to_cart(update, context)


async def cart_confirm_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение добавления в корзину с выбранными атрибутами"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_code = query.data.replace("cart_confirm_", "")
    product = products_manager.get_by_code(product_code)
    
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    # Собираем все выбранные атрибуты
    # 1. Главные атрибуты (из карточки)
    main_attrs = product.get_main_attributes()
    selected_main = {}
    for attr_key in main_attrs.keys():
        value = context.user_data.get(f"attr_{attr_key}_{user_id}")
        if value:
            selected_main[attr_key] = value
    
    # 2. Размер
    size = context.user_data.get(f"cart_size_{user_id}")
    
    # 3. Остальные атрибуты
    extra_attrs = product.get_extra_attributes()
    selected_attrs = {}
    for key in extra_attrs.keys():
        if key in ["colors", "sizes"]:
            continue
        attr_value = context.user_data.get(f"cart_attr_{key}_{user_id}")
        if attr_value:
            selected_attrs[key] = attr_value
    
    # Добавляем в корзину
    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    # Формируем ключ для корзины
    size_part = f"_{size}" if size else ""
    item_key = f"{product_code}{size_part}"
    
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += 1
    else:
        item_data = {
            "product_code": product_code,
            "quantity": 1,
            "name": product.name,
            "price": product.price,
            "size": size,
            **selected_main,
            **selected_attrs
        }
        context.user_data[cart_key][item_key] = item_data

    # Очищаем временные данные
    context.user_data.pop(f"cart_size_{user_id}", None)
    for key in extra_attrs.keys():
        if key not in ["colors", "sizes"]:
            context.user_data.pop(f"cart_attr_{key}_{user_id}", None)
    context.user_data.pop(f"cart_product_{user_id}", None)

    # Формируем текст
    attrs_text = ""
    if size:
        attrs_text += f"\n📏 Размер: {size}"
    for key, value in selected_main.items():
        attrs_text += f"\n📌 {key.capitalize()}: {value}"
    for key, value in selected_attrs.items():
        attrs_text += f"\n📌 {key.capitalize()}: {value}"

    await query.edit_message_text(
        text=f"✅ *{product.name} добавлен в корзину!*{attrs_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart")],
            [InlineKeyboardButton("🔙 Продолжить покупки", callback_data="main_back")]
        ])
    )


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
    """Показывает корзину пользователя"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    cart = context.user_data.get(f"cart_{user_id}", {})

    await msg_manager.clear(context.bot, chat_id, user_id)

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

    total = 0
    for item_key, item in cart.items():
        product = products_manager.get_by_code(item["product_code"])
        if product:
            subtotal = item["price"] * item["quantity"]
            total += subtotal
            
            text = f"👟 *{product.name}*\n📦 {item['quantity']} шт"
            
            # Добавляем все атрибуты
            if item.get('size'):
                text += f"\n📏 Размер: {item['size']}"
            
            # Главные атрибуты
            main_attrs = product.get_main_attributes()
            for attr_key in main_attrs.keys():
                if item.get(attr_key):
                    text += f"\n📌 {attr_key.capitalize()}: {item[attr_key]}"
            
            # Остальные атрибуты
            extra_attrs = product.get_extra_attributes()
            for key in extra_attrs.keys():
                if key not in ["colors", "sizes"] and item.get(key):
                    text += f"\n📌 {key.capitalize()}: {item[key]}"
            
            text += f"\n💰 {subtotal} руб"
            
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
    
    save_user_data_sync(user_id, {cart_key: context.user_data.get(cart_key, {})}, context)
    
    await view_cart(update, context)