import json
from google_sheets_storage import GoogleSheetsStorage
import time

def migrate_products():
    """Переносит товары из products.json в Google Sheets"""
    
    # Загружаем JSON
    with open('data/products.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Извлекаем список товаров из ключа 'products'
    products = data.get('products', [])
    
    if not products:
        print("❌ Товары не найдены в файле")
        return
    
    print(f"📦 Найдено товаров: {len(products)}")
    
    # Подключаемся к Google Sheets
    storage = GoogleSheetsStorage()
    
    # Добавляем каждый товар
    for product in products:
        # Подготавливаем данные для таблицы
        row_data = {
            'id': product.get('id', f"prod_{int(time.time())}"),
            'code': product.get('code', ''),
            'name': product.get('name', ''),
            'category': product.get('category', ''),
            'price': product.get('price', 0),
            'old_price': product.get('old_price', 0),
            'description': product.get('description', ''),
            'photo_url': product.get('photo', ''),
            'photos': json.dumps(product.get('photos', {}), ensure_ascii=False),
            'rating': product.get('rating', 0),
            'orders': product.get('orders', 0),
            'attributes': json.dumps(product.get('attributes', {}), ensure_ascii=False)
        }
        
        storage.add_product(row_data)
        print(f"✅ Добавлен: {product.get('name', 'Без названия')}")

if __name__ == "__main__":
    print("🚀 Начинаем миграцию товаров в Google Sheets...")
    migrate_products()
    print("🎉 Миграция завершена!")