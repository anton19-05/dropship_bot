import json
import os


class CategoryManager:
    def __init__(self, json_path="data/categories.json"):
        self.categories = []
        self.categories_by_id = {}
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, json_path)
        print(f"🔍 Загрузка категорий из: {full_path}")
        self._load(full_path)

    def _load(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.categories = data.get("categories", [])
                for cat in self.categories:
                    self.categories_by_id[cat["id"]] = cat
            print(f"✅ Загружено {len(self.categories)} категорий")
        else:
            print(f"❌ Файл категорий не найден: {path}")

    def get_all(self):
        return sorted(self.categories, key=lambda x: x.get("order", 999))

    def get_by_id(self, cat_id):
        return self.categories_by_id.get(cat_id)

    def get_subcategories(self, cat_id):
        cat = self.get_by_id(cat_id)
        if cat:
            return sorted(cat.get("subcategories", []), key=lambda x: x.get("order", 999))
        return []

    def get_products_by_subcategory(self, subcategory_id):
        from models import products_manager
        result = [p for p in products_manager.products if p.category == subcategory_id]
        return result


# ✅ ЭТА СТРОКА ДОЛЖНА БЫТЬ!
categories_manager = CategoryManager()