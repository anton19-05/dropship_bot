import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import products_manager
from keyboards import get_product_keyboard
from config import ADMIN_ID

async def show_product(chat_id, prod_id, color_id, context, bot, category=None, page=0, user_id=None, main_value=None):
    product = products_manager.get_by_id(prod_id)
    
    if not product:
        return
    
    # ✅ ДИАГНОСТИКА
    print(f"🔍 show_product: product_id={prod_id}, color_id={color_id}, main_value={main_value}")
    print(f"📋 photos: {product.photos if hasattr(product, 'photos') else 'нет'}")
    print(f"📋 photo: {product.photo if hasattr(product, 'photo') else 'нет'}")
    
    # ============================================================
    # ✅ ПОЛУЧАЕМ ТЕКУЩИЙ ВЫБРАННЫЙ АТРИБУТ
    # ============================================================
    if user_id and context:
        # Проверяем, есть ли выбранный цвет
        selected_color = context.user_data.get(f"color_{user_id}")
        if not selected_color:
            selected_color = context.user_data.get(f"attr_цвет_{user_id}")
        if not selected_color:
            selected_color = context.user_data.get(f"attr_colors_{user_id}")
        
        # Если есть выбранный цвет — используем его для фото
        if selected_color:
            color_id = selected_color
            print(f"✅ Используем выбранный цвет: {color_id}")
        
        # Также проверяем другие главные атрибуты
        main_attrs = product.get_main_attributes()
        for attr_key in main_attrs.keys():
            if attr_key in ["colors", "цвет", "color"]:
                continue
            attr_value = context.user_data.get(f"attr_{attr_key}_{user_id}")
            if attr_value:
                # Проверяем, есть ли фото для этого атрибута
                photos = product.photos if hasattr(product, 'photos') else {}
                if isinstance(photos, dict) and attr_value in photos:
                    color_id = attr_value
                    print(f"✅ Используем атрибут {attr_key}={attr_value} для фото")
                    break
    
    # ============================================================
    # ✅ ПОЛУЧАЕМ ФОТО ДЛЯ ВЫБРАННОГО АТРИБУТА
    # ============================================================
    photo_path = ""
    photos = product.photos if hasattr(product, 'photos') else {}
    
    # Сначала пробуем найти фото по color_id
    if color_id and isinstance(photos, dict) and color_id in photos:
        photo_path = photos[color_id]
        print(f"✅ Найдено фото для {color_id}: {photo_path}")
    
    # Если не нашли — пробуем основное фото
    if not photo_path or not os.path.exists(photo_path):
        photo_path = product.photo if hasattr(product, 'photo') else ""
        print(f"✅ Используем основное фото: {photo_path}")
    
    # Если и основного нет — ищем любое фото из photos
    if (not photo_path or not os.path.exists(photo_path)) and isinstance(photos, dict):
        for color, path in photos.items():
            if path and os.path.exists(path):
                photo_path = path
                print(f"✅ Используем первое доступное фото: {photo_path}")
                break
    
    # ============================================================
    # ✅ ФОРМИРУЕМ ТЕКСТ (С ДИНАМИЧЕСКИМ ОПИСАНИЕМ)
    # ============================================================
    # Получаем динамическое описание из выбранных атрибутов
    description = product.get_description_for_attributes(user_id, context)
    
    # Формируем текст вручную, чтобы подставить правильное описание
    text = f"📦 *{product.name}*\n\n"
    
    # Рейтинг и заказы
    if product.rating:
        text += f"⭐ Рейтинг: {product.rating}\n"
    if product.orders:
        text += f"📦 Заказов: {product.orders}\n"
    text += "\n"
    
    # Цена
    text += f"💰 Цена: {product.price} руб.\n"
    if product.old_price and product.old_price > product.price:
        text += f"~~{product.old_price} руб.~~\n"
    text += "\n"
    
    # ✅ ДИНАМИЧЕСКОЕ ОПИСАНИЕ
    if description:
        text += f"📝 *Описание товара*\n{description}\n"
    else:
        # Если описания нет — показываем стандартное
        text += f"📝 *Описание товара*\n{product.description}\n"
    
    # Добавляем выбранные атрибуты в текст
    if user_id and context:
        main_attrs = product.get_main_attributes()
        selected_attrs = []
        for attr_key in main_attrs.keys():
            value = context.user_data.get(f"attr_{attr_key}_{user_id}")
            if value:
                display_name = attr_key.capitalize()
                selected_attrs.append(f"📌 {display_name}: {value}")
        
        if selected_attrs:
            text += "\n--- *ВЫБРАНО:* ---"
            text += "\n" + "\n".join(selected_attrs)
    
    # ============================================================
    # ✅ ОТПРАВЛЯЕМ СООБЩЕНИЕ
    # ============================================================
    try:
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_product_keyboard(product, color_id, category, page, context, user_id)
                )
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_product_keyboard(product, color_id, category, page, context, user_id)
            )
        
        if "last_product_msg" in context.user_data:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=context.user_data["last_product_msg"])
            except:
                pass
        context.user_data["last_product_msg"] = msg.message_id
        
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=get_product_keyboard(product, color_id, category, page, context, user_id)
        )
        if "last_product_msg" in context.user_data:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=context.user_data["last_product_msg"])
            except:
                pass
        context.user_data["last_product_msg"] = msg.message_id