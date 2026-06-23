# test_sheets.py
import os
import json
from google_sheets_storage import GoogleSheetsStorage

try:
    print("🔍 Подключаюсь к Google Sheets...")
    storage = GoogleSheetsStorage()
    
    print("📊 Получаю все товары...")
    products = storage.get_all_products()
    
    print(f"✅ Найдено товаров: {len(products)}")
    
    if products:
        print("\n📦 Первые 3 товара:")
        for p in products[:3]:
            print(f"  - {p.get('name', 'Без имени')} ({p.get('price', 0)} руб.)")
    else:
        print("❌ Товаров нет в таблице!")
        print("Проверьте, что таблица называется 'Товары для бота' и в ней есть данные")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()