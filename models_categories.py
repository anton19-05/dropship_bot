import json
import os

class CategoryManager:
    def __init__(self, json_path="data/categories.json"):
        self.categories = []
        self.categories_by_id = {}
        self._load(json_path)

    def _load(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.categories = data.get("categories", [])
                for cat in self.categories:
                    self.categories_by_id[cat["id"]] = cat

    def get_all(self):
        """Получить все категории (отсортированные по order)"""
        return sorted(self.categories, key=lambda x: x.get("order", 999))

    def get_by_id(self, cat_id):
        """Получить категорию по ID"""
        return self.categories_by_id.get(cat_id)

    def get_subcategories(self, cat_id):
        """Получить подкатегории категории"""
        cat = self.get_by_id(cat_id)
        if cat:
            return sorted(cat.get("subcategories", []), key=lambda x: x.get("order", 999))
        return []

    def get_products_by_subcategory(self, subcategory_id):
        """Получить товары из подкатегории (пока просто по category, потом расширим)"""
        from models import products_manager
        # Пока фильтруем по основной категории
        # Позже можно добавить поле subcategory в products.json
        return [p for p in products_manager.products if p.category == subcategory_id]

categories_manager = CategoryManager()