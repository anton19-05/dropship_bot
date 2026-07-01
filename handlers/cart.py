import os
import logging
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import products_manager, msg_manager
from storage import save_user_data_sync
from config import ADMIN_ID
from cart_utils import (
    get_cart_display_mode,
    should_show_separate_cards,
    format_variant_label,
    get_photo_for_variant
)

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
    
    print(f"🔍 show_cart_attributes: user_id={user_id}, product_code={product_code}")
    
    product = products_manager.get_by_code(product_code)
    
    if not product:
        logger.error(f"❌ Товар не найден! product_code={product_code}")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    # ✅ БЕРЕМ ЦВЕТ ИЗ РЕАЛЬНОГО МЕСТА ХРАНЕНИЯ
    color = context.user_data.get(f"attr_цвет_{user_id}")
    if not color:
        color = context.user_data.get(f"attr_colors_{user_id}")
    if not color:
        color = context.user_data.get(f"color_{user_id}")
    if not color:
        color = "белый"
    
    print(f"✅ show_cart_attributes: color={color}")
    
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
    
    # ============================================================
    # ✅ СОБИРАЕМ ВСЕ ГЛАВНЫЕ АТРИБУТЫ
    # ============================================================
    main_attrs = product.get_main_attributes()
    selected_main_attrs = {}
    
    for attr_key in main_attrs.keys():
        attr_value = context.user_data.get(f"attr_{attr_key}_{user_id}")
        if attr_value:
            selected_main_attrs[attr_key] = attr_value
            print(f"✅ Главный атрибут {attr_key} = {attr_value}")
    
    # Если не нашли ни одного главного атрибута — используем цвет
    if not selected_main_attrs:
        color = context.user_data.get(f"color_{user_id}", "белый")
        selected_main_attrs["цвет"] = color
        print(f"✅ Используем цвет по умолчанию: {color}")
    
    # ✅ Убеждаемся, что цвет сохранен в item
    color_value = None
    for key, value in selected_main_attrs.items():
        if key in ["colors", "цвет", "color"]:
            color_value = value
            break
    
    if not color_value:
        color_value = context.user_data.get(f"color_{user_id}", "белый")
    
    print(f"📋 Цвет для корзины: {color_value}")
    
    # ============================================================
    # ✅ СОБИРАЕМ ВСЕ ОБЫЧНЫЕ АТРИБУТЫ (не главные)
    # ============================================================
    extra_attrs = product.get_extra_attributes()
    selected_extra_attrs = {}
    for key in extra_attrs.keys():
        if key in ["colors", "sizes"]:
            continue
        # Сначала пробуем из cart_attr_ (выбор в корзине)
        attr_value = context.user_data.get(f"cart_attr_{key}_{user_id}")
        if not attr_value:
            # Потом из attr_ (выбор в карточке)
            attr_value = context.user_data.get(f"attr_{key}_{user_id}")
        if attr_value:
            selected_extra_attrs[key] = attr_value
            print(f"✅ Обычный атрибут {key} = {attr_value}")
    
    # ============================================================
    # ✅ ПОЛУЧАЕМ РАЗМЕР (если есть)
    # ============================================================
    size = context.user_data.get(f"cart_size_{user_id}")
    if not size:
        size = context.user_data.get(f"attr_size_{user_id}")
    if not size:
        for key, value in selected_main_attrs.items():
            if key in ["size", "размер"]:
                size = value
                break
        if not size:
            for key, value in selected_extra_attrs.items():
                if key in ["size", "размер"]:
                    size = value
                    break
    
    print(f"✅ Размер для корзины: {size}")
    
    # ============================================================
    # ✅ ДОБАВЛЯЕМ В КОРЗИНУ
    # ============================================================
    cart_key = f"cart_{user_id}"
    if cart_key not in context.user_data:
        context.user_data[cart_key] = {}

    # Формируем ключ
    main_attrs_str = "_".join([f"{k}_{v}" for k, v in selected_main_attrs.items()])
    extra_attrs_str = "_".join([f"{k}_{v}" for k, v in selected_extra_attrs.items()])
    size_str = f"_size_{size}" if size else ""
    
    if main_attrs_str and extra_attrs_str:
        full_key = f"{product_code}_{main_attrs_str}_{extra_attrs_str}{size_str}"
    elif main_attrs_str:
        full_key = f"{product_code}_{main_attrs_str}{size_str}"
    elif extra_attrs_str:
        full_key = f"{product_code}_{extra_attrs_str}{size_str}"
    else:
        full_key = f"{product_code}{size_str}"
    
    print(f"✅ full_key={full_key}")
    
    if full_key in context.user_data[cart_key]:
        context.user_data[cart_key][full_key]["quantity"] += 1
        print(f"✅ увеличено количество для {full_key}")
    else:
        item_data = {
            "product_code": product_code,
            "quantity": 1,
            "name": product.name,
            "price": product.price,
            **selected_main_attrs,
            **selected_extra_attrs
        }
        if size:
            item_data["size"] = size
        
        context.user_data[cart_key][full_key] = item_data
        print(f"✅ новый товар: {full_key}")
        print(f"📋 item_data: {item_data}")

    # ============================================================
    # ✅ ОЧИЩАЕМ ВСЕ ВРЕМЕННЫЕ ДАННЫЕ
    # ============================================================
    # Очищаем размер
    context.user_data.pop(f"cart_size_{user_id}", None)
    
    # Очищаем атрибуты корзины
    for key in extra_attrs.keys():
        if key not in ["colors", "sizes"]:
            context.user_data.pop(f"cart_attr_{key}_{user_id}", None)
    
    # ✅ ОЧИЩАЕМ ВСЕ ВРЕМЕННЫЕ АТРИБУТЫ ИЗ КАРТОЧКИ
    keys_to_remove = []
    all_product_attrs = list(main_attrs.keys()) + list(extra_attrs.keys())
    for key in list(context.user_data.keys()):
        if key.startswith(f"attr_") and key.endswith(f"_{user_id}"):
            attr_key = key.replace(f"attr_", "").replace(f"_{user_id}", "")
            if attr_key in all_product_attrs:
                keys_to_remove.append(key)
                print(f"✅ Очищен атрибут: {key}")
    
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    # Очищаем цвет
    if "color" in all_product_attrs or "цвет" in all_product_attrs:
        context.user_data.pop(f"color_{user_id}", None)
        print(f"✅ Очищен цвет: color_{user_id}")
    
    print(f"📋 Очищено {len(keys_to_remove)} временных атрибутов")

    # ============================================================
    # ✅ ФОРМИРУЕМ ТЕКСТ (БЕЗ ДУБЛИРОВАНИЯ)
    # ============================================================
    # Объединяем атрибуты и убираем дубли
    all_attrs = {}
    for key, value in selected_main_attrs.items():
        normalized_key = key
        if key in ["size", "размер"]:
            normalized_key = "размер"
        elif key in ["color", "цвет"]:
            normalized_key = "цвет"
        all_attrs[normalized_key] = value
    
    for key, value in selected_extra_attrs.items():
        normalized_key = key
        if key in ["size", "размер"]:
            normalized_key = "размер"
        elif key in ["color", "цвет"]:
            normalized_key = "цвет"
        all_attrs[normalized_key] = value

    attrs_text = ""
    for key, value in all_attrs.items():
        attrs_text += f"\n🔥 {key.capitalize()}: {value}"

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
    # ШАГ 1: ГРУППИРУЕМ ПО ТОВАРУ + ОПРЕДЕЛЯЕМ ГЛАВНЫЙ АТРИБУТ
    # ============================================================
    temp_cart = {}

    for item_key, item in cart.items():
        product_code = item["product_code"]
        product = products_manager.get_by_code(product_code)
        if not product:
            continue

        if product_code not in temp_cart:
            temp_cart[product_code] = {
                "product": product,
                "items": [],
                "main_attr_key": None,
                "main_attr_value": None,
                "has_photos": False,
                "photo": ""
            }

        temp_cart[product_code]["items"].append({"item_key": item_key, "item": item})

        # ✅ ОПРЕДЕЛЯЕМ ГЛАВНЫЙ АТРИБУТ
        if not temp_cart[product_code]["main_attr_key"]:
            main_attrs = product.get_main_attributes()
            photos = getattr(product, 'photos', {})
            
            # Сначала ищем атрибут с фото
            for attr_key in main_attrs.keys():
                attr_value = item.get(attr_key)
                if attr_value and attr_value in photos and photos[attr_value] and os.path.exists(photos[attr_value]):
                    temp_cart[product_code]["main_attr_key"] = attr_key
                    temp_cart[product_code]["main_attr_value"] = attr_value
                    temp_cart[product_code]["has_photos"] = True
                    temp_cart[product_code]["photo"] = photos[attr_value]
                    break
            
            # Если фото нет — берём ПЕРВЫЙ главный атрибут (как в карточке)
            if not temp_cart[product_code]["main_attr_key"] and main_attrs:
                first_attr_key = list(main_attrs.keys())[0]
                first_attr_value = item.get(first_attr_key)
                if first_attr_value:
                    temp_cart[product_code]["main_attr_key"] = first_attr_key
                    temp_cart[product_code]["main_attr_value"] = first_attr_value
                    temp_cart[product_code]["has_photos"] = False
                    temp_cart[product_code]["photo"] = ""

    # ============================================================
    # ШАГ 2: ГРУППИРОВКА (С УЧЁТОМ КОЛИЧЕСТВА АТРИБУТОВ)
    # ============================================================
    grouped_cart = {}

    for product_code, group in temp_cart.items():
        product = group["product"]
        has_photos = group["has_photos"]
        main_attr_key = group["main_attr_key"]
        photo = group["photo"]

        # ✅ ПРОВЕРЯЕМ, СКОЛЬКО ВСЕГО АТРИБУТОВ У ТОВАРА
        all_attrs = dict(product.get_main_attributes())
        all_attrs.update(product.get_extra_attributes())
        total_attr_count = len(all_attrs)

        for entry in group["items"]:
            item = entry["item"]
            item_key = entry["item_key"]

            # ✅ ОПРЕДЕЛЯЕМ ЗНАЧЕНИЕ ГЛАВНОГО АТРИБУТА
            main_value = None
            if main_attr_key:
                main_value = item.get(main_attr_key)
                if not main_value and main_attr_key == "цвет":
                    main_value = item.get("color")
                elif not main_value and main_attr_key == "color":
                    main_value = item.get("цвет")

            # ✅ ЕСЛИ ВСЕГО 1 АТРИБУТ — НЕ ГРУППИРУЕМ ПО ЗНАЧЕНИЯМ
            if total_attr_count <= 1:
                group_key = f"{product_code}_single_attr"
            elif main_attr_key and main_value:
                group_key = f"{product_code}_{main_attr_key}_{main_value}"
            else:
                group_key = f"{product_code}_grouped"

            if group_key not in grouped_cart:
                grouped_cart[group_key] = {
                    "product": product,
                    "variants": {},
                    "total_quantity": 0,
                    "total_price": 0,
                    "main_attr_key": main_attr_key,
                    "main_attr_value": main_value,
                    "has_photos": has_photos,
                    "photo": photo if has_photos and photo and os.path.exists(photo) else "",
                }
            else:
                # ✅ ОБНОВЛЯЕМ PHOTO В СУЩЕСТВУЮЩЕЙ ГРУППЕ
                if has_photos and main_attr_key and main_value:
                    photos = getattr(product, 'photos', {})
                    if main_value in photos and photos[main_value] and os.path.exists(photos[main_value]):
                        grouped_cart[group_key]["photo"] = photos[main_value]
                        print(f"🔄 Обновлено фото для {group_key}: {photos[main_value]}")

            # ============================================================
            # ФОРМИРУЕМ КЛЮЧ ВАРИАНТА (ВСЕ АТРИБУТЫ КРОМЕ ГЛАВНОГО)
            # ============================================================
            variant_parts = []
            for key, value in item.items():
                if key in ["product_code", "quantity", "name", "price", "item_key"]:
                    continue
                if main_attr_key:
                    if key == main_attr_key:
                        continue
                    if main_attr_key == "размер" and key == "size":
                        continue
                    if main_attr_key == "size" and key == "размер":
                        continue
                    if main_attr_key == "цвет" and key == "color":
                        continue
                    if main_attr_key == "color" and key == "цвет":
                        continue
                if value:
                    variant_parts.append(f"{key}_{value}")

            variant_key = "_".join(sorted(variant_parts)) if variant_parts else "standard"

            # ✅ ДЛЯ 1 АТРИБУТА — НЕ СЛИВАЕМ ОДИНАКОВЫЕ variant_key
            if total_attr_count <= 1:
                unique_key = f"single_{item_key}"
                if unique_key not in grouped_cart[group_key]["variants"]:
                    grouped_cart[group_key]["variants"][unique_key] = {
                        "label": format_variant_label(product, item),
                        "quantity": 0,
                        "item_keys": [],
                        "item": item
                    }
                grouped_cart[group_key]["variants"][unique_key]["quantity"] += item.get("quantity", 1)
                grouped_cart[group_key]["variants"][unique_key]["item_keys"].append(item_key)
            else:
                if variant_key not in grouped_cart[group_key]["variants"]:
                    grouped_cart[group_key]["variants"][variant_key] = {
                        "label": format_variant_label(product, item),
                        "quantity": 0,
                        "item_keys": [],
                        "item": item
                    }
                grouped_cart[group_key]["variants"][variant_key]["quantity"] += item.get("quantity", 1)
                grouped_cart[group_key]["variants"][variant_key]["item_keys"].append(item_key)

            grouped_cart[group_key]["total_quantity"] += item.get("quantity", 1)
            grouped_cart[group_key]["total_price"] += item.get("price", product.price) * item.get("quantity", 1)

        # ============================================================
        # 🔥 ТОТАЛЬНАЯ ДИАГНОСТИКА (исправленная)
        # ============================================================
        print(f"\n{'='*50}")
        print(f"🔍 ТОВАР: {product.name}")
        print(f"🔍 main_attr_key: {group.get('main_attr_key')}")
        print(f"🔍 main_attr_value: {group.get('main_attr_value')}")
        print(f"🔍 has_photos: {group.get('has_photos')}")
        print(f"🔍 variants: {len(grouped_cart[group_key]['variants'])} вариантов")
        
        for idx, (v_key, v_data) in enumerate(grouped_cart[group_key]['variants'].items(), 1):
            print(f"\n  📌 Вариант {idx}:")
            print(f"     v_key: {v_key}")
            print(f"     label: {v_data['label']}")
            print(f"     quantity: {v_data['quantity']}")
            print(f"     item keys: {list(v_data['item'].keys())}")
            print(f"     item: {v_data['item']}")
        print(f"{'='*50}\n")

    # ============================================================
    # ШАГ 3: ОТОБРАЖЕНИЕ
    # ============================================================
    total_all = 0

    for group_key, group in grouped_cart.items():
        product = group["product"]
        variants = group["variants"]
        total_quantity = group["total_quantity"]
        total_price = group["total_price"]
        has_photos = group["has_photos"]
        photo = group["photo"]
        main_attr_key = group["main_attr_key"]
        main_attr_value = group["main_attr_value"]

        total_all += total_price

        # ============================================================
        # ОПРЕДЕЛЯЕМ РЕЖИМ ОТОБРАЖЕНИЯ
        # ============================================================
        # ✅ ОБЩЕЕ КОЛИЧЕСТВО АТРИБУТОВ (ГЛАВНЫЕ + ВТОРОСТЕПЕННЫЕ)
        total_attrs = len(product.get_main_attributes()) + len(product.get_extra_attributes())
        use_numbers = total_attrs >= 3
        
        print(f"🔍 [DIAGNOSTIC] total_attrs={total_attrs}, use_numbers={use_numbers}")

        # ============================================================
        # ФОРМИРОВАНИЕ ТЕКСТА
        # ============================================================
        variant_list = list(variants.items())
        
        # ✅ ЕСЛИ НЕТ ВАРИАНТОВ — ПРОПУСКАЕМ
        if not variant_list:
            print(f"⚠️ Нет вариантов для товара {product.name}, пропускаем")
            print(f"⚠️ variant_list пустой для {product.name}")
            print(f"📋 variants: {variants}")
            continue

        text = f"👟 *{product.name}*\n"
        text += f"💰 {product.price} руб/шт\n\n"

        if main_attr_key and main_attr_value:
            text += f"📌 {main_attr_key.capitalize()}: {main_attr_value}\n\n"

        # ============================================================
        # 3+ АТРИБУТОВ — НУМЕРОВАННЫЙ СПИСОК
        # ============================================================
        if use_numbers:
            for idx, (v_key, v_data) in enumerate(variant_list, 1):
                label = v_data['label']
                qty = v_data['quantity']

                if main_attr_key and main_attr_value:
                    main_pattern = f"{main_attr_key.capitalize()}: {main_attr_value}"
                    label = label.replace(main_pattern, "").strip(" | ")

                if not label:
                    text += f"  {idx}. {qty} шт\n"
                else:
                    text += f"  {idx}. {label} — {qty} шт\n"

            text += f"\n📦 Кол-во: {total_quantity} шт | 💰 {total_price} руб"

            # ✅ КНОПКИ С ИНДЕКСАМИ (СОХРАНЯЕМ МАППИНГ)
            keyboard = []
            key_map = {}
            for idx, (v_key, v_data) in enumerate(variant_list, 1):
                first_item_key = v_data["item_keys"][0]
                key_map[str(idx)] = first_item_key
                keyboard.append([
                    InlineKeyboardButton("➖", callback_data=f"cart_decr_{idx}"),
                    InlineKeyboardButton(str(idx), callback_data="noop"),
                    InlineKeyboardButton("➕", callback_data=f"cart_incr_{idx}")
                ])
            
            # ✅ КНОПКА УДАЛЕНИЯ
            first_item_key = list(variants.values())[0]["item_keys"][0] if variants else None
            if first_item_key:
                key_map["delete"] = first_item_key
                keyboard.append([InlineKeyboardButton("❌ Удалить", callback_data=f"cart_remove_delete")])
            keyboard.append([InlineKeyboardButton("🔗 К товару", callback_data=f"goto_product_{product.id}")])
            
            # ✅ СОХРАНЯЕМ МАППИНГ
            context.user_data[f"cart_key_map_{user_id}"] = key_map

        # ============================================================
        # 1-2 АТРИБУТА — ПОЛНЫЙ ТЕКСТ
        # ============================================================
        else:
            display_variants = []

            for v_key, v_data in variant_list:
                qty = v_data['quantity']
                item = v_data['item']

                clean_parts = []
                used_keys = set()

                for key, value in item.items():
                    if key in ["product_code", "quantity", "name", "price", "item_key"]:
                        continue
                    if main_attr_key:
                        if key == main_attr_key:
                            continue
                        if main_attr_key == "размер" and key == "size":
                            continue
                        if main_attr_key == "size" and key == "размер":
                            continue
                        if main_attr_key == "цвет" and key == "color":
                            continue
                        if main_attr_key == "color" and key == "цвет":
                            continue
                    if value:
                        normalized_key = key
                        if key in ["size", "размер"]:
                            normalized_key = "размер"
                        elif key in ["color", "цвет"]:
                            normalized_key = "цвет"

                        if normalized_key in used_keys:
                            continue
                        used_keys.add(normalized_key)

                        display_name = normalized_key.capitalize()
                        if normalized_key == "цвет":
                            display_name = "Цвет"
                        elif normalized_key == "размер":
                            display_name = "Размер"

                        clean_parts.append(f"{display_name}: {value}")

                clean_label = " | ".join(clean_parts) if clean_parts else ""

                if not clean_label:
                    for key, value in item.items():
                        if key in ["product_code", "quantity", "name", "price", "item_key"]:
                            continue
                        if value:
                            normalized_key = key
                            if key in ["size", "размер"]:
                                normalized_key = "размер"
                            elif key in ["color", "цвет"]:
                                normalized_key = "цвет"
                            display_name = normalized_key.capitalize()
                            if normalized_key == "цвет":
                                display_name = "Цвет"
                            elif normalized_key == "размер":
                                display_name = "Размер"
                            clean_label = f"{display_name}: {value}"
                            break

                display_variants.append({
                    "clean_label": clean_label,
                    "qty": qty,
                    "first_item_key": v_data["item_keys"][0],
                    "v_data": v_data
                })

            # ТЕКСТ
            for item in display_variants:
                if not item["clean_label"]:
                    text += f"  {item['qty']} шт\n"
                else:
                    text += f"  {item['clean_label']} — {item['qty']} шт\n"

            text += f"\n📦 Кол-во: {total_quantity} шт | 💰 {total_price} руб"

            # ✅ КНОПКИ С ИНДЕКСАМИ (СОХРАНЯЕМ МАППИНГ)
            keyboard = []
            key_map = {}
            for idx, item in enumerate(display_variants, 1):
                first_item_key = item["first_item_key"]
                key_map[str(idx)] = first_item_key

                clean_label = item["clean_label"]

                # Извлекаем значения для кнопки
                parts = []
                if clean_label:
                    for part in clean_label.split(" | "):
                        if ": " in part:
                            parts.append(part.split(": ")[-1])
                        else:
                            parts.append(part)

                # Если parts пустой — берём значение из item
                if not parts:
                    used_values = set()
                    for key, value in item["v_data"]["item"].items():
                        if key in ["product_code", "quantity", "name", "price", "item_key"]:
                            continue
                        if value:
                            if main_attr_key and key == main_attr_key:
                                continue
                            if main_attr_key == "размер" and key == "size":
                                continue
                            if main_attr_key == "size" and key == "размер":
                                continue
                            if main_attr_key == "цвет" and key == "color":
                                continue
                            if main_attr_key == "color" and key == "цвет":
                                continue
                            normalized_key = key
                            if normalized_key in ["size", "размер"]:
                                normalized_key = "размер"
                            elif normalized_key in ["color", "цвет"]:
                                normalized_key = "цвет"
                            if normalized_key in used_values:
                                continue
                            used_values.add(normalized_key)
                            parts.append(str(value))
                            break

                # Убираем дубли в кнопке
                unique_parts = []
                for p in parts:
                    if p not in unique_parts:
                        unique_parts.append(p)

                button_text = ", ".join(unique_parts) if unique_parts else "Стандарт"

                keyboard.append([
                    InlineKeyboardButton("➖", callback_data=f"cart_decr_{idx}"),
                    InlineKeyboardButton(button_text, callback_data="noop"),
                    InlineKeyboardButton("➕", callback_data=f"cart_incr_{idx}")
                ])

            # ✅ КНОПКА УДАЛЕНИЯ (ИСПОЛЬЗУЕТ ФИКСИРОВАННЫЙ КЛЮЧ "delete")
            first_item_key = display_variants[0]["first_item_key"] if display_variants else None
            if first_item_key:
                key_map["delete"] = first_item_key
                keyboard.append([InlineKeyboardButton("❌ Удалить", callback_data="cart_remove_delete")])
            keyboard.append([InlineKeyboardButton("🔗 К товару", callback_data=f"goto_product_{product.id}")])

            # ✅ СОХРАНЯЕМ МАППИНГ В context.user_data
            context.user_data[f"cart_key_map_{user_id}"] = key_map

        # ============================================================
        # ✅ ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ФОТО ПЕРЕД ОТПРАВКОЙ
        # ============================================================
        if has_photos and variants:
            first_variant = list(variants.values())[0]
            photo = get_photo_for_variant(product, first_variant["item"])
            if photo:
                print(f"🔄 Обновлено фото для варианта: {photo}")

        # ============================================================
        # ОТПРАВКА
        # ============================================================
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
            print(f"Ошибка отправки: {e}")
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await msg_manager.add(context.bot, chat_id, user_id, msg)

    # Итого
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
    
    # Получаем индекс из callback_data
    idx = query.data.replace("cart_incr_", "")
    
    # Восстанавливаем item_key по индексу
    key_map = context.user_data.get(f"cart_key_map_{user_id}", {})
    item_key = key_map.get(str(idx))
    
    if item_key:
        cart = context.user_data.get(f"cart_{user_id}", {})
        if item_key in cart:
            cart[item_key]["quantity"] += 1
            save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
            print(f"✅ [DIAGNOSTIC] Увеличено: {item_key}")
        else:
            print(f"❌ [DIAGNOSTIC] Товар не найден: {item_key}")
    else:
        print(f"❌ [DIAGNOSTIC] Индекс не найден: {idx}")
    
    await view_cart(update, context)


