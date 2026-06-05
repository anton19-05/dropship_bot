# user_data.py - Хранение данных пользователей

import json
import os
import re

# Файл для сохранения данных
DATA_FILE = "user_data.json"

# Хранилище данных пользователей
user_data = {}
# Хранилище занятых никнеймов
used_nicknames = {}

# Список запрещённых слов (матерные и оскорбительные)
BAD_WORDS = [
    "сука", "бля", "хуй", "пизда", "залупа", "мудак", "редиска",
    "дебил", "идиот", "тупой", "урод", "гандон", "пидор", "пидар",
    "ебан", "ебать", "выеб", "хуесос", "чмо", "шлюха", "шлюх",
    "проститутка", "сперма", "конча", "секс", "порно", "хер", "хрен",
    "нахер", "нахуй", "охуел", "охуенная", "ахуенный", "заебал",
    "долбаеб", "долбоеб", "елда", "манда", "мудила", "петух", "гей"
]

def load_data():
    """Загрузить данные из файла"""
    global user_data, used_nicknames
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_data = data.get("users", {})
                used_nicknames = data.get("used_nicknames", {})
        except:
            user_data = {}
            used_nicknames = {}
    else:
        user_data = {}
        used_nicknames = {}

def save_data():
    """Сохранить данные в файл"""
    try:
        data = {
            "users": user_data,
            "used_nicknames": used_nicknames
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def contains_bad_words(text):
    """Проверка на наличие запрещённых слов"""
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

def is_valid_nickname(nickname):
    """Проверка валидности никнейма"""
    # Только буквы, цифры, подчёркивание, длина 3-20 символов
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', nickname):
        return False, "Никнейм должен содержать только буквы, цифры и _ (3-20 символов)"
    if contains_bad_words(nickname):
        return False, "Никнейм содержит запрещённые слова"
    return True, "OK"

def is_nickname_taken(nickname):
    """Проверка занятости никнейма"""
    return nickname in used_nicknames and used_nicknames[nickname] != ""

def get_user_data(user_id):
    """Получить данные пользователя"""
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = {
            "name": "",           # ФИО
            "nickname": "",       # Никнейм для отзывов
            "phone": "",          # Телефон
            "index": "",          # Почтовый индекс
            "city": "",           # Город
            "address": "",        # Улица, дом, квартира
            "cart": {},
            "favorites": [],
            "orders": [],
            "reviews": []
        }
    return user_data[user_id_str]

def save_user_data(user_id, data):
    """Сохранить данные пользователя"""
    user_id_str = str(user_id)
    
    # Обновляем словарь занятых никнеймов
    old_data = user_data.get(user_id_str, {})
    old_nickname = old_data.get("nickname", "")
    new_nickname = data.get("nickname", "")
    
    if old_nickname and old_nickname != new_nickname:
        used_nicknames.pop(old_nickname, None)
    if new_nickname:
        used_nicknames[new_nickname] = user_id_str
    
    user_data[user_id_str] = data
    save_data()

def add_to_cart(user_id, product_code, quantity=1, size=None, color_id="white", product_name=""):
    """Добавить товар в корзину"""
    data = get_user_data(user_id)
    
    if size:
        cart_key = f"{product_code}_{size}"
    else:
        cart_key = product_code
    
    if cart_key in data["cart"]:
        if isinstance(data["cart"][cart_key], dict):
            data["cart"][cart_key]["quantity"] += quantity
        else:
            data["cart"][cart_key] += quantity
    else:
        data["cart"][cart_key] = {
            "product_code": product_code,
            "size": size or "Не выбран",
            "quantity": quantity,
            "color_id": color_id,
            "product_name": product_name
        }
    
    save_user_data(user_id, data)

def remove_from_cart(user_id, cart_key):
    """Удалить товар из корзины по ключу"""
    data = get_user_data(user_id)
    if cart_key in data["cart"]:
        del data["cart"][cart_key]
    save_user_data(user_id, data)

def add_to_favorites(user_id, product_code, size=None, color_id="white", product_name=""):
    """Добавить товар в избранное"""
    data = get_user_data(user_id)
    
    fav_item = {
        "product_code": product_code,
        "size": size or "Не выбран",
        "color_id": color_id,
        "product_name": product_name
    }
    
    # Проверяем, нет ли уже такого
    exists = False
    for item in data["favorites"]:
        if item.get("product_code") == product_code and item.get("size") == fav_item["size"]:
            exists = True
            break
    
    if not exists:
        data["favorites"].append(fav_item)
    
    save_user_data(user_id, data)

def remove_from_favorites(user_id, product_code, size):
    """Удалить товар из избранного"""
    data = get_user_data(user_id)
    data["favorites"] = [
        item for item in data["favorites"] 
        if not (item.get("product_code") == product_code and item.get("size") == size)
    ]
    save_user_data(user_id, data)

def add_review(user_id, review_text):
    """Добавить отзыв"""
    data = get_user_data(user_id)
    from datetime import datetime
    nickname = data.get("nickname", "Аноним")
    data["reviews"].append({
        "nickname": nickname,
        "text": review_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_user_data(user_id, data)

def get_product_by_code(code):
    """Найти товар по коду"""
    from products_config import PRODUCTS
    for color_id, product in PRODUCTS.items():
        if product.get("code", "") == code:
            return product, color_id
    return None, None

def clear_cart(user_id):
    """Очистить корзину"""
    data = get_user_data(user_id)
    data["cart"] = {}
    save_user_data(user_id, data)

# Загружаем данные при старте
load_data()