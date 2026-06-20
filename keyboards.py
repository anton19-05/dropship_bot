from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_ID

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="menu_catalog")],
        [InlineKeyboardButton("🔍 Поиск по коду", callback_data="menu_search")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ Как заказать", callback_data="menu_help")],
        [InlineKeyboardButton("📞 Контакты", callback_data="menu_contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_categories_keyboard():
    from models_categories import categories_manager
    keyboard = []
    for cat in categories_manager.get_all():
        keyboard.append([InlineKeyboardButton(
            cat["name"],
            callback_data=f"category_{cat['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_back")])
    return InlineKeyboardMarkup(keyboard)

def get_subcategories_keyboard(category_id):
    from models_categories import categories_manager
    subcategories = categories_manager.get_subcategories(category_id)
    if not subcategories:
        return None
    keyboard = []
    for subcat in subcategories:
        keyboard.append([InlineKeyboardButton(
            subcat["name"],
            callback_data=f"subcat_{subcat['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_back")])
    return InlineKeyboardMarkup(keyboard)

def get_product_keyboard(product, current_color=None, category=None, page=0, context=None, user_id=None):
    # ✅ ДИАГНОСТИКА (отправка админу)
    attrs = product.get_attributes()
    if context and user_id:
        import asyncio
        asyncio.create_task(
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⌨️ get_product_keyboard: {product.name}\nattrs={attrs}\nuser_id={user_id}\nmain_attrs={[k for k, v in attrs.items() if isinstance(v, dict) and v.get('type') == 'main']}"
            )
        )
    # ... остальной код
    keyboard = []

    # ✅ ПОКАЗЫВАЕМ ТОЛЬКО ГЛАВНЫЙ АТРИБУТ (type: main)
    attrs = product.get_attributes()
    has_main = False
    
    for key, value in attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, dict) and value.get("type") == "main":
            has_main = True
            variants = value.get("variants", {})
            if variants:
                row = []
                current_value = context.user_data.get(f"attr_{key}_{user_id}") if context and user_id else None
                for variant_key in variants.keys():
                    marker = "✅ " if current_value == variant_key else ""
                    row.append(InlineKeyboardButton(
                        f"{marker}{variant_key}",
                        callback_data=f"attr_{product.id}_{key}_{variant_key}"
                    ))
                if row:
                    keyboard.append(row)
            else:
                keyboard.append([InlineKeyboardButton(
                    f"📌 {key}",
                    callback_data=f"attr_{product.id}_{key}_default"
                )])

    # Если нет главного атрибута — показываем цвета (для обратной совместимости)
    if not has_main and "colors" in attrs:
        colors = attrs["colors"]
        if isinstance(colors, dict) and colors.get("type") == "main":
            pass  # уже обработали
        elif isinstance(colors, list):
            colors_row = []
            for color in colors:
                marker = "✅ " if color == current_color else ""
                colors_row.append(InlineKeyboardButton(
                    f"{marker}{color}",
                    callback_data=f"color_{product.id}_{color}"
                ))
            keyboard.append(colors_row)

    # Остальные кнопки
    keyboard.extend([
        [InlineKeyboardButton("⭐ Отзывы", callback_data=f"reviews_{product.id}")],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}"),
         InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_add_{product.code}")],
        [InlineKeyboardButton("🛍️ Корзина", callback_data="view_cart_from_product"),
         InlineKeyboardButton("⭐ Избранное", callback_data="view_favorites")],
        [InlineKeyboardButton("✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_category_{category}_{page}")]
    ])

    return InlineKeyboardMarkup(keyboard)