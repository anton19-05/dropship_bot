import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from keyboards import get_categories_keyboard, get_product_keyboard, get_subcategories_keyboard
from models import products_manager, msg_manager
from models_categories import categories_manager
from debug import info, debug, error, success, warning, print_state
from logger import send_debug

user_states = {}


async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список категорий при нажатии на кнопку Каталог"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    await msg_manager.clear(context.bot, chat_id, user_id)
    
    # Используем get_categories_keyboard() для показа категорий
    from keyboards import get_categories_keyboard
    
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📦 *КАТАЛОГ ТОВАРОВ*\n\n👇 Выберите категорию:",
        parse_mode="Markdown",
        reply_markup=get_categories_keyboard()
    )
    await msg_manager.add(context.bot, chat_id, user_id, msg)


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает товары выбранной категории"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    category = query.data.replace("cat_", "")

    # 📨 ДИАГНОСТИКА: отправляем себе в Telegram
    try:
        await context.bot.send_message(
            chat_id=1941249302,
            text=f"🔍 show_category\ncategory={category}\nВсего товаров в БД: {len(products_manager.products)}"
        )
    except Exception as e:
        print(f"Ошибка отправки диагностики: {e}")

    # Получаем товары по категории
    products = products_manager.get_by_category(category)

    # 📨 ДИАГНОСТИКА: сколько найдено
    try:
        categories_list = [p.category for p in products_manager.products]
        await context.bot.send_message(
            chat_id=1941249302,
            text=f"🔍 Результат: найдено {len(products)} товаров для '{category}'\nКатегории всех товаров: {categories_list}"
        )
    except Exception as e:
        print(f"Ошибка отправки диагностики: {e}")

    if not products:
        warning("CATALOG", f"Нет товаров в категории {category}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="📦 *Товаров пока нет*\n\n✨ Скоро появятся!",
            parse_mode="Markdown"
        )
        return

    user_states[user_id] = {
        "products": products,
        "page": 0,
        "category": category
    }

    try:
        await query.message.delete()
        debug("CATALOG", "Сообщение с категориями удалено")
    except Exception as e:
        warning("CATALOG", f"Не удалось удалить сообщение: {e}")

    await show_products_page(update, user_id, 0, context)
    success("CATALOG", f"Показана страница с товарами для категории {category}")


# НОВЫЙ ОБРАБОТЧИК: Выбор категории из главного меню
async def show_category_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора категории из главного меню"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    category_id = query.data.replace("category_", "")
    category = categories_manager.get_by_id(category_id)
    
    if not category:
        await query.answer("❌ Категория не найдена!", show_alert=True)
        return
    
    # ✅ ПРЯМОЙ ПОИСК ТОВАРОВ (временно для проверки)
    from models import products_manager
    products = products_manager.get_by_category(category_id)
    
    # Диагностика (отправим вам в Telegram)
    await context.bot.send_message(
        chat_id=1941249302,
        text=f"🔍 Категория: {category_id}\nНайдено товаров: {len(products)}\nТовары: {[p.name for p in products]}"
    )
    
    if products:
        user_states[user_id] = {
            "products": products,
            "page": 0,
            "category": category_id
        }
        await show_products_page(update, user_id, 0, context)
    else:
        await query.edit_message_text(
            text=f"📦 *{category['name']}*\n\nТоваров пока нет.\n✨ Скоро появятся!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="main_back")
            ]])
        )


# НОВЫЙ ОБРАБОТЧИК: Выбор подкатегории
async def show_subcategory_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора подкатегории"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    subcategory_id = query.data.replace("subcat_", "")
    
    # Получаем родительскую категорию (для кнопки "Назад")
    parent_category_id = None
    for cat in categories_manager.get_all():
        for subcat in cat.get("subcategories", []):
            if subcat["id"] == subcategory_id:
                parent_category_id = cat["id"]
                break
        if parent_category_id:
            break
    
    context.user_data[f"current_category_{user_id}"] = parent_category_id
    context.user_data[f"current_subcategory_{user_id}"] = subcategory_id
    
    # Получаем товары подкатегории
    products = categories_manager.get_products_by_subcategory(subcategory_id)
    
    if not products:
        await query.edit_message_text(
            text="📦 *Товаров пока нет*\n\n✨ Скоро появятся!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data=f"category_{parent_category_id}")
            ]])
        )
        return
    
    # Сохраняем в user_states и показываем товары
    user_states[user_id] = {
        "products": products,
        "page": 0,
        "category": subcategory_id
    }
    
    await show_products_page(update, user_id, 0, context)


