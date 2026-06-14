import sqlite3
import json
import os

DB_PATH = "user_data.db"

def get_db():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создаёт таблицы при первом запуске"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            last_name TEXT,
            first_name TEXT,
            phone TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            postal_code TEXT,
            address TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица корзины
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carts (
            user_id INTEGER PRIMARY KEY,
            cart_data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица избранного
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER PRIMARY KEY,
            favorites_data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных SQLite инициализирована")

def save_cart(user_id: int, cart_data: dict):
    """Сохраняет корзину в SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO carts (user_id, cart_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, json.dumps(cart_data, ensure_ascii=False)))
        conn.commit()
        conn.close()
        print(f"✅ Корзина сохранена в SQLite: user_id={user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения корзины: {e}")
        return False

def load_cart(user_id: int):
    """Загружает корзину из SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT cart_data FROM carts WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return {}
    except Exception as e:
        print(f"Ошибка загрузки корзины: {e}")
        return {}

def save_user_profile(user_id: int, profile_data: dict):
    """Сохраняет профиль в SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, last_name, first_name, phone, country, region, city, postal_code, address, email, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id,
            profile_data.get('last_name', ''),
            profile_data.get('first_name', ''),
            profile_data.get('phone', ''),
            profile_data.get('country', ''),
            profile_data.get('region', ''),
            profile_data.get('city', ''),
            profile_data.get('postal_code', ''),
            profile_data.get('address', ''),
            profile_data.get('email', '')
        ))
        conn.commit()
        conn.close()
        print(f"✅ Профиль сохранён в SQLite: user_id={user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения профиля: {e}")
        return False

def load_user_profile(user_id: int):
    """Загружает профиль из SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {}
    except Exception as e:
        print(f"Ошибка загрузки профиля: {e}")
        return {}

def save_favorites(user_id: int, favorites_data: dict):
    """Сохраняет избранное в SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO favorites (user_id, favorites_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, json.dumps(favorites_data, ensure_ascii=False)))
        conn.commit()
        conn.close()
        print(f"✅ Избранное сохранено в SQLite: user_id={user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения избранного: {e}")
        return False

def load_favorites(user_id: int):
    """Загружает избранное из SQLite"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT favorites_data FROM favorites WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return {}
    except Exception as e:
        print(f"Ошибка загрузки избранного: {e}")
        return {}

def restore_all_user_data(application):
    """Восстанавливает все данные при запуске"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Восстанавливаем профили
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        for user in users:
            user_id = user['user_id']
            user_data = {k: user[k] for k in user.keys() if k not in ['user_id', 'created_at', 'updated_at']}
            application.user_data[f"user_data_{user_id}"] = user_data
        
        # Восстанавливаем корзины
        cursor.execute('SELECT user_id, cart_data FROM carts')
        carts = cursor.fetchall()
        for cart in carts:
            user_id = cart['user_id']
            application.user_data[f"cart_{user_id}"] = json.loads(cart['cart_data'])
        
        # Восстанавливаем избранное
        cursor.execute('SELECT user_id, favorites_data FROM favorites')
        favorites = cursor.fetchall()
        for fav in favorites:
            user_id = fav['user_id']
            application.user_data[f"favorites_{user_id}"] = json.loads(fav['favorites_data'])
        
        conn.close()
        print(f"✅ Восстановлено {len(users)} профилей, {len(carts)} корзин, {len(favorites)} избранных из SQLite")
    except Exception as e:
        print(f"Ошибка восстановления: {e}")

# Инициализируем базу данных при загрузке модуля
init_db()