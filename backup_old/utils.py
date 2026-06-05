# utils.py - Вспомогательные функции

import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from products_config import COLORS, PRODUCTS


async def show_product(chat_id, prod_id, color_id, context, bot):
    """Показывает карточку товара"""
    product = PRODUCTS.get(prod_id)
    if not product:
        return

    color_data = product["colors"].get(color_id, {})
    code = product.get("code", "")

    text = f"""
👟 *{product['name']}* 👟

⭐ {product.get('rating', '4.5')} ★★★★★ | 📦 {product.get('orders', 0)} заказов
🔖 *Код товара:* `{code}`

💰 Цена: ~~{product.get('old_price', product['price'])} руб~~ → *{product['price']} руб*

📋 *Характеристики:*
{product.get('description', '✅ Качественный товар\n✅ Оригинал\n✅ Быстрая доставка')}

🚚 *Доставка:* 15-25 дней
✅ *Гарантия:* 14 дней
    """

    # Кнопки выбора цвета
    color_buttons = []
    for cid, cinfo in product["colors"].items():
        marker = "✅ " if cid == color_id else ""
        color_buttons.append(InlineKeyboardButton(
            f"{marker}{cinfo['name']}",
            callback_data=f"product_change_color_{prod_id}_{cid}"
        ))

    color_rows = [color_buttons[i:i+3]
                  for i in range(0, len(color_buttons), 3)]

    # Основные кнопки
    keyboard = color_rows + [
        [InlineKeyboardButton(
            "⭐ Отзывы", callback_data=f"product_reviews_{prod_id}_{color_id}")],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"add_cart_{code}"),
         InlineKeyboardButton("❤️ В избранное", callback_data=f"add_fav_{code}")],
        [InlineKeyboardButton("🛍️ Перейти в корзину", callback_data="goto_cart"),
         InlineKeyboardButton("⭐ Перейти в избранное", callback_data="goto_favorites")],
        [InlineKeyboardButton("✅ Заказать", callback_data="order_start")],
        [InlineKeyboardButton(
            "🔙 Назад", callback_data="back_to_subcategory_menu")]
    ]

    photo_path = color_data.get("photo", "static/1.jpg")

    # Удаляем предыдущую карточку товара
    if "last_product_msg" in context.user_data:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=context.user_data["last_product_msg"])
        except:
            pass
        context.user_data.pop("last_product_msg", None)

    # Отправляем карточку
    if os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data["last_product_msg"] = msg.message_id
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["last_product_msg"] = msg.message_id


def get_product_by_code(code):
    """Найти товар по коду"""
    for prod_id, product in PRODUCTS.items():
        if product.get("code", "") == code:
            return product, prod_id
    return None, None