async def show_products_page(update, user_id, page, context=None, edit=False):
    """Показывает страницу с товарами и пагинацией внизу"""
    state = user_states.get(user_id)
    if not state:
        return

    products = state["products"]
    items_per_page = 3
    total_pages = (len(products) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, len(products))
    page_products = products[start:end]

    # Получаем chat_id и bot
    if hasattr(update, 'callback_query'):
        chat_id = update.callback_query.message.chat_id
        bot = context.bot
    else:
        chat_id = update.effective_chat.id
        bot = context.bot

    # Удаляем старые сообщения
    await msg_manager.clear(bot, chat_id, user_id)

    message_ids = []

    # Показываем товары на странице
    for product in page_products:
        text = product.get_text()
        photo = product.get_photo()

        # Кнопка "Перейти" под каждым товаром
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔗 Перейти", callback_data=f"goto_product_{product.id}")]
        ])

        try:
            if os.path.exists(photo):
                with open(photo, 'rb') as f:
                    msg = await bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption=text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    message_ids.append(msg.message_id)
            else:
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                message_ids.append(msg.message_id)
        except Exception as e:
            print(f"Ошибка отправки: {e}")
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            message_ids.append(msg.message_id)

    # ========== ПАГИНАЦИЯ ВСЕГДА ВНИЗУ ==========
    # Формируем кнопки пагинации
    nav_buttons_row = []

    # Кнопка "Назад"
    if page > 0:
        nav_buttons_row.append(InlineKeyboardButton(
            "◀️ Назад", callback_data=f"page_{page-1}"))
    else:
        nav_buttons_row.append(InlineKeyboardButton(
            "◀️ Назад", callback_data="noop"))

    # Кнопка "Вперед"
    if page < total_pages - 1:
        nav_buttons_row.append(InlineKeyboardButton(
            "Вперед ▶️", callback_data=f"page_{page+1}"))
    else:
        nav_buttons_row.append(InlineKeyboardButton(
            "Вперед ▶️", callback_data="noop"))

    # Информация о странице
    page_info = f"📄 *Страница {page + 1} из {total_pages}*"

        # Клавиатура пагинации
    # Получаем текущую категорию из state
    current_category = state.get("category", "shoes")
    
    keyboard = [
        nav_buttons_row,
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_catalog_from_products")]
    ]

    # Отправляем панель пагинации
    nav_msg = await bot.send_message(
        chat_id=chat_id,
        text=page_info,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    message_ids.append(nav_msg.message_id)

    # Сохраняем ID всех сообщений
    if "last_products_msg" not in context.user_data:
        context.user_data["last_products_msg"] = {}
    context.user_data["last_products_msg"][user_id] = message_ids
    state["page"] = page


async def change_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    page = int(query.data.replace("page_", ""))
    await show_products_page(update, context, user_id, page)


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    product_id = query.data.replace("product_", "")
    product = products_manager.get_by_id(product_id)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # ✅ СОХРАНЯЕМ ID ТОВАРА ДЛЯ ВОЗВРАТА
    context.user_data[f"last_product_id_{user_id}"] = product_id

    # ... остальной код функции

    # ✅ НОВЫЙ КОД: Определяем первый цвет из attributes
    attributes = product.get_attributes()
    colors = attributes.get("colors", [])
    
    if colors:
        default_color = colors[0]
    else:
        default_color = "белый"
    
    # Сохраняем выбранный цвет
    context.user_data[f"color_{user_id}"] = default_color
    current_color = default_color

    # Удаляем старое сообщение
    try:
        await query.message.delete()
    except:
        pass

    text = product.get_text(current_color)
    photo = product.get_photo(current_color)

    from keyboards import get_product_keyboard

    try:
        if os.path.exists(photo):
            with open(photo, 'rb') as f:
                msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_product_keyboard(product, current_color)
                )
                await msg_manager.add(context.bot, chat_id, user_id, msg)
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_product_keyboard(product, current_color)
            )
            await msg_manager.add(context.bot, chat_id, user_id, msg)
    except Exception as e:
        print(f"Ошибка: {e}")
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=get_product_keyboard(product, current_color)
        )
        await msg_manager.add(context.bot, chat_id, user_id, msg)


