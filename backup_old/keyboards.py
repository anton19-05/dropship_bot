# keyboards.py - Все клавиатуры

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📦 Каталог", callback_data="menu_catalog")],
        [InlineKeyboardButton("🔍 Поиск", callback_data="menu_search")],
        [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")],
        [InlineKeyboardButton("📞 Контакты", callback_data="menu_contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(callback):
    """Кнопка назад"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data=callback)]
    ])


def get_categories_keyboard():
    """Категории каталога"""
    keyboard = [
        [InlineKeyboardButton("👟 Обувь", callback_data="cat_shoes")],
        [InlineKeyboardButton("👕 Одежда", callback_data="cat_clothing")],
        [InlineKeyboardButton("🎣 Рыбалка", callback_data="cat_fishing")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_product_keyboard(product, current_color=None):
    """Клавиатура для карточки товара"""
    keyboard = []

    # Кнопки выбора цвета (если есть)
    if "colors" in product.get_attributes():
        colors_row = []
        for color in product.get_attributes()["colors"]:
            marker = "✅ " if color == current_color else ""
            colors_row.append(InlineKeyboardButton(
                f"{marker}{color}",
                callback_data=f"color_{product.id}_{color}"
            ))
        keyboard.append(colors_row)

    # Основные кнопки
    keyboard.extend([
        [InlineKeyboardButton(
            "⭐ Отзывы", callback_data=f"reviews_{product.id}")],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}"),
         InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_add_{product.code}")],
        [InlineKeyboardButton("🛍️ Корзина", callback_data="goto_cart"),
         InlineKeyboardButton("⭐ Избранное", callback_data="goto_favorites")],
        [InlineKeyboardButton(
            "✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_catalog")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_pagination_keyboard(page, total_pages):
    """Пагинация"""
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(
            "◀️ Назад", callback_data=f"page_{page-1}"))
    else:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data="noop"))

    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(
            "Вперед ▶️", callback_data=f"page_{page+1}"))
    else:
        buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data="noop"))

    keyboard = [
        buttons,
        [InlineKeyboardButton("🏠 Главная", callback_data="main_back")]
    ]
    return InlineKeyboardMarkup(keyboard)
