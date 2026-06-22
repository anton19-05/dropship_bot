import logging
from typing import List, Dict, Optional
from google_sheets_storage import storage

logger = logging.getLogger(__name__)

class CategoriesManager:
    """Менеджер категорий (читает из Google Sheets)"""
    
    def __init__(self):
        self._categories_cache = []
        self._cache_time = 0
        self._cache_ttl = 60  # секунд
    
    def _load_categories(self) -> List[Dict]:
        """Загружает категории из Google Sheets с кешированием"""
        import time
        current_time = time.time()
        
        if not self._categories_cache or (current_time - self._cache_time > self._cache_ttl):
            try:
                raw_categories = storage.get_categories()
                self._categories_cache = raw_categories
                self._cache_time = current_time
                logger.info(f"📂 Загружено {len(self._categories_cache)} категорий из Google Sheets")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки категорий из Google Sheets: {e}")
                if not self._categories_cache:
                    return self._get_default_categories()
        
        return self._categories_cache
    
    def _get_default_categories(self) -> List[Dict]:
        """Возвращает категории по умолчанию (если нет в Google Sheets)"""
        return [
            {"id": "shoes", "name": "👟 Обувь", "order": 1, "subcategories": [{"id": "sneakers", "name": "Кроссовки", "order": 1}]},
            {"id": "sport", "name": "🏀 Спорт", "order": 2, "subcategories": [{"id": "fishing", "name": "🎣 Рыбалка", "order": 1}]},
            {"id": "electronics", "name": "📱 Электроника", "order": 3, "subcategories": [{"id": "powerbanks", "name": "🔋 Повербанки", "order": 1}]},
            {"id": "clothing", "name": "👕 Одежда", "order": 4, "subcategories": []},
            {"id": "accessories", "name": "🕶️ Аксессуары", "order": 5, "subcategories": []}
        ]
    
    def get_all(self) -> List[Dict]:
        """Возвращает все категории"""
        return self._load_categories()
    
    def get_by_id(self, category_id: str) -> Optional[Dict]:
        """Получает категорию по ID"""
        for category in self._load_categories():
            if category.get('id') == category_id:
                return category
        return None
    
    def get_subcategories(self, category_id: str) -> List[Dict]:
        """Получает подкатегории категории"""
        category = self.get_by_id(category_id)
        if category:
            return category.get('subcategories', [])
        return []
    
    def get_categories_as_dict(self) -> Dict[str, str]:
        """Возвращает словарь {id: name} для всех категорий"""
        return {c['id']: c['name'] for c in self._load_categories()}
    
    def get_category_name(self, category_id: str) -> str:
        """Возвращает имя категории по ID"""
        category = self.get_by_id(category_id)
        return category.get('name', category_id) if category else category_id

# Создаем глобальный экземпляр
categories_manager = CategoriesManager()