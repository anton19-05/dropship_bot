from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="menu_catalog")],
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
    attrs = product.get_attributes()
    
    print(f"⌨️ get_product_keyboard: product={product.name}, attrs={attrs}, user_id={user_id}")
    
    # Находим главный атрибут
    main_key = None
    main_variants = None
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            main_key = key
            main_variants = value.get("variants", {})
            break
    
    print(f"⌨️ main_key={main_key}, main_variants={list(main_variants.keys()) if main_variants else None}")
    
    # Остальной код...
    
    # ⭐ 1. ПОКАЗЫВАЕМ ЦВЕТА (если они есть и они НЕ главный атрибут)
    if "colors" in attrs:
        colors = attrs["colors"]
        colors_row = []
        
        # Если colors — это словарь с type:main (но мы его пропускаем, т.к. это главный атрибут)
        if isinstance(colors, dict) and colors.get("type") == "main":
            pass  # пропускаем, т.к. это главный атрибут
        # Если colors — это простой список
        elif isinstance(colors, list):
            for color in colors:
                marker = "✅ " if color == current_color else ""
                colors_row.append(InlineKeyboardButton(
                    f"{marker}{color}",
                    callback_data=f"color_{product.id}_{color}"
                ))
        
        if colors_row:
            keyboard.append(colors_row)
    
    # ⭐ 2. ПОКАЗЫВАЕМ ГЛАВНЫЙ АТРИБУТ (ЛЮБОЙ, с type:main)
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            variants = value.get("variants", {})
            if variants:
                row = []
                selected = context.user_data.get(f"attr_{key}_{user_id}") if context and user_id else None
                for variant in variants.keys():
                    marker = "✅ " if selected == variant else ""
                    row.append(InlineKeyboardButton(
                        f"{marker}{variant}",
                        callback_data=f"attr_{product.id}_{key}_{variant}"
                    ))
                if row:
                    keyboard.append(row)
    
    # ⭐ 3. ОСТАЛЬНЫЕ КНОПКИ
    keyboard.extend([
        [InlineKeyboardButton("⭐ Отзывы", callback_data=f"reviews_{product.id}")],
        [
            InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}"),
            InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_add_{product.code}")
        ],
        [
            InlineKeyboardButton("🛍️ Корзина", callback_data="view_cart_from_product"),
            InlineKeyboardButton("⭐ Избранное", callback_data="view_favorites")
        ],
        [InlineKeyboardButton("✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_category_{category}_{page}")]
    ])

    return InlineKeyboardMarkup(keyboard)