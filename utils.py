import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import products_manager
from keyboards import get_product_keyboard
from config import ADMIN_ID

async def show_product(chat_id, prod_id, color_id, context, bot, category=None, page=0, user_id=None, main_value=None):
    product = products_manager.get_by_id(prod_id)
    
    if not product:
        return
    
    # ============================================================
    # ✅ АВТОВЫБОР ТОЛЬКО ЕСЛИ НЕТ ЦВЕТА
    # ============================================================
    if user_id and context:
        existing_color = context.user_data.get(f"color_{user_id}")
        
        if not existing_color:
            colors = product.get_colors()
            default_color = colors[0] if colors else "белый"
            context.user_data[f"color_{user_id}"] = default_color
            print(f"✅ [show_product] color_{user_id} установлен: {default_color}")
        else:
            print(f"✅ [show_product] color_{user_id} уже существует: {existing_color}")
    
    # Получаем текст
    text = product.get_text()
    
    # Добавляем выбранные атрибуты в текст
    if user_id and context:
        main_attrs = product.get_main_attributes()
        selected_attrs = []
        for attr_key in main_attrs.keys():
            value = context.user_data.get(f"attr_{attr_key}_{user_id}")
            if value:
                display_name = attr_key.capitalize()
                selected_attrs.append(f"📌 {display_name}: {value}")
        
        # ✅ ПОКАЗЫВАЕМ ТЕКУЩИЙ ЦВЕТ
        current_color = context.user_data.get(f"color_{user_id}", "белый")
        if selected_attrs:
            text += f"\n\n--- *ВЫБРАНО:* ---"
            text += "\n" + "\n".join(selected_attrs)
    
    photo = product.get_photo()
    
    try:
        if os.path.exists(photo):
            with open(photo, 'rb') as f:
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