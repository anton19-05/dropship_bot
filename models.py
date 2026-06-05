import json
import os


class Product:
    def __init__(self, data):
        self.id = data.get("id")
        self.code = data.get("code")
        self.name = data.get("name")
        self.category = data.get("category")
        self.price = data.get("price")
        self.old_price = data.get("old_price")
        self.photo = data.get("photo")
        self.photos = data.get("photos", {})
        self.description = data.get("description")
        self.rating = data.get("rating", 4.5)
        self.orders = data.get("orders", 0)
        self.colors_reviews = data.get("colors_reviews", {})
        self.colors_reviews_text = data.get("colors_reviews_text", {})
        self.has_sizes = data.get("has_sizes", False)
        self.attributes = data.get("attributes", {})

    def get_text(self, color=None):
        old_price_str = f"~~{self.old_price} руб~~ " if self.old_price else ""
        return f"""
👟 *{self.name}* 👟

⭐ {self.rating} ★★★★★ | 📦 {self.orders} заказов
🔖 *Код товара:* `{self.code}`

💰 Цена: {old_price_str}→ *{self.price} руб*

📋 *Характеристики:*
{self.description}

🚚 *Доставка:* 15-25 дней
✅ *Гарантия:* 14 дней
"""

    def get_photo(self, color=None):
        if color and color in self.photos:
            return self.photos[color]
        return self.photo

    def get_attributes(self):
        return self.attributes

    def get_reviews_for_color(self, color):
        if self.colors_reviews and color in self.colors_reviews:
            return self.colors_reviews[color]
        return []

    def get_reviews_text_for_color(self, color):
        if self.colors_reviews_text and color in self.colors_reviews_text:
            return self.colors_reviews_text[color]
        color_name = color.capitalize()
        return f"⭐ ОТЗЫВЫ НА {color_name} КРОССОВКИ ⭐"


class ProductManager:
    def __init__(self, json_path="data/products.json"):
        self.products = []
        self.products_by_id = {}
        self.products_by_code = {}
        self._load(json_path)

    def _load(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get("products", []):
                    product = Product(item)
                    self.products.append(product)
                    self.products_by_id[product.id] = product
                    self.products_by_code[product.code] = product

    def get_by_id(self, prod_id):
        return self.products_by_id.get(prod_id)

    def get_by_code(self, code):
        return self.products_by_code.get(code)

    def get_by_category(self, category):
        return [p for p in self.products if p.category == category]


class MessageManager:
    def __init__(self):
        self.user_messages = {}

    async def add(self, bot, chat_id, user_id, message):
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(message.message_id)

    async def clear(self, bot, chat_id, user_id, keep_last=False):
        if user_id in self.user_messages:
            to_delete = self.user_messages[user_id]
            if keep_last and to_delete:
                to_delete = to_delete[:-1]
            for msg_id in to_delete:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except:
                    pass
            self.user_messages[user_id] = []


products_manager = ProductManager()
msg_manager = MessageManager()