async def cart_decrease(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Получаем индекс из callback_data
    idx = query.data.replace("cart_decr_", "")
    
    # Восстанавливаем item_key по индексу
    key_map = context.user_data.get(f"cart_key_map_{user_id}", {})
    item_key = key_map.get(str(idx))
    
    if item_key:
        cart = context.user_data.get(f"cart_{user_id}", {})
        if item_key in cart:
            if cart[item_key]["quantity"] > 1:
                cart[item_key]["quantity"] -= 1
            else:
                del cart[item_key]
            save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
            print(f"✅ [DIAGNOSTIC] Уменьшено: {item_key}")
        else:
            print(f"❌ [DIAGNOSTIC] Товар не найден: {item_key}")
    else:
        print(f"❌ [DIAGNOSTIC] Индекс не найден: {idx}")
    
    await view_cart(update, context)


async def cart_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Получаем ключ из callback_data (всегда "delete")
    key = query.data.replace("cart_remove_", "")
    
    # Восстанавливаем item_key по ключу "delete"
    key_map = context.user_data.get(f"cart_key_map_{user_id}", {})
    item_key = key_map.get(key)  # key = "delete"
    
    if item_key:
        cart = context.user_data.get(f"cart_{user_id}", {})
        if item_key in cart:
            del cart[item_key]
            save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
            print(f"✅ [DIAGNOSTIC] Удалено: {item_key}")
        else:
            print(f"❌ [DIAGNOSTIC] Товар не найден: {item_key}")
    else:
        print(f"❌ [DIAGNOSTIC] Ключ не найден: {key}")
    
    await view_cart(update, context)


async def view_cart_from_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_cart(update, context, from_product_card=False)


async def view_cart_from_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_cart(update, context, from_product_card=True)


async def cart_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все позиции в группе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_key = query.data.replace("cart_remove_group_", "")
    
    print(f"🔍 [DIAGNOSTIC] cart_remove_group: group_key={group_key}")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    print(f"📋 [DIAGNOSTIC] cart до удаления: {cart}")
    
    # ✅ ИЩЕМ ВСЕ ПОЗИЦИИ, КОТОРЫЕ ВХОДЯТ В ГРУППУ
    items_to_remove = []
    for item_key, item in cart.items():
        # Проверяем, принадлежит ли этот товар к группе
        # group_key формируется как: {product_code}_{main_attr_key}_{main_value}
        # или {product_code}_single_attr
        if item_key.startswith(group_key.split("_")[0]):  # Проверяем по product_code
            # Дополнительная проверка: если в group_key есть атрибут, проверяем и его
            parts = group_key.split("_")
            if len(parts) >= 3:
                # group_key = product_code_main_attr_key_main_value
                # Проверяем, что товар имеет этот атрибут
                attr_key = parts[1]
                attr_value = "_".join(parts[2:])
                if item.get(attr_key) == attr_value:
                    items_to_remove.append(item_key)
            else:
                # group_key = product_code_single_attr или product_code_grouped
                items_to_remove.append(item_key)
    
    print(f"🗑️ [DIAGNOSTIC] Удаляем позиции: {items_to_remove}")
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    print(f"📋 [DIAGNOSTIC] cart после удаления: {cart}")
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
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

async def cart_incr_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Увеличивает количество в группе"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    group_key = query.data.replace("cart_incr_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    for item_key in list(cart.keys()):
        if item_key.startswith(group_key.split("_")[0]):  # Проверяем по product_code
            cart[item_key]["quantity"] += 1
            break
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)

