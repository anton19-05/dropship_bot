from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_ID
import asyncio

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
    
    # Остальные кнопки
    keyboard.extend([
        [InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{product.code}")],
        [InlineKeyboardButton("✅ Заказать", callback_data=f"order_{product.id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_back")]
    ])
    
    return InlineKeyboardMarkup(keyboard)