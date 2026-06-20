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

    # ✅ ДИАГНОСТИКА
    attrs = product.get_attributes()
    if context and user_id:
        try:
            # Создаем задачу для отправки сообщения, не блокируя основной поток
            async def send_diagnostic():
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⌨️ get_product_keyboard:\n"
                         f"product={product.name}\n"
                         f"attrs={attrs}\n"
                         f"user_id={user_id}\n"
                         f"current_color={current_color}"
                )
            asyncio.create_task(send_diagnostic())
        except:
            pass

    # 1. Находим главный атрибут
    main_attr_key = None
    main_attr_value = None
    for key, value in attrs.items():
        if isinstance(value, dict) and value.get("type") == "main":
            main_attr_key = key
            variants = value.get("variants", {})
            if variants:
                main_attr_value = variants
            break
    
    # 2. Если есть главный атрибут с вариантами — показываем кнопки
    if main_attr_value:
        row = []
        selected = None
        if context and user_id and main_attr_key:
            selected = context.user_data.get(f"attr_{main_attr_key}_{user_id}")
        
        # ✅ ДИАГНОСТИКА: что сохранилось в user_data
        if context and user_id and main_attr_key:
            try:
                async def send_attr_diagnostic():
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🎯 attr_{main_attr_key}_{user_id} = {selected}"
                    )
                asyncio.create_task(send_attr_diagnostic())
            except:
                pass
        
        for variant_key in main_attr_value.keys():
            marker = "✅ " if selected == variant_key else ""
            row.append(InlineKeyboardButton(
                f"{marker}{variant_key}",
                callback_data=f"attr_{product.id}_{main_attr_key}_{variant_key}"
            ))
        if row:
            keyboard.append(row)
    
    # 3. Если нет главного атрибута — показываем цвета (для кроссовок)
    if not main_attr_key and "colors" in attrs:
        colors = attrs["colors"]
        if isinstance(colors, list):
            colors_row = []
            for color in colors:
                marker = "✅ " if color == current_color else ""
                colors_row.append(InlineKeyboardButton(
                    f"{marker}{color}",
                    callback_data=f"color_{product.id}_{color}"
                ))
            keyboard.append(colors_row)

    # 4. Остальные кнопки
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