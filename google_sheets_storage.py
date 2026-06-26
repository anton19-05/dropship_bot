import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GoogleSheetsStorage:
    """Класс для работы с товарами через Google Sheets"""
    
    def __init__(self, creds_file: str = 'creds.json', sheet_name: str = None):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Пробуем взять из переменной окружения (для Render)
            creds_json_str = os.environ.get('GOOGLE_CREDS_JSON')
            if creds_json_str:
                logger.info("🔑 Использую учетные данные из переменной окружения")
                creds_dict = json.loads(creds_json_str)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            else:
                # Пробуем из файла (для локальной разработки)
                logger.info(f"🔑 Использую учетные данные из файла {creds_file}")
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
            
            self.client = gspread.authorize(creds)
            
            # Название таблицы
            sheet_name = os.environ.get('GOOGLE_SHEET_NAME', 'Товары для бота')
            self.sheet = self.client.open(sheet_name).sheet1
            
            logger.info("✅ Подключение к Google Sheets установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
            raise
    
    # В google_sheets_storage.py

    def get_all_products(self) -> List[Dict]:
        try:
            all_values = self.sheet.get_all_values()
        
            if not all_values or len(all_values) < 2:
                logger.warning("⚠️ Таблица пуста или нет данных")
                return []
        
            headers = all_values[0]
            unique_headers = []
            seen = {}
        
            for header in headers:
                if header in seen:
                    seen[header] += 1
                    unique_headers.append(f"{header}_{seen[header]}")
                else:
                    seen[header] = 1
                    unique_headers.append(header)
        
            logger.info(f"📋 Заголовки: {unique_headers}")
        
            products = []
            for row in all_values[1:]:
                if not row or not row[0]:
                    continue
            
                product = {}
                for i, header in enumerate(unique_headers):
                    if i < len(row):
                        value = row[i]
                    
                        if header in ['price', 'old_price', 'orders']:
                            try:
                                value = int(float(value)) if value else 0
                            except:
                                value = 0
                        elif header == 'rating':
                            try:
                                value = float(value) if value else 0
                            except:
                                value = 0
                        elif header in ['attributes', 'photos', 'colors_reviews', 'colors_reviews_text']:
                            try:
                                value = json.loads(value) if value else {}
                            except:
                                value = {}
                    
                        # ✅ МАППИНГ ДЛЯ ФОТО
                        if header == 'photo_url':
                            product['photo'] = value
                        elif header == 'photo':
                            product['photo'] = value
                        elif header == 'photos':
                            product['photos'] = value  # ← ЭТО ВАЖНО!
                        else:
                            product[header] = value
            
                # Добавляем недостающие поля
                if 'photo' not in product:
                    product['photo'] = ''
                if 'photos' not in product:
                    product['photos'] = {}
                if 'attributes' not in product:
                    product['attributes'] = {}
            
                products.append(product)
        
            logger.info(f"📦 Загружено {len(products)} товаров из Google Sheets")
            return products
        
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки товаров: {e}")
            return []
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Получает товар по ID"""
        products = self.get_all_products()
        for product in products:
            if product.get('id') == product_id:
                return product
        return None
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """Получает товары по категории"""
        products = self.get_all_products()
        return [p for p in products if p.get('category', '').lower() == category.lower()]
    
    def add_product(self, product_data: Dict) -> bool:
        """Добавляет новый товар в таблицу"""
        try:
            all_values = self.sheet.get_all_values()
            headers = all_values[0] if all_values else []
            
            if not headers:
                # Создаем заголовки если их нет
                headers = ['id', 'code', 'name', 'category', 'price', 'old_price', 
                          'description', 'photo_url', 'photos', 'rating', 'orders', 'attributes']
                self.sheet.append_row(headers)
            
            # Формируем новую строку
            new_row = []
            for header in headers:
                if header == 'attributes' and 'attributes' in product_data:
                    new_row.append(json.dumps(product_data['attributes'], ensure_ascii=False))
                elif header == 'photos' and 'photos' in product_data:
                    new_row.append(json.dumps(product_data['photos'], ensure_ascii=False))
                elif header == 'photo_url':
                    new_row.append(str(product_data.get('photo', '')))
                else:
                    new_row.append(str(product_data.get(header, '')))
            
            self.sheet.append_row(new_row)
            logger.info(f"✅ Товар '{product_data.get('name')}' добавлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления товара: {e}")
            return False
    
    def update_product(self, product_id: str, updates: Dict) -> bool:
        """Обновляет товар по ID"""
        try:
            records = self.get_all_products()
            all_values = self.sheet.get_all_values()
            headers = all_values[0] if all_values else []
            
            for i, record in enumerate(records, start=2):
                if record.get('id') == product_id:
                    for key, value in updates.items():
                        if key in headers:
                            col_index = headers.index(key) + 1
                            if key in ['attributes', 'photos']:
                                value = json.dumps(value, ensure_ascii=False)
                            self.sheet.update_cell(i, col_index, str(value))
                    
                    logger.info(f"✅ Товар '{product_id}' обновлен")
                    return True
            
            logger.warning(f"⚠️ Товар с ID {product_id} не найден")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления товара: {e}")
            return False
    
    def delete_product(self, product_id: str) -> bool:
        """Удаляет товар по ID"""
        try:
            records = self.get_all_products()
            
            for i, record in enumerate(records, start=2):
                if record.get('id') == product_id:
                    self.sheet.delete_rows(i)
                    logger.info(f"✅ Товар '{product_id}' удален")
                    return True
            
            logger.warning(f"⚠️ Товар с ID {product_id} не найден")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления товара: {e}")
            return False
    
    def get_categories(self) -> List[Dict]:
        """Получает все категории из листа 'categories'"""
        try:
            try:
                categories_sheet = self.client.open('Товары для бота').worksheet('categories')
            except:
                return []
            
            records = categories_sheet.get_all_records()
            
            categories = []
            for row in records:
                if not row.get('id'):
                    continue
                
                subcategories = []
                if row.get('subcategories'):
                    try:
                        subcategories = json.loads(row['subcategories'])
                    except:
                        subcategories = []
                
                categories.append({
                    'id': row.get('id', ''),
                    'name': row.get('name', ''),
                    'order': int(row.get('order', 0)) if row.get('order') else 0,
                    'subcategories': subcategories
                })
            
            return categories
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки категорий: {e}")
            return []
    
    def get_category_by_id(self, category_id: str) -> Optional[Dict]:
        """Получает категорию по ID"""
        categories = self.get_categories()
        for category in categories:
            if category.get('id') == category_id:
                return category
        return None

# Создаем глобальный экземпляр
storage = GoogleSheetsStorage()