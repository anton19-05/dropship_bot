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
        self.photo = data.get('photo', '')
        self.photos = data.get('photos', {})
        self.rating = data.get('rating', 0)
        self.orders = data.get('orders', 0)
        self.attributes = data.get('attributes', {})
        self._colors_reviews = {}  # не используется в новой версии
    
    def get_text(self) -> str:
        """Формирует текст для карточки товара"""
        text = f"👟 *{self.name}*\n\n"
        text += f"💰 Цена: {self.price} руб.\n"
        if self.old_price and self.old_price > self.price:
            text += f"~~{self.old_price} руб.~~\n"
        text += f"\n📝 {self.description}\n"
        if self.rating:
            text += f"\n⭐ Рейтинг: {self.rating}"
        if self.orders:
            text += f"\n📦 Заказов: {self.orders}"
        return text
    
    def get_photo(self) -> str:
        """Возвращает путь к фото"""
        if self.photo and os.path.exists(self.photo):
            return self.photo
        return ""
    
    def get_attributes(self) -> Dict:
        """Возвращает атрибуты товара"""
        return self.attributes
    
    def get_sizes(self) -> List:
        """Возвращает список размеров (если есть)"""
        sizes = self.attributes.get('sizes', [])
        if isinstance(sizes, list):
            return sizes
        return []
    
    @property
    def has_sizes(self) -> bool:
        """Проверяет, есть ли размеры у товара"""
        return bool(self.get_sizes())
    
    def get_reviews_for_color(self, color: str) -> List[str]:
        """Возвращает отзывы для цвета (из photos)"""
        # В новой версии используем photos как источник отзывов
        if color in self.photos:
            return [self.photos[color]] if self.photos[color] else []
        return []
    
    def get_colors(self) -> List[str]:
        """Возвращает список доступных цветов"""
        colors_attr = self.attributes.get('colors', {})
        if isinstance(colors_attr, dict) and colors_attr.get('type') == 'main':
            variants = colors_attr.get('variants', {})
            return list(variants.keys())
        elif isinstance(colors_attr, list):
            return colors_attr
        return []


class ProductsManager:
    """Менеджер товаров (читает из Google Sheets)"""
    
    def __init__(self):
        self._products_cache = []
        self._cache_time = 0
        self._cache_ttl = 60  # секунд
    
    def _load_products(self) -> List[Dict]:
        """Загружает товары из Google Sheets с кешированием"""
        import time
        current_time = time.time()
        
        # Если кеш устарел или пуст — обновляем
        if not self._products_cache or (current_time - self._cache_time > self._cache_ttl):
            try:
                raw_products = storage.get_all_products()
                self._products_cache = raw_products
                self._cache_time = current_time
                logger.info(f"📦 Загружено {len(self._products_cache)} товаров из Google Sheets")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки товаров из Google Sheets: {e}")
                # Возвращаем кеш, если он есть
                if not self._products_cache:
                    return []
        
        return self._products_cache
    
    def get_all(self) -> List[Product]:
        """Возвращает все товары как объекты Product"""
        return [Product(p) for p in self._load_products()]
    
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Получает товар по ID"""
        for product_data in self._load_products():
            if product_data.get('id') == product_id:
                return Product(product_data)
        return None
    
    def get_by_code(self, code: str) -> Optional[Product]:
        """Получает товар по коду"""
        for product_data in self._load_products():
            if product_data.get('code') == code:
                return Product(product_data)
        return None
    
    def get_by_category(self, category: str) -> List[Product]:
        """Получает товары по категории"""
        products = []
        for product_data in self._load_products():
            if product_data.get('category') == category:
                products.append(Product(product_data))
        return products
    
    def get_all_categories(self) -> List[str]:
        """Получает список всех категорий"""
        categories = set()
        for product_data in self._load_products():
            category = product_data.get('category')
            if category:
                categories.add(category)
        return list(categories)
    
    def get_products_by_category_with_limit(self, category: str, limit: int = 20) -> List[Product]:
        """Получает товары категории с ограничением"""
        products = self.get_by_category(category)
        return products[:limit]

# Создаем глобальный экземпляр
products_manager = ProductsManager()