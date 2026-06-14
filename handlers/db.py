from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_user_profile(user_id: int, profile_data: dict):
    """Сохраняет профиль пользователя в БД"""
    print(f"💾 save_user_profile ВЫЗВАНА: user_id={user_id}, profile_data={profile_data}")
    try:
        data = {
            "user_id": user_id,
            **profile_data,
            "updated_at": "now()"
        }
        
        existing = supabase.table("users").select("*").eq("user_id", user_id).execute()
        print(f"🔍 Существующий профиль: {existing.data}")
        
        if existing.data:
            result = supabase.table("users").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Обновлён профиль: {result.data}")
        else:
            data["created_at"] = "now()"
            result = supabase.table("users").insert(data).execute()
            print(f"➕ Создан новый профиль: {result.data}")
        
        print("✅ Профиль сохранён в Supabase")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения профиля: {e}")
        return False


def load_user_profile(user_id: int):
    """Загружает профиль пользователя из БД"""
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        print(f"Ошибка загрузки профиля: {e}")
        return {}


def save_cart(user_id: int, cart_data: dict):
    """Сохраняет корзину пользователя в БД"""
    print(f"💾 save_cart ВЫЗВАНА: user_id={user_id}, cart_data={cart_data}")
    try:
        data = {
            "user_id": user_id,
            "cart_data": cart_data,
            "updated_at": "now()"
        }
        
        # Проверяем, есть ли уже запись
        existing = supabase.table("carts").select("*").eq("user_id", user_id).execute()
        print(f"🔍 Существующая запись: {existing.data}")
        
        if existing.data:
            result = supabase.table("carts").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Обновлена существующая корзина: {result.data}")
        else:
            result = supabase.table("carts").insert(data).execute()
            print(f"➕ Создана новая корзина: {result.data}")
        
        print("✅ Корзина сохранена в Supabase")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения корзины: {e}")
        return False


def load_cart(user_id: int):
    """Загружает корзину пользователя из БД"""
    try:
        result = supabase.table("carts").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0].get("cart_data", {})
        return {}
    except Exception as e:
        print(f"Ошибка загрузки корзины: {e}")
        return {}


def save_favorites(user_id: int, favorites_data: dict):
    """Сохраняет избранное пользователя в БД"""
    print(f"💾 save_favorites ВЫЗВАНА: user_id={user_id}, favorites_data={favorites_data}")
    try:
        data = {
            "user_id": user_id,
            "favorites_data": favorites_data,
            "updated_at": "now()"
        }
        
        existing = supabase.table("favorites").select("*").eq("user_id", user_id).execute()
        print(f"🔍 Существующее избранное: {existing.data}")
        
        if existing.data:
            result = supabase.table("favorites").update(data).eq("user_id", user_id).execute()
            print(f"🔄 Обновлено избранное: {result.data}")
        else:
            result = supabase.table("favorites").insert(data).execute()
            print(f"➕ Создано новое избранное: {result.data}")
        
        print("✅ Избранное сохранено в Supabase")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения избранного: {e}")
        return False


def load_favorites(user_id: int):
    """Загружает избранное пользователя из БД"""
    try:
        result = supabase.table("favorites").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0].get("favorites_data", {})
        return {}
    except Exception as e:
        print(f"Ошибка загрузки избранного: {e}")
        return {}


def restore_all_user_data(application):
    """Восстанавливает данные всех пользователей при запуске"""
    try:
        users = supabase.table("users").select("*").execute()
        for user in users.data:
            user_id = user["user_id"]
            user_data = {k: v for k, v in user.items() if k not in ["user_id", "created_at", "updated_at"]}
            application.user_data[f"user_data_{user_id}"] = user_data
        
        carts = supabase.table("carts").select("*").execute()
        for cart in carts.data:
            user_id = cart["user_id"]
            application.user_data[f"cart_{user_id}"] = cart["cart_data"]
        
        favorites = supabase.table("favorites").select("*").execute()
        for fav in favorites.data:
            user_id = fav["user_id"]
            favorites_list = fav["favorites_data"].get(f"favorites_{user_id}", [])
            application.user_data[f"favorites_{user_id}"] = favorites_list
        
        print(f"✅ Восстановлено {len(users.data)} профилей из Supabase")
    except Exception as e:
        print(f"Ошибка восстановления из Supabase: {e}")