import json
import os
from models import products_manager


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