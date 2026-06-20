from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="menu_catalog")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
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
    attrs = product.get_attributes()
    
    # Находим главный атрибут
    main_key = None
    main_variants = None
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            main_key = key
            main_variants = value.get("variants", {})
            break
    
    # Показываем кнопки главного атрибута
    if main_variants:
        row = []
        selected = context.user_data.get(f"attr_{main_key}_{user_id}") if context and user_id else None
        for variant in main_variants.keys():
            marker = "✅ " if selected == variant else ""
            row.append(InlineKeyboardButton(
                f"{marker}{variant}",
                callback_data=f"attr_{product.id}_{main_key}_{variant}"
            ))
        keyboard.append(row)
    
    # Показываем цвета (если они есть и НЕ главный атрибут)
    if "colors" in attrs and main_key != "colors":
        colors = attrs["colors"]
        if isinstance(colors, list):
            row = []
            for color in colors:
                marker = "✅ " if color == current_color else ""
                row.append(InlineKeyboardButton(
                    f"{marker}{color}",
                    callback_data=f"color_{product.id}_{color}"
                ))
            keyboard.append(row)
        elif isinstance(colors, dict) and colors.get("type") != "main":
            # Если colors это словарь но не main (например, с описанием)
            variants = colors.get("variants", {})
            if variants:
                row = []
                for color in variants.keys():
                    marker = "✅ " if color == current_color else ""
                    row.append(InlineKeyboardButton(
                        f"{marker}{color}",
                        callback_data=f"color_{product.id}_{color}"
                    ))
                keyboard.append(row)
    
    # Остальные кнопки
    keyboard.extend([
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}")],
        [InlineKeyboardButton("✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
    ])
    
    return InlineKeyboardMarkup(keyboard)