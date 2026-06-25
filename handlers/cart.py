import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync
from config import ADMIN_ID

# Настраиваем логирование
logger = logging.getLogger(__name__)

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_code = query.data.replace("cart_add_", "")
    
    logger.info(f"🔍 add_to_cart: user_id={user_id}, product_code={product_code}")
    
    product = products_manager.get_by_code(product_code)

    if not product:
        logger.error(f"❌ add_to_cart: товар не найден! product_code={product_code}")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    logger.info(f"✅ add_to_cart: товар найден: {product.name} (id: {product.id})")
    
    # ✅ ПОКАЗЫВАЕМ ВЫБОР АТРИБУТОВ ПЕРЕД ДОБАВЛЕНИЕМ
    attrs = product.get_extra_attributes()
    logger.info(f"📋 add_to_cart: атрибуты: {list(attrs.keys())}")
    
    keyboard = []
    
    # 1. Размеры (если есть)
    if product.has_sizes:
        sizes = product.get_sizes()
        size_row = []
        selected_size = context.user_data.get(f"cart_size_{user_id}")
        logger.info(f"📏 add_to_cart: sizes={sizes}, selected_size={selected_size}")
        
        for size in sizes:
            size_value = size["value"] if isinstance(size, dict) else size
            marker = "✅ " if str(selected_size) == str(size_value) else ""
            size_row.append(InlineKeyboardButton(
                f"{marker}{size_value}",
                callback_data=f"cart_attr_{product_code}_size_{size_value}"
            ))
            if len(size_row) == 3:
                keyboard.append(size_row)
                size_row = []
        if size_row:
            keyboard.append(size_row)
    
    # 2. Остальные атрибуты (не main и не colors)
    for key, value in attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, list):
            logger.info(f"📌 add_to_cart: атрибут {key} = {value}")
            row = []
            for item in value:
                item_str = str(item)
                selected = context.user_data.get(f"cart_attr_{key}_{user_id}") == item_str
                marker = "✅ " if selected else ""
                encoded_value = item_str.replace(" ", "_").replace("мАч", "mah").replace("W", "w")
                row.append(InlineKeyboardButton(
                    f"{marker}{item_str}",
                    callback_data=f"cart_attr_{product_code}_{key}_{encoded_value}"
                ))
            if row:
                display_name = key.capitalize()
                keyboard.append([InlineKeyboardButton(f"📌 {display_name}:", callback_data="noop")])
                for i in range(0, len(row), 3):
                    keyboard.append(row[i:i+3])
    
    # 3. Кнопка "Добавить в корзину"
    keyboard.append([InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"cart_confirm_{product_code}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")])
    
    context.user_data[f"cart_product_{user_id}"] = product_code
    
    # Формируем текст с уже выбранными атрибутами
    selected_text = ""
    main_attrs = product.get_main_attributes()
    for attr_key in main_attrs.keys():
        value = context.user_data.get(f"attr_{attr_key}_{user_id}")
        if value:
            selected_text += f"\n📌 {attr_key.capitalize()}: {value}"
    
    text = (f"🛒 *ДОБАВЛЕНИЕ В КОРЗИНУ*\n\n"
            f"👟 {product.name}\n"
            f"💰 {product.price} руб\n"
            f"{selected_text}\n\n"
            f"👇 Выберите параметры:")
    
    logger.info(f"📤 add_to_cart: отправка сообщения с клавиатурой, rows={len(keyboard)}")
    
    # ✅ БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"✅ add_to_cart: сообщение отредактировано")
    except Exception as e:
        logger.error(f"❌ add_to_cart: ошибка редактирования: {e}")
        if "There is no text in the message to edit" in str(e):
            try:
                await query.message.delete()
                logger.info("🗑️ add_to_cart: сообщение удалено")
            except Exception as delete_error:
                logger.error(f"❌ add_to_cart: ошибка удаления: {delete_error}")
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info("✅ add_to_cart: новое сообщение отправлено")
        else:
            raise