async def change_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    print(f"DEBUG change_color: query.data = {query.data}")

    user_id = query.from_user.id

    # Получаем данные: color_nb_550_blue
    data = query.data.replace("color_", "")

    # Ищем последнее подчеркивание, чтобы отделить ID от цвета
    last_underscore = data.rfind("_")

    if last_underscore == -1:
        print("DEBUG change_color: не найдено подчеркивание")
        return

    product_id = data[:last_underscore]  # nb_550
    color = data[last_underscore + 1:]   # blue

    print(f"DEBUG change_color: product_id={product_id}, color={color}")

    # Сохраняем выбранный цвет
    context.user_data[f"color_{user_id}"] = color

    # Получаем товар
    product = products_manager.get_by_id(product_id)
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Удаляем старое сообщение
    try:
        await query.message.delete()
    except:
        pass

    # Отправляем новое сообщение с обновлённым цветом
    chat_id = query.message.chat_id
    text = product.get_text(color)
    photo = product.get_photo(color)

    from keyboards import get_product_keyboard

    try:
        if os.path.exists(photo):
            with open(photo, 'rb') as f:
                msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_product_keyboard(product, color)
                )
                await msg_manager.add(context.bot, chat_id, user_id, msg)
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_product_keyboard(product, color)
            )
            await msg_manager.add(context.bot, chat_id, user_id, msg)
    except Exception as e:
        print(f"Ошибка отправки: {e}")


async def back_to_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    await msg_manager.clear(context.bot, chat_id, user_id)
    await catalog(update, context)


