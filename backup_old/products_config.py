# products_config.py - Файл с настройками товаров

# Категории и подкатегории
CATEGORIES = {
    "shoes": {
        "name": "👟 Обувь",
        "callback": "shoes",
        "subcategories": {
            "sneakers": "👟 Кроссовки",
            "classic": "👞 Классическая обувь",
            "sandals": "👡 Сандалии/Шлёпанцы",
            "kids_shoes": "👶 Детская обувь"
        }
    },
    "clothing": {
        "name": "👕 Одежда",
        "callback": "clothing",
        "subcategories": {
            "t_shirts": "👕 Футболки/Поло",
            "pants": "👖 Штаны/Джинсы",
            "jackets": "🧥 Куртки/Ветровки",
            "kids_clothing": "👶 Детская одежда"
        }
    },
    "accessories": {
        "name": "🕶️ Аксессуары",
        "callback": "accessories",
        "subcategories": {
            "glasses": "🕶️ Очки",
            "hats": "🧢 Кепки/Шапки",
            "bags": "💼 Сумки/Рюкзаки",
            "watches": "⌚ Часы/Ремешки"
        }
    },
    "home": {
        "name": "🏠 Дом и сад",
        "callback": "home",
        "subcategories": {
            "furniture": "🛋️ Мебель",
            "decor": "💡 Декор",
            "garden": "🌱 Сад/Огород"
        }
    },
    "electronics": {
        "name": "📱 Электроника",
        "callback": "electronics",
        "subcategories": {
            "phones": "📱 Телефоны/Аксессуары",
            "audio": "🎧 Наушники/Колонки",
            "chargers": "🔌 Зарядные устройства"
        }
    },
    "kids": {
        "name": "👶 Детские товары",
        "callback": "kids",
        "subcategories": {
            "kids_shoes": "👟 Детская обувь",
            "kids_clothing": "👕 Детская одежда",
            "toys": "🧸 Игрушки"
        }
    }
}

# Цвета для товаров (оставляем для совместимости)
COLORS = {
    "white": {"name": "⚪ Белый", "callback": "color_white", "photo": "static/1.jpg"},
    "blue": {"name": "🔵 Синий", "callback": "color_blue", "photo": "static/1.1.jpg"},
    "brown": {"name": "🟤 Коричневый", "callback": "color_brown", "photo": "static/1.2.jpg"},
}

# Товары (объединённые по моделям)
PRODUCTS = {
    "new_balance_550": {
        "code": "NB-550",
        "name": "Кроссовки New Balance 550",
        "category": "sneakers",
        "subcategory": "sneakers",
        "price": 2600,
        "old_price": 3500,
        "description": "✅ *Материал:* Натуральная кожа\n"
                        "✅ *Подошва:* Полиуретан, противоскользящая\n"
                        "✅ *Стелька:* Анатомическая, съёмная\n"
                        "✅ *Амортизация:* Да, во всей подошве\n"
                        "✅ *Размеры:* 36-45 (полноразмерные)\n"
                        "✅ *Вес:* 450 грамм",
        "rating": "4.9",
        "orders": 1247,
        "colors": {
            "white": {
                "name": "⚪ Белый",
                "photo": "static/1.jpg",
                "reviews_photos": ["static/2.jpg", "static/3.jpg", "static/4.jpg"]
            },
            "blue": {
                "name": "🔵 Синий",
                "photo": "static/1.1.jpg",
                "reviews_photos": []
            },
            "brown": {
                "name": "🟤 Коричневый",
                "photo": "static/1.2.jpg",
                "reviews_photos": []
            }
        }
    }
}

# Настройки ЮMoney
YOOMONEY_WALLET = "4100119535616904"