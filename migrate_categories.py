import json
from google_sheets_storage import GoogleSheetsStorage

def migrate_categories():
    """Переносит категории из categories.json в Google Sheets"""
    
    # Загружаем JSON
    with open('data/categories.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    categories = data.get('categories', [])
    
    if not categories:
        print("❌ Категории не найдены в файле")
        return
    
    print(f"📂 Найдено категорий: {len(categories)}")
    
    # Подключаемся к Google Sheets
    storage = GoogleSheetsStorage()
    
    # Получаем лист categories
    try:
        categories_sheet = storage.client.open('Товары для бота').worksheet('categories')
    except:
        # Если листа нет - создаем
        categories_sheet = storage.client.open('Товары для бота').add_worksheet(
            title='categories',
            rows=100,
            cols=10
        )
        # Добавляем заголовки
        categories_sheet.append_row(['id', 'name', 'order', 'subcategories'])
    
    # Добавляем каждую категорию
    for category in categories:
        row_data = [
            category.get('id', ''),
            category.get('name', ''),
            category.get('order', 0),
            json.dumps(category.get('subcategories', []), ensure_ascii=False)
        ]
        
        categories_sheet.append_row(row_data)
        print(f"✅ Добавлена категория: {category.get('name', 'Без названия')}")

if __name__ == "__main__":
    print("🚀 Начинаем миграцию категорий в Google Sheets...")
    migrate_categories()
    print("🎉 Миграция категорий завершена!")