from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Каталог товаров",
                              callback_data="menu_catalog")],
        [InlineKeyboardButton("🔍 Поиск по коду", callback_data="menu_search")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ Как заказать", callback_data="menu_help")],
        [InlineKeyboardButton("📞 Контакты", callback_data="menu_contacts")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard():
    keyboard = [
        [InlineKeyboardButton("👟 Обувь", callback_data="cat_shoes")],
        [InlineKeyboardButton("👕 Одежда", callback_data="cat_clothing")],
        [InlineKeyboardButton(
            "🕶️ Аксессуары", callback_data="cat_accessories")],
        [InlineKeyboardButton("🏠 Дом и сад", callback_data="cat_home")],
        [InlineKeyboardButton(
            "📱 Электроника", callback_data="cat_electronics")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_product_keyboard(product, current_color=None, category=None, page=0):
    keyboard = []

    # Кнопки выбора цвета
    if "colors" in product.get_attributes():
        colors_row = []
        color_emoji = {
            "белый": "белый",
            "синий": "синий",
            "коричневый": "коричневый",
            "зеленый": "зеленый",
            "черный": "черный"
        }
        for color in product.get_attributes()["colors"]:
            display = color_emoji.get(color, color.capitalize())
            marker = "✅ " if color == current_color else ""
            colors_row.append(InlineKeyboardButton(
                f"{marker}{display}",
                callback_data=f"color_{product.id}_{color}"
            ))
        keyboard.append(colors_row)

    keyboard.extend([
        [InlineKeyboardButton(
            "⭐ Отзывы", callback_data=f"reviews_{product.id}")],
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}"),
         InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_add_{product.code}")],
        [InlineKeyboardButton("🛍️ Корзина", callback_data="view_cart"),
         InlineKeyboardButton("⭐ Избранное", callback_data="view_favorites")],
        [InlineKeyboardButton(
            "✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton(
            "🔙 Назад", callback_data=f"back_to_category_{category}_{page}")]
    ])

    return InlineKeyboardMarkup(keyboard)


def get_pagination_keyboard(page, total_pages, category):
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "◀️ Назад", callback_data=f"page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(
            "◀️ Назад", callback_data="noop"))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            "Вперед ▶️", callback_data=f"page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(
            "Вперед ▶️", callback_data="noop"))

    return InlineKeyboardMarkup([
        nav_buttons,
        [InlineKeyboardButton("🏠 Главная страница", callback_data="main_back")]
    ])


def get_back_keyboard(callback):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=callback)]])
