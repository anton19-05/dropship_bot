import json
import os

DATA_FILE = "user_data.json"

def load_user_data():
    """Загружает все данные пользователей из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_data(data):
    """Сохраняет все данные пользователей в файл"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id, context):
    """Получает данные пользователя (из файла или context)"""
    # Загружаем из файла
    all_data = load_user_data()
    user_data = all_data.get(str(user_id), {})
    
    # Если есть новые данные в context, объединяем
    context_data = context.user_data.get(f"user_data_{user_id}", {})
    if context_data:
        user_data.update(context_data)
    
    return user_data

def save_user_data_sync(user_id, user_data, context):
    """Сохраняет данные пользователя и в context, и в файл"""
    # Сохраняем в context (для текущей сессии)
    context.user_data[f"user_data_{user_id}"] = user_data
    
    # Сохраняем в файл
    all_data = load_user_data()
    all_data[str(user_id)] = user_data
    save_user_data(all_data)