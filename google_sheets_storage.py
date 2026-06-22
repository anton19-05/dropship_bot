import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GoogleSheetsStorage:
    """Класс для работы с товарами через Google Sheets"""
    
    def __init__(self, creds_file: str = 'creds.json', sheet_name: str = None):
        """
        Инициализация подключения к Google Sheets
        
        Args:
            creds_file: путь к файлу с учетными данными
            sheet_name: название листа (если None - берет первый)
        """
        try:
            # Настройка доступа
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
            self.client = gspread.authorize(creds)
            
            # Ищем таблицу по названию
            # ВАЖНО: замените "Товары для бота" на название вашей таблицы
            self.sheet = self.client.open('Товары для бота').sheet1
            
            logger.info("✅ Подключение к Google Sheets установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
            raise
    
    def get_all_products(self) -> List[Dict]:
        """
        Получает все товары из таблицы
        
        Returns:
            List[Dict]: список товаров с ключами из заголовков
        """
        try:
            # Получаем все записи
            records = self.sheet.get_all_records()
            
            # Преобразуем данные
            products = []
            for row in records:
                # Пропускаем пустые строки
                if not row.get('name'):
                    continue
                
                # Парсим атрибуты (если есть)
                attributes = {}
                if row.get('attributes'):
                    try:
                        attributes = json.loads(row['attributes'])
                    except:
                        attributes = {}
                
                # Парсим фото (если есть несколько)
                photos = {}
                if row.get('photos'):
                    try:
                        photos = json.loads(row['photos'])
                    except:
                        photos = {}
                
                product = {
                    'id': row.get('id', ''),
                    'code': row.get('code', ''),
                    'name': row.get('name', ''),
                    'category': row.get('category', ''),
                    'price': int(row.get('price', 0)) if row.get('price') else 0,
                    'old_price': int(row.get('old_price', 0)) if row.get('old_price') else 0,
                    'description': row.get('description', ''),
                    'photo': row.get('photo_url', ''),
                    'photos': photos,
                    'rating': float(row.get('rating', 0)) if row.get('rating') else 0,
                    'orders': int(row.get('orders', 0)) if row.get('orders') else 0,
                    'attributes': attributes
                }
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
            if product['id'] == product_id:
                return product
        return None
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """Получает товары по категории"""
        products = self.get_all_products()
        return [p for p in products if p['category'].lower() == category.lower()]
    
    def add_product(self, product_data: Dict) -> bool:
        """
        Добавляет новый товар в таблицу
        
        Args:
            product_data: словарь с данными товара
        """
        try:
            # Получаем все строки
            all_values = self.sheet.get_all_values()
            headers = all_values[0]  # Заголовки
            
            # Формируем новую строку
            new_row = []
            for header in headers:
                if header == 'attributes' and 'attributes' in product_data:
                    new_row.append(json.dumps(product_data['attributes'], ensure_ascii=False))
                elif header == 'photos' and 'photos' in product_data:
                    new_row.append(json.dumps(product_data['photos'], ensure_ascii=False))
                else:
                    new_row.append(str(product_data.get(header, '')))
            
            # Добавляем строку
            self.sheet.append_row(new_row)
            logger.info(f"✅ Товар '{product_data.get('name')}' добавлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления товара: {e}")
            return False
    
    def update_product(self, product_id: str, updates: Dict) -> bool:
        """
        Обновляет товар по ID
        
        Args:
            product_id: ID товара
            updates: словарь с полями для обновления
        """
        try:
            # Находим строку с товаром
            records = self.sheet.get_all_records()
            
            for i, record in enumerate(records, start=2):  # +2 потому что заголовок на 1 строке
                if record.get('id') == product_id:
                    # Обновляем нужные поля
                    for key, value in updates.items():
                        if key == 'attributes':
                            value = json.dumps(value, ensure_ascii=False)
                        self.sheet.update_cell(i, self._get_column_index(key), value)
                    
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
            records = self.sheet.get_all_records()
            
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
        """
        Получает все категории из листа 'categories'
        """
        try:
            # Пытаемся получить лист categories
            try:
                categories_sheet = self.client.open('Товары для бота').worksheet('categories')
            except:
                # Если нет листа categories - возвращаем пустой список
                return []
            
            records = categories_sheet.get_all_records()
            
            categories = []
            for row in records:
                if not row.get('id'):
                    continue
                
                # Парсим subcategories
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
            if category['id'] == category_id:
                return category
        return None
    
    def _get_column_index(self, column_name: str) -> int:
        """Получает индекс колонки по названию"""
        headers = self.sheet.row_values(1)
        try:
            return headers.index(column_name) + 1
        except ValueError:
            return 1

# Создаем глобальный экземпляр
storage = GoogleSheetsStorage()