async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает отзывы для выбранного цвета товара"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    product_id = query.data.replace("reviews_", "")
    product = products_manager.get_by_id(product_id)

    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    current_color = context.user_data.get(f"color_{user_id}", "white")
    reviews_photos = product.get_reviews_for_color(current_color)

    # Сохраняем страницу для возврата (для кнопки "Назад" в карточке)
    if user_id in user_states:
        page = user_states[user_id].get("page", 0)
        context.user_data[f"back_page_{user_id}"] = page

    # Удаляем сообщение с карточкой товара
    try:
        await query.message.delete()
    except:
        pass

    if not reviews_photos:
        keyboard = [[InlineKeyboardButton(
            "🔙 Назад к товару", callback_data=f"back_to_product_{product_id}")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"⭐ *ОТЗЫВЫ* ⭐\n\n📝 Для {current_color} цвета отзывов пока нет",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Сохраняем данные для листалки
    context.user_data[f"reviews_product_{user_id}"] = product_id
    context.user_data[f"reviews_color_{user_id}"] = current_color
    context.user_data[f"reviews_index_{user_id}"] = 0

    await send_review_photo(update, context, 0)


async def send_review_photo(update, context, index):
    """Отправляет фото отзыва"""
    query = update.callback_query
    user_id = query.from_user.id
    product_id = context.user_data.get(f"reviews_product_{user_id}")
    color = context.user_data.get(f"reviews_color_{user_id}")
    product = products_manager.get_by_id(product_id)

    if not product:
        return

    reviews_photos = product.get_reviews_for_color(color)
    color_name = color.capitalize()

    if not reviews_photos or index >= len(reviews_photos):
        # Кнопка "Назад к товару" - возвращаем в карточку товара
        keyboard = [[InlineKeyboardButton(
            "🔙 Назад к товару", callback_data=f"back_to_product_{product_id}_{color}")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"⭐ *ОТЗЫВЫ* ⭐\n\n📝 Для {color_name} цвета отзывов пока нет",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    total = len(reviews_photos)
    chat_id = query.message.chat_id
    photo_path = reviews_photos[index]

    # Проверяем существование файла
    if not os.path.exists(photo_path):
        alt_path = f"/Users/maksimmaksimov/dropship_bot/{photo_path}"
        if os.path.exists(alt_path):
            photo_path = alt_path
        else:
            keyboard = [[InlineKeyboardButton(
                "🔙 Назад к товару", callback_data=f"back_to_product_{product_id}_{color}")]]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⭐ *ОТЗЫВЫ НА {color_name} КРОССОВКИ* ⭐\n\n❌ Фото временно недоступно",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    caption = f"⭐ *ОТЗЫВЫ НА {color_name} КРОССОВКИ* ⭐"

    # Кнопка "Назад к товару" - возвращаем в карточку товара
    keyboard = [
        [
            InlineKeyboardButton("◀️ Назад", callback_data="review_prev"),
            InlineKeyboardButton(f"{index + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton("Вперед ▶️", callback_data="review_next")
        ],
        [InlineKeyboardButton(
            "🔙 Назад к товару", callback_data=f"back_to_product_{product_id}")]
    ]

    try:
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")


async def review_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current = context.user_data.get(f"reviews_index_{user_id}", 0)
    context.user_data[f"reviews_index_{user_id}"] = current + 1
    await send_review_photo(update, context, current + 1)


async def review_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current = context.user_data.get(f"reviews_index_{user_id}", 0)
    context.user_data[f"reviews_index_{user_id}"] = current - 1
    await send_review_photo(update, context, current - 1)


async def back_to_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к карточке товара"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("back_to_product_", "")
    
    # Диагностика
    await context.bot.send_message(
        chat_id=1941249302,
        text=f"1️⃣ data = {data}"
    )
    
    # ✅ ИСПРАВЛЕНО: правильное извлечение product_id
    # Нужно понять, есть ли в конце цвет (через подчёркивание)
    # Формат может быть: "classic_shoes" или "classic_shoes_белый"
    
    parts = data.split("_")
    
    # Если есть цвет (3 части: [classic, shoes, белый])
    if len(parts) >= 3:
        # ID товара — первые две части с подчёркиванием
        product_id = f"{parts[0]}_{parts[1]}"
        color = "_".join(parts[2:])  # цвет может быть из нескольких частей
    else:
        # Если только ID товара (classic_shoes)
        product_id = data
        color = context.user_data.get(f"color_{query.from_user.id}", "белый")
    
    await context.bot.send_message(
        chat_id=1941249302,
        text=f"2️⃣ product_id = {product_id}"
    )
    
    product = products_manager.get_by_id(product_id)
    
    await context.bot.send_message(
        chat_id=1941249302,
        text=f"3️⃣ product найден = {product is not None}"
    )
    
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return
    
    user_id = query.from_user.id
    context.user_data[f"color_{user_id}"] = color
    
    # Получаем сохранённую страницу и категорию
    page = context.user_data.get(f"back_page_{user_id}", 0)
    category = product.category
    
    # Удаляем сообщение
    try:
        await query.message.delete()
    except:
        pass
    
    # Показываем карточку товара
    from utils import show_product
    await show_product(
        query.message.chat_id, 
        product_id, 
        color, 
        context, 
        context.bot, 
        category, 
        page
    )


async def goto_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    product_id = query.data.replace("goto_product_", "")
    
    # ✅ СОХРАНЯЕМ ID ТОВАРА ДЛЯ ВОЗВРАТА
    context.user_data[f"last_product_id_{user_id}"] = product_id

    # ... остальной код функции

    debug("PRODUCT", f"Переход к товару {product_id}", {"user_id": user_id})

    product = products_manager.get_by_id(product_id)

    if not product:
        error("PRODUCT", f"Товар {product_id} не найден")
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Сохраняем категорию и страницу для возврата
    if user_id in user_states:
        current_page = user_states[user_id].get("page", 0)
        current_category = user_states[user_id].get(
            "category", product.category)
        context.user_data[f"back_page_{user_id}"] = current_page
        context.user_data[f"back_category_{user_id}"] = current_category
        debug(
            "PRODUCT", f"Сохранена страница {current_page}, категория {current_category} для возврата")
    else:
        context.user_data[f"back_page_{user_id}"] = 0
        context.user_data[f"back_category_{user_id}"] = product.category
        debug(
            "PRODUCT", f"Создано состояние: страница 0, категория {product.category}")

    # ✅ НОВЫЙ КОД: Определяем первый цвет из attributes
    attributes = product.get_attributes()
    colors = attributes.get("colors", [])
    
    if colors:
        # Если есть цвета, выбираем первый
        default_color = colors[0]
    else:
        # Если цветов нет, используем "белый" или значение по умолчанию
        default_color = "белый"
    
    # Сохраняем выбранный цвет
    context.user_data[f"color_{user_id}"] = default_color
    current_color = default_color

    await msg_manager.clear(context.bot, query.message.chat_id, user_id)
    debug("PRODUCT", "Старые сообщения очищены")

    from utils import show_product
    await show_product(
        query.message.chat_id, 
        product_id, 
        current_color, 
        context, 
        context.bot, 
        product.category, 
        context.user_data.get(f"back_page_{user_id}", 0)
    )

    try:
        await query.message.delete()
        debug("PRODUCT", "Сообщение с кнопкой Перейти удалено")
    except:
        pass

    success("PRODUCT", f"Показана карточка товара {product.name}")


async def back_to_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data.replace("back_to_category_", "")
    parts = data.split("_")

    # Извлекаем категорию и страницу
    if len(parts) >= 2:
        category = parts[0]
        try:
            page = int(parts[1])
        except:
            page = context.user_data.get(f"back_page_{user_id}", 0)
    else:
        category = data
        page = context.user_data.get(f"back_page_{user_id}", 0)

    # Если категория не определена, берём из сохранённой
    if not category or category == "None":
        category = context.user_data.get(f"back_category_{user_id}", "shoes")
        page = context.user_data.get(f"back_page_{user_id}", 0)
        debug("BACK", f"Категория взята из сохранённой: {category}")

    debug("BACK", f"Возврат в категорию", {
          "category": category, "page": page, "user_id": user_id})

    products = products_manager.get_by_category(category)

    if not products:
        warning("BACK", f"Нет товаров в категории {category}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📦 *Товаров пока нет*",
            parse_mode="Markdown"
        )
        return

    user_states[user_id] = {
        "products": products,
        "page": page,
        "category": category
    }

    # Удаляем сообщение с карточкой товара
    if "last_product_msg" in context.user_data:
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=context.user_data["last_product_msg"])
        except:
            pass
        context.user_data.pop("last_product_msg", None)
        debug("BACK", "Сообщение с карточкой товара удалено")

    await show_products_page(update, user_id, page, context)
    success("BACK", f"Возврат в категорию {category}, страница {page}")


async def back_to_product_from_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к карточке товара из отзывов"""
    query = update.callback_query
    await query.answer()

    data = query.data.replace("back_to_product_from_reviews_", "")
    parts = data.split("_")
    prod_id = "_".join(parts[:-1])
    color_id = parts[-1]

    user_id = query.from_user.id
    context.user_data[f"color_{user_id}"] = color_id

    product = products_manager.get_by_id(prod_id)
    if not product:
        await query.answer("❌ Товар не найден!", show_alert=True)
        return

    # Получаем сохранённую страницу (для кнопки "Назад" в карточке)
    page = context.user_data.get(f"back_page_{user_id}", 0)
    category = product.category

    # Удаляем сообщение с отзывами
    try:
        await query.message.delete()
    except:
        pass

    # Показываем карточку товара
    from utils import show_product
    await show_product(query.message.chat_id, prod_id, color_id, context, context.bot, category, page)


async def back_to_catalog_from_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к списку категорий из страницы с товарами"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # Очищаем старые сообщения
    await msg_manager.clear(context.bot, chat_id, user_id)
    
    # Показываем категории
    from keyboards import get_categories_keyboard
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="📦 *КАТАЛОГ ТОВАРОВ*\n\n👇 Выберите категорию:",
        parse_mode="Markdown",
        reply_markup=get_categories_keyboard()
    )