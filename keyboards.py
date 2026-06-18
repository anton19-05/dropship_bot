from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models_categories import categories_manager


def get_main_menu():
    """Главное меню (без категорий!)"""
    keyboard = [
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="menu_catalog")],
        [InlineKeyboardButton("🔍 Поиск по коду", callback_data="menu_search")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ Как заказать", callback_data="menu_help")],
        [InlineKeyboardButton("📞 Контакты", callback_data="menu_contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard():
    """Клавиатура с категориями (для кнопки Каталог)"""
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
    """Клавиатура с подкатегориями"""
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

    # Кнопки выбора цвета
    if "colors" in product.get_attributes():
        colors_row = []
        for color in product.get_attributes()["colors"]:
            marker = "✅ " if color == current_color else ""
            colors_row.append(InlineKeyboardButton(
                f"{marker}{color}",
                callback_data=f"color_{product.id}_{color}"
            ))
        keyboard.append(colors_row)

    # ✅ КНОПКИ ДЛЯ ДРУГИХ АТРИБУТОВ
    attrs = product.get_attributes()
    for key, values in attrs.items():
        if key == "colors":
            continue
        row = []
        for value in values:
            # Проверяем, выбран ли этот атрибут
            selected = False
            if context and user_id:
                stored_value = context.user_data.get(f"attr_{key}_{user_id}")
                selected = (stored_value == value)
            marker = "✅ " if selected else ""
            row.append(InlineKeyboardButton(
                f"{marker}{value}",
                callback_data=f"attr_{product.id}_{key}_{value}"
            ))
        if row:
            keyboard.append(row)

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


def get_pagination_keyboard(page, total_pages, category):
    """Клавиатура для пагинации"""
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data="noop"))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data="noop"))

    return InlineKeyboardMarkup([
        nav_buttons,
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_back")]
    ])


def get_back_keyboard(callback):
    """Простая кнопка назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=callback)]])