async def cart_select_attr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор атрибута при добавлении в корзину"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.replace("cart_attr_", "")
    parts = data.split("_")
    
    logger.info(f"🔍 cart_select_attr: user_id={user_id}, data={data}, parts={parts}")
    
    product_code = parts[0]
    
    if len(parts) >= 3:
        attr_key = parts[1]
        attr_value = "_".join(parts[2:])
        attr_value = attr_value.replace("_", " ").replace("mah", "мАч").replace("w", "W")
        
        if attr_key == "size":
            context.user_data[f"cart_size_{user_id}"] = attr_value
            logger.info(f"✅ cart_select_attr: размер выбран: {attr_value}")
        else:
            context.user_data[f"cart_attr_{attr_key}_{user_id}"] = attr_value
            logger.info(f"✅ cart_select_attr: {attr_key} = {attr_value}")
    else:
        logger.warning(f"⚠️ cart_select_attr: недостаточно данных: {parts}")
    
    # Обновляем окно выбора атрибутов
    await add_to_cart(update, context)


async def cart_confirm_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение добавления в корзину с выбранными атрибутами"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_code = query.data.replace("cart_confirm_", "")
    
    logger.info(f"🔍 cart_confirm_add: user_id={user_id}, product_code={product_code}")
    
    product = products_manager.get_by_code(product_code)
    
    if not product:
        logger.error(f"❌ cart_confirm_add: товар не найден! product_code={product_code}")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    color = context.user_data.get(f"color_{user_id}", "белый")
    size = context.user_data.get(f"cart_size_{user_id}")
    
    logger.info(f"📋 cart_confirm_add: color={color}, size={size}")
    
    attrs = product.get_extra_attributes()
    selected_attrs = {}
    for key in attrs.keys():
        if key not in ["colors", "sizes"]:
            attr_value = context.user_data.get(f"cart_attr_{key}_{user_id}")
            if attr_value:
                selected_attrs[key] = attr_value
                logger.info(f"✅ cart_confirm_add: {key} = {attr_value}")
    
    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    item_key = f"{product_code}_{size}" if size else product_code
    logger.info(f"📦 cart_confirm_add: item_key={item_key}")
    
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += 1
        logger.info(f"✅ cart_confirm_add: количество увеличено до {context.user_data[cart_key][item_key]['quantity']}")
    else:
        item_data = {
            "product_code": product_code,
            "quantity": 1,
            "name": product.name,
            "price": product.price,
            "color": color,
            "size": size,
            **selected_attrs
        }
        context.user_data[cart_key][item_key] = item_data
        logger.info(f"✅ cart_confirm_add: новый товар добавлен в корзину")

    # Очищаем временные данные
    context.user_data.pop(f"cart_size_{user_id}", None)
    for key in attrs.keys():
        if key not in ["colors", "sizes"]:
            context.user_data.pop(f"cart_attr_{key}_{user_id}", None)
    context.user_data.pop(f"cart_product_{user_id}", None)

    # Формируем текст
    attrs_text = f"\n🎨 Цвет: {color}"
    if size:
        attrs_text += f"\n📏 Размер: {size}"
    for key, value in selected_attrs.items():
        attrs_text += f"\n📌 {key.capitalize()}: {value}"

    text = f"✅ *{product.name} добавлен в корзину!*{attrs_text}"
    logger.info(f"✅ cart_confirm_add: {text}")

    # ✅ БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart")],
                [InlineKeyboardButton("🔙 Продолжить покупки", callback_data="main_back")]
            ])
        )
        logger.info("✅ cart_confirm_add: сообщение отредактировано")
    except Exception as e:
        logger.error(f"❌ cart_confirm_add: ошибка редактирования: {e}")
        if "There is no text in the message to edit" in str(e):
            try:
                await query.message.delete()
                logger.info("🗑️ cart_confirm_add: сообщение удалено")
            except:
                pass
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart")],
                    [InlineKeyboardButton("🔙 Продолжить покупки", callback_data="main_back")]
                ])
            )
            logger.info("✅ cart_confirm_add: новое сообщение отправлено")
        else:
            raise


# ============================================================
# ОСТАЛЬНЫЕ ФУНКЦИИ (без изменений)
# ============================================================

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
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
            if item.get('color'):
                text += f"\n🎨 Цвет: {item['color']}"
            if item.get('size'):
                text += f"\n📏 Размер: {item['size']}"
            if item.get('main_attr'):
                text += f"\n📌 {item['main_attr']}"
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
    color = context.user_data.get(f"color_{user_id}", "белый")

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