async def cart_decr_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Уменьшает количество в группе"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    group_key = query.data.replace("cart_decr_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    items_to_remove = []
    for item_key in list(cart.keys()):
        if item_key.startswith(group_key.split("_")[0]):
            if cart[item_key]["quantity"] > 1:
                cart[item_key]["quantity"] -= 1
            else:
                items_to_remove.append(item_key)
            break
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)

async def cart_remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет всю группу"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    group_key = query.data.replace("cart_remove_group_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    items_to_remove = []
    for item_key in list(cart.keys()):
        if item_key.startswith(group_key.split("_")[0]):
            items_to_remove.append(item_key)
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)

async def cart_change_variant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список вариантов для изменения количества (детальный режим)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_code = query.data.replace("cart_change_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    variants = []
    for item_key, item in cart.items():
        if item["product_code"] == product_code:
            product = products_manager.get_by_code(product_code)
            label = format_variant_label(product, item) if product else "Стандарт"
            variants.append({
                "item_key": item_key,
                "label": label,
                "quantity": item["quantity"]
            })
    
    if not variants:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    keyboard = []
    for variant in variants:
        keyboard.append([
            InlineKeyboardButton(
                f"{variant['label']} ({variant['quantity']} шт)",
                callback_data=f"cart_change_item_{variant['item_key']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="view_cart")])
    
    await query.edit_message_text(
        text=f"🔄 *Выберите вариант для изменения:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cart_remove_all_variants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все варианты товара (детальный режим)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_code = query.data.replace("cart_remove_all_", "")
    
    cart = context.user_data.get(f"cart_{user_id}", {})
    
    items_to_remove = []
    for item_key, item in cart.items():
        if item["product_code"] == product_code:
            items_to_remove.append(item_key)
    
    for key in items_to_remove:
        del cart[key]
    
    if not cart:
        context.user_data.pop(f"cart_{user_id}", None)
    
    save_user_data_sync(user_id, {f"cart_{user_id}": cart}, context)
    await view_cart(update, context)