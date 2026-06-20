import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import products_manager
from keyboards import get_product_keyboard
from config import ADMIN_ID

async def show_product(chat_id, prod_id, color_id, context, bot, category=None, page=0, user_id=None, main_value=None):
    product = products_manager.get_by_id(prod_id)
    
    # ✅ ДИАГНОСТИКА
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🖼️ show_product: {product.name if product else 'None'}\ncolor_id={color_id}\nmain_value={main_value}\nattributes={product.attributes if product else 'None'}"
    )
    
    if not product:
        return
    
    if category is None:
        category = product.category
    
    # Если main_value не передан, пытаемся получить из context
    if not main_value and user_id:
        attrs = product.get_attributes()
        for key, value in attrs.items():
            if isinstance(value, dict) and value.get("type") == "main":
                main_value = context.user_data.get(f"attr_{key}_{user_id}")
                break
    
    text = product.get_text(color_id, main_value)
    photo = product.get_photo(color_id, main_value)
    
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