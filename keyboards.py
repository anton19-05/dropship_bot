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
    """
    Создает клавиатуру для карточки товара.
    
    В карточке товара отображаются ТОЛЬКО:
    1. Главные атрибуты (type: main) — с галочками ✅
    2. Кнопки: Отзывы, В корзину, В избранное, Корзина, Избранное, Заказать, Назад
    
    Обычные атрибуты (без type: main) НЕ отображаются в карточке!
    Они будут показаны при нажатии "Заказать" или "В корзину".
    """
    keyboard = []
    
    # ============================================================
    # 1. ТОЛЬКО ГЛАВНЫЕ АТРИБУТЫ (type: main) — отображаются в карточке
    # ============================================================
    main_attrs = product.get_main_attributes()
    
    for attr_key, attr_value in main_attrs.items():
        variants = attr_value.get('variants', {})
        
        # Если variants - словарь {value: {}}
        if isinstance(variants, dict):
            variant_names = list(variants.keys())
        # Если variants - список
        elif isinstance(variants, list):
            variant_names = variants
        else:
            continue
        
        # Получаем выбранное значение для этого атрибута
        selected = context.user_data.get(f"attr_{attr_key}_{user_id}") if context and user_id else None
        
        # Создаем ряд кнопок для атрибута
        row = []
        for variant in variant_names:
            marker = "✅ " if selected == variant else ""
            row.append(InlineKeyboardButton(
                f"{marker}{variant}",
                callback_data=f"attr_{product.id}_{attr_key}_{variant}"
            ))
        
        # Добавляем заголовок атрибута
        display_name = attr_key.capitalize()
        if row:
            keyboard.append([InlineKeyboardButton(f"📌 {display_name}:", callback_data="noop")])
            # Разбиваем на ряды по 3 кнопки
            for i in range(0, len(row), 3):
                keyboard.append(row[i:i+3])
    
    # ============================================================
    # 2. РАЗМЕРЫ — НЕ ДОБАВЛЯЕМ В КАРТОЧКУ!
    # Они будут показаны при нажатии "Заказать" или "В корзину"
    # ============================================================
    # Размеры УДАЛЕНЫ из карточки!
    
    # ============================================================
    # 3. ОСТАЛЬНЫЕ КНОПКИ (без изменений)
    # ============================================================
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