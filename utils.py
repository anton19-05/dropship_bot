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
    # Автоматически выбираем первый вариант главного атрибута,
    # если ничего не выбрано
    # ============================================================
    if user_id and context:
        main_attrs = product.get_main_attributes()
        for attr_key in main_attrs.keys():
            # Проверяем, есть ли уже выбранное значение
            existing = context.user_data.get(f"attr_{attr_key}_{user_id}")
            if not existing:
                # Если нет — выбираем первый вариант
                attr_value = main_attrs[attr_key]
                variants = attr_value.get('variants', {})
                if isinstance(variants, dict):
                    first_variant = list(variants.keys())[0] if variants else None
                elif isinstance(variants, list):
                    first_variant = variants[0] if variants else None
                else:
                    first_variant = None
                
                if first_variant:
                    context.user_data[f"attr_{attr_key}_{user_id}"] = first_variant
                    print(f"✅ Автовыбор: {attr_key} = {first_variant}")
    
    # Получаем основной текст карточки (без лишнего текста)
    text = product.get_text()
    
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