import json
import os

# Путь к вашему файлу products.json
file_path = "data/products.json"
print(f"🔍 Проверяем файл: {file_path}")

# Проверяем, существует ли файл
if os.path.exists(file_path):
    print("✅ Файл найден. Читаем...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        products = data.get("products", [])
        print(f"✅ Всего товаров в файле: {len(products)}")
        
        # Проверяем несколько товаров
        for product in products[:3]:  # Проверим первые три
            product_id = product.get("id")
            attributes = product.get("attributes", {})
            
            print(f"\n--- Проверка товара: {product_id} ---")
            print(f"Атрибуты: {attributes}")
            
            # Ищем главный атрибут
            main_attr = None
            for key, value in attributes.items():
                if isinstance(value, dict) and value.get("type") == "main":
                    main_attr = key
                    variants = value.get("variants", {})
                    print(f"✅ Главный атрибут: '{main_attr}' с вариантами: {list(variants.keys())}")
                    break
            
            if not main_attr:
                print("❌ Главный атрибут не найден!")
else:
    print(f"❌ Файл НЕ НАЙДЕН по пути: {file_path}")