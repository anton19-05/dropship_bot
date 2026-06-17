import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import products_manager
from keyboards import get_product_keyboard

async def show_product(chat_id, prod_id, color_id, context, bot, category=None, page=0):
    product = products_manager.get_by_id(prod_id)
    if not product:
        return
    
    if category is None:
        category = product.category
    
    user_id = None
    if context and hasattr(context, 'user_data'):
        # Получаем user_id из context
        pass
    
    text = product.get_text(color_id)
    photo = product.get_photo(color_id)
    
    try:
        if os.path.exists(photo):
            with open(photo, 'rb') as f:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_product_keyboard(product, color_id, category, page, context, None)
                )
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_product_keyboard(product, color_id, category, page, context, None)
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
            reply_markup=get_product_keyboard(product, color_id, category, page, context, None)
        )
        if "last_product_msg" in context.user_data:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=context.user_data["last_product_msg"])
            except:
                pass
        context.user_data["last_product_msg"] = msg.message_id