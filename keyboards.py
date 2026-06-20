from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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

    # ✅ ЕСЛИ НЕТ ГЛАВНОГО АТРИБУТА — НЕ ПОКАЗЫВАЕМ НИЧЕГО (даже цвета)
    # Цвета и другие атрибуты будут при заказе

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