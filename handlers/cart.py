import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync
from config import ADMIN_ID

logger = logging.getLogger(__name__)


async def cart_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК для всех cart_* callback'ов
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    logger.info(f"🔍 cart_callback_handler: data={data}")
    
    # ============================================================
    # 1. ВЫБОР АТРИБУТА (cart_attr_)
    # ============================================================
    if data.startswith("cart_attr_"):
        # Парсим: cart_attr_PB-20000_емкость_10000_mah
        parts = data.replace("cart_attr_", "").split("_")
        logger.info(f"📋 cart_attr: parts={parts}")
        
        if len(parts) >= 3:
            product_code = parts[0]
            attr_key = parts[1]
            attr_value = "_".join(parts[2:])
            attr_value = attr_value.replace("_", " ").replace("mah", "мАч").replace("w", "W")
            
            if attr_key == "size":
                context.user_data[f"cart_size_{user_id}"] = attr_value
                logger.info(f"✅ Размер выбран: {attr_value}")
            else:
                context.user_data[f"cart_attr_{attr_key}_{user_id}"] = attr_value
                logger.info(f"✅ Атрибут {attr_key} = {attr_value}")
            
            # Обновляем окно выбора атрибутов
            await show_cart_attributes(update, context, product_code)
            return
    
    # ============================================================
    # 2. ПОДТВЕРЖДЕНИЕ ДОБАВЛЕНИЯ (cart_confirm_)
    # ============================================================
    elif data.startswith("cart_confirm_"):
        product_code = data.replace("cart_confirm_", "")
        await confirm_add_to_cart(update, context, product_code)
        return
    
    # ============================================================
    # 3. ДОБАВЛЕНИЕ В КОРЗИНУ (cart_add_)
    # ============================================================
    elif data.startswith("cart_add_"):
        product_code = data.replace("cart_add_", "")
        await show_cart_attributes(update, context, product_code)
        return


