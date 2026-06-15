from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import json

# Создаём клиент Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_cart(user_id: int, cart_data: dict):
    """Сохраняет корзину в Supabase"""
    try:
        data = {
            "user_id": user_id,
            "cart_data": cart_data,
            "updated_at": "now()"
        }
        
        # Проверяем, есть ли уже запись
        existing = supabase.table("carts").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            result = supabase.table("carts").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Корзина обновлена в Supabase: user_id={user_id}")
        else:
            result = supabase.table("carts").insert(data).execute()
            print(f"➕ Корзина создана в Supabase: user_id={user_id}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения корзины в Supabase: {e}")
        return False


def load_cart(user_id: int):
    """Загружает корзину из Supabase"""
    try:
        result = supabase.table("carts").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0].get("cart_data", {})
        return {}
    except Exception as e:
        print(f"Ошибка загрузки корзины: {e}")
        return {}


def save_user_profile(user_id: int, profile_data: dict):
    """Сохраняет профиль в Supabase"""
    try:
        data = {
            "user_id": user_id,
            **profile_data,
            "updated_at": "now()"
        }
        
        existing = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            supabase.table("users").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Профиль обновлён: user_id={user_id}")
        else:
            data["created_at"] = "now()"
            supabase.table("users").insert(data).execute()
            print(f"➕ Профиль создан: user_id={user_id}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения профиля: {e}")
        return False


def load_user_profile(user_id: int):
    """Загружает профиль из Supabase"""
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"Ошибка загрузки профиля: {e}")
        return {}


def save_favorites(user_id: int, favorites_data: dict):
    """Сохраняет избранное в Supabase"""
    try:
        data = {
            "user_id": user_id,
            "favorites_data": favorites_data,
            "updated_at": "now()"
        }
        
        existing = supabase.table("favorites").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            supabase.table("favorites").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Избранное обновлено: user_id={user_id}")
        else:
            supabase.table("favorites").insert(data).execute()
            print(f"➕ Избранное создано: user_id={user_id}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения избранного: {e}")
        return False


def load_favorites(user_id: int):
    """Загружает избранное из Supabase"""
    try:
        result = supabase.table("favorites").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0].get("favorites_data", {})
        return {}
    except Exception as e:
        print(f"Ошибка загрузки избранного: {e}")
        return {}


def restore_all_user_data(application):
    """Восстанавливает все данные при запуске"""
    try:
        # Восстанавливаем корзины
        carts = supabase.table("carts").select("*").execute()
        for cart in carts.data:
            user_id = cart["user_id"]
            application.user_data[f"cart_{user_id}"] = cart["cart_data"]
        
        # Восстанавливаем профили
        users = supabase.table("users").select("*").execute()
        for user in users.data:
            user_id = user["user_id"]
            user_data = {k: v for k, v in user.items() if k not in ["user_id", "created_at", "updated_at"]}
            application.user_data[f"user_data_{user_id}"] = user_data
        
        # Восстанавливаем избранное
        favorites = supabase.table("favorites").select("*").execute()
        for fav in favorites.data:
            user_id = fav["user_id"]
            application.user_data[f"favorites_{user_id}"] = fav["favorites_data"].get(f"favorites_{user_id}", [])
        
        print(f"✅ Восстановлено {len(carts.data)} корзин из Supabase")
        print(f"✅ Восстановлено {len(users.data)} профилей из Supabase")
    except Exception as e:
        print(f"Ошибка восстановления из Supabase: {e}")