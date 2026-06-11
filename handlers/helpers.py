"""Вспомогательные функции для работы с профилем и заказами"""

async def get_profile_data(user_id, context):
    """Вспомогательная функция для получения данных профиля"""
    return context.user_data.get(f"user_data_{user_id}", {})


async def is_profile_complete(user_id, context):
    """Проверяет, заполнен ли профиль полностью"""
    user_data = await get_profile_data(user_id, context)
    return all([
        user_data.get('last_name'),
        user_data.get('first_name'),
        user_data.get('phone'),
        user_data.get('country'),
        user_data.get('region'),
        user_data.get('city'),
        user_data.get('postal_code'),
        user_data.get('address'),
        user_data.get('email')
    ])