async def show_cart_attributes(update: Update, context: ContextTypes.DEFAULT_TYPE, product_code: str):
    """Показывает выбор атрибутов перед добавлением в корзину"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # ✅ ДИАГНОСТИКА
    print(f"🔍 [DIAGNOSTIC] show_cart_attributes: user_id={user_id}, product_code={product_code}")
    
    product = products_manager.get_by_code(product_code)
    
    if not product:
        logger.error(f"❌ Товар не найден! product_code={product_code}")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    # ✅ ПОЛУЧАЕМ ЦВЕТ
    color = context.user_data.get(f"attr_colors_{user_id}")
    if not color:
        color = context.user_data.get(f"color_{user_id}", "белый")
    
    print(f"✅ [DIAGNOSTIC] show_cart_attributes: color={color}")
    print(f"📋 [DIAGNOSTIC] attr_colors_{user_id} = {context.user_data.get(f'attr_colors_{user_id}')}")
    print(f"📋 [DIAGNOSTIC] color_{user_id} = {context.user_data.get(f'color_{user_id}')}")
    
    # ... остальной код ...
    
    logger.info(f"✅ Товар найден: {product.name}")
    
    attrs = product.get_extra_attributes()
    keyboard = []
    
    # 1. Размеры
    if product.has_sizes:
        sizes = product.get_sizes()
        size_row = []
        selected_size = context.user_data.get(f"cart_size_{user_id}")
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
    
    # 2. Остальные атрибуты
    for key, value in attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, list):
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
    
    # 3. Кнопки управления
    keyboard.append([InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"cart_confirm_{product_code}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_product_{product.id}")])
    
    context.user_data[f"cart_product_{user_id}"] = product_code
    
    # Текст
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
    
    # Удаляем старое и отправляем новое
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    logger.info("✅ Показаны атрибуты для добавления в корзину")


async def confirm_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, product_code: str):
    """Подтверждение добавления в корзину"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    product = products_manager.get_by_code(product_code)
    
    if not product:
        logger.error(f"❌ Товар не найден! product_code={product_code}")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    # ✅ ПОЛУЧАЕМ ЦВЕТ
    color = context.user_data.get(f"attr_colors_{user_id}")
    if not color:
        color = context.user_data.get(f"color_{user_id}", "белый")
    
    size = context.user_data.get(f"cart_size_{user_id}")
    
    print(f"✅ [DIAGNOSTIC] confirm_add_to_cart: color={color}, size={size}")
    
    attrs = product.get_extra_attributes()
    selected_attrs = {}
    for key in attrs.keys():
        if key not in ["colors", "sizes"]:
            attr_value = context.user_data.get(f"cart_attr_{key}_{user_id}")
            if attr_value:
                selected_attrs[key] = attr_value
    
    # Добавляем в корзину
    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    # ✅ ИСПРАВЛЕНО: ключ с УЧЕТОМ ЦВЕТА
    if size:
        item_key = f"{product_code}_{color}_{size}"
    else:
        item_key = f"{product_code}_{color}"
    
    print(f"✅ [DIAGNOSTIC] item_key={item_key}")
    
    if item_key in context.user_data[cart_key]:
        context.user_data[cart_key][item_key]["quantity"] += 1
        print(f"✅ [DIAGNOSTIC] увеличено количество для {item_key}")
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
        print(f"✅ [DIAGNOSTIC] новый товар: {item_key}")

    # Очищаем временные данные
    context.user_data.pop(f"cart_size_{user_id}", None)
    for key in attrs.keys():
        if key not in ["colors", "sizes"]:
            context.user_data.pop(f"cart_attr_{key}_{user_id}", None)

    # Формируем текст
    attrs_text = f"\n🎨 Цвет: {color}"
    if size:
        attrs_text += f"\n📏 Размер: {size}"
    for key, value in selected_attrs.items():
        attrs_text += f"\n📌 {key.capitalize()}: {value}"

    text = f"✅ *{product.name} добавлен в корзину!*{attrs_text}"
    
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart")],
            [InlineKeyboardButton("🔙 Продолжить покупки", callback_data="main_back")]
        ])
    )
    logger.info("✅ Товар добавлен в корзину")

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, from_product_card: bool = False):
    """Показывает корзину с группировкой по товару + цвету."""
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

    # ============================================================
    # ГРУППИРОВКА ПО ТОВАРУ + ЦВЕТУ
    # ============================================================
    grouped_cart = {}
    
    print(f"🔍 [DIAGNOSTIC] view_cart: группировка...")
    
    for item_key, item in cart.items():
        product_code = item["product_code"]
        product = products_manager.get_by_code(product_code)
        if not product:
            continue
        
        color = item.get("color", "белый")
        size = item.get("size")
        quantity = item.get("quantity", 1)
        price = item.get("price", product.price)
        
        print(f"  📦 {item_key}: color={color}, size={size}, qty={quantity}")
        
        # Ключ группировки: product_code + color (без размера!)
        group_key = f"{product_code}_{color}"
        
        if group_key not in grouped_cart:
            photo_for_color = ""
            photos = product.photos if hasattr(product, 'photos') else {}
            if isinstance(photos, dict) and color in photos:
                photo_for_color = photos[color]
            
            grouped_cart[group_key] = {
                "product": product,
                "color": color,
                "sizes": {},
                "total_quantity": 0,
                "total_price": 0,
                "item_keys": [],
                "photo": photo_for_color
            }
        
        # Добавляем размер
        size_key = str(size) if size else "без_размера"
        grouped_cart[group_key]["sizes"][size_key] = grouped_cart[group_key]["sizes"].get(size_key, 0) + quantity
        grouped_cart[group_key]["item_keys"].append(item_key)
        grouped_cart[group_key]["total_quantity"] += quantity
        grouped_cart[group_key]["total_price"] += price * quantity

    # ============================================================
    # ОТОБРАЖЕНИЕ
    # ============================================================
    total_all = 0
    
    for group_key, group_data in grouped_cart.items():
        product = group_data["product"]
        color = group_data["color"]
        sizes = group_data["sizes"]
        total_quantity = group_data["total_quantity"]
        total_price = group_data["total_price"]
        photo = group_data.get("photo", "")
        
        total_all += total_price
        
        text = f"👟 *{product.name}*\n"
        text += f"💰 Цена: {product.price} руб/шт\n\n"
        text += f"🎨 *Цвет: {color}*\n"
        
        if sizes and not (len(sizes) == 1 and "без_размера" in sizes):
            text += "📏 *Размеры:*\n"
            for size_key, qty in sizes.items():
                size_display = size_key if size_key != "без_размера" else "Без размера"
                text += f"  • {size_display} — {qty} шт\n"
        
        text += f"\n📦 Итого: {total_quantity} шт\n"
        text += f"💰 {total_price} руб"
        
        keyboard = [
            [InlineKeyboardButton("➖", callback_data=f"cart_decr_color_{group_key}"),
             InlineKeyboardButton(f"{total_quantity} шт", callback_data="noop"),
             InlineKeyboardButton("➕", callback_data=f"cart_incr_color_{group_key}")],
            [InlineKeyboardButton("❌ Удалить цвет", callback_data=f"cart_remove_color_{group_key}")],
            [InlineKeyboardButton("🔗 К товару", callback_data=f"goto_product_{product.id}")]
        ]
        
        photo_to_send = ""
        if photo and os.path.exists(photo):
            photo_to_send = photo
        elif product.photo and os.path.exists(product.photo):
            photo_to_send = product.photo
        
        try:
            if photo_to_send:
                with open(photo_to_send, 'rb') as f:
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
        text=f"💰 *ОБЩИЙ ИТОГ: {total_all} руб*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ОФОРМИТЬ ЗАКАЗ", callback_data="checkout")],
            [InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_cart")],
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

async def cart_increase_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Увеличивает количество у всех позиций в группе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_incr_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    # Находим все позиции в группе
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            cart[item_key]["quantity"] += 1
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def cart_decrease_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Уменьшает количество у всех позиций в группе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_decr_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    # Находим все позиции в группе
    items_to_remove = []
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            if item["quantity"] > 1:
                cart[item_key]["quantity"] -= 1
            else:
                items_to_remove.append(item_key)
    
    # Удаляем позиции с нулевым количеством
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def cart_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все позиции в группе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_remove_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    # Находим все позиции в группе и удаляем
    items_to_remove = []
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            items_to_remove.append(item_key)
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полностью очищает корзину"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    context.user_data.pop(f"cart_{user_id}", None)
    save_user_data_sync(user_id, {f"cart_{user_id}": {}}, context)
    
    await view_cart(update, context)


async def cart_incr_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Увеличивает количество у всех позиций в группе (по цвету)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_incr_color_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            cart[item_key]["quantity"] += 1
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def cart_decr_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Уменьшает количество у всех позиций в группе (по цвету)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_decr_color_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    items_to_remove = []
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            if item["quantity"] > 1:
                cart[item_key]["quantity"] -= 1
            else:
                items_to_remove.append(item_key)
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def cart_remove_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все позиции выбранного цвета"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_remove_color_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    items_to_remove = []
    for item_key, item in cart.items():
        product_code = item.get("product_code", "")
        color = item.get("color", "белый")
        current_group_key = f"{product_code}_{color}"
        
        if current_group_key == group_key:
            items_to_remove.append(item_key)
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полностью очищает корзину"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    context.user_data.pop(f"cart_{user_id}", None)
    save_user_data_sync(user_id, {f"cart_{user_id}": {}}, context)
    
    await view_cart(update, context)