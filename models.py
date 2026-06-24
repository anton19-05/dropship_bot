import os
import json
import logging
from typing import List, Dict, Optional, Any
from google_sheets_storage import storage

logger = logging.getLogger(__name__)

class Product:
    """Класс товара (данные из Google Sheets)"""
    
    def __init__(self, data: Dict):
        self.id = data.get('id', '')
        self.code = data.get('code', '')
        self.name = data.get('name', '')
        self.category = data.get('category', '')
        self.price = data.get('price', 0)
        self.old_price = data.get('old_price', 0)
        self.description = data.get('description', '')
        
        photo_raw = data.get('photo', '')
        if isinstance(photo_raw, dict):
            first_color = list(photo_raw.keys())[0] if photo_raw else None
            self.photo = photo_raw.get(first_color, '') if first_color else ''
        else:
            self.photo = photo_raw
        
        self.photos = data.get('photos', {})
        if not isinstance(self.photos, dict):
            self.photos = {}
        
        self.rating = data.get('rating', 0)
        self.orders = data.get('orders', 0)
        self.attributes = data.get('attributes', {})
        self.colors_reviews = data.get('colors_reviews', {})
        self.colors_reviews_text = data.get('colors_reviews_text', {})
    
    def get_text(self) -> str:
        """Формирует текст для карточки товара в нужном порядке"""
        text = f"📦 *{self.name}*\n\n"
        
        # 1. Рейтинг и заказы (сразу после названия)
        if self.rating:
            text += f"⭐ Рейтинг: {self.rating}\n"
        if self.orders:
            text += f"📦 Заказов: {self.orders}\n"
        text += "\n"
    
        # 2. Цена (после рейтинга)
        text += f"💰 Цена: {self.price} руб.\n"
        if self.old_price and self.old_price > self.price:
            text += f"~~{self.old_price} руб.~~\n"
        text += "\n"
    
        # 3. Описание товара (после цены)
        text += f"📝 {self.description}\n"
    
        return text
    
    def get_photo(self) -> str:
        if self.photo and isinstance(self.photo, str) and os.path.exists(self.photo):
            return self.photo
        return ""
    
    def get_attributes(self) -> Dict:
        return self.attributes
    
    # ========== НОВЫЕ МЕТОДЫ ДЛЯ ГЛАВНЫХ АТРИБУТОВ ==========
    
    def get_main_attributes(self) -> Dict:
        """Возвращает все главные атрибуты (type: main)"""
        main_attrs = {}
        for key, value in self.attributes.items():
            if isinstance(value, dict) and value.get('type') == 'main':
                main_attrs[key] = value
        return main_attrs
    
    def get_extra_attributes(self) -> Dict:
        """Возвращает обычные атрибуты (не main)"""
        extra_attrs = {}
        for key, value in self.attributes.items():
            if not (isinstance(value, dict) and value.get('type') == 'main'):
                extra_attrs[key] = value
        return extra_attrs
    
    def get_attribute_value(self, attr_key: str, user_id: int, context) -> Optional[str]:
        """Получает выбранное значение атрибута для пользователя"""
        return context.user_data.get(f"attr_{attr_key}_{user_id}")
    
    def get_sizes(self) -> List:
        sizes = self.attributes.get('sizes', [])
        if isinstance(sizes, list):
            return sizes
        return []
    
    @property
    def has_sizes(self) -> bool:
        return bool(self.get_sizes())
    
    def get_reviews_for_color(self, color: str) -> List[str]:
        reviews = self.colors_reviews.get(color, [])
        if isinstance(reviews, list):
            return reviews
        return []
    
    def get_reviews_text_for_color(self, color: str) -> str:
        return self.colors_reviews_text.get(color, f"⭐ ОТЗЫВЫ НА {color.upper()} ⭐")
    
    def get_colors(self) -> List[str]:
        colors_attr = self.attributes.get('colors', {})
        if isinstance(colors_attr, dict) and colors_attr.get('type') == 'main':
            variants = colors_attr.get('variants', {})
            return list(variants.keys())
        elif isinstance(colors_attr, list):
            return colors_attr
        return []
    
    def get_main_color(self) -> str:
        colors = self.get_colors()
        return colors[0] if colors else "белый"


class ProductsManager:
    def __init__(self):
        self._products_cache = []
        self._cache_time = 0
        self._cache_ttl = 60
    
    def _load_products(self) -> List[Dict]:
        import time
        current_time = time.time()
        
        if not self._products_cache or (current_time - self._cache_time > self._cache_ttl):
            try:
                raw_products = storage.get_all_products()
                self._products_cache = raw_products
                self._cache_time = current_time
                logger.info(f"📦 Загружено {len(self._products_cache)} товаров из Google Sheets")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки товаров из Google Sheets: {e}")
                if not self._products_cache:
                    return []
        
        return self._products_cache
    
    def get_all(self) -> List[Product]:
        return [Product(p) for p in self._load_products()]
    
    def get_by_id(self, product_id: str) -> Optional[Product]:
        for product_data in self._load_products():
            if product_data.get('id') == product_id:
                return Product(product_data)
        return None
    
    def get_by_code(self, code: str) -> Optional[Product]:
        for product_data in self._load_products():
            if product_data.get('code') == code:
                return Product(product_data)
        return None
    
    def get_by_category(self, category: str) -> List[Product]:
        products = []
        for product_data in self._load_products():
            if product_data.get('category') == category:
                products.append(Product(product_data))
        return products
    
    def get_all_categories(self) -> List[str]:
        categories = set()
        for product_data in self._load_products():
            category = product_data.get('category')
            if category:
                categories.add(category)
        return list(categories)
    
    def get_products_by_category_with_limit(self, category: str, limit: int = 20) -> List[Product]:
        products = self.get_by_category(category)
        return products[:limit]


class MessageManager:
    def __init__(self):
        self.user_messages = {}
    
    async def add(self, bot, chat_id, user_id, message):
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(message.message_id)
    
    async def clear(self, bot, chat_id, user_id):
        if user_id in self.user_messages:
            for msg_id in self.user_messages[user_id]:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except:
                    pass
            self.user_messages[user_id] = []


msg_manager = MessageManager()
products_manager = ProductsManager()