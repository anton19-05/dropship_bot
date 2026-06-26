# cart_utils.py
"""
Утилиты для корзины:
- Определение типа отображения
- Формирование текста для корзины
"""
import os


def has_photos_for_variants(product) -> bool:
    """
    Проверяет, есть ли у товара фото для разных вариантов.
    """
    photos = product.photos if hasattr(product, 'photos') else {}
    
    # Проверяем, есть ли хотя бы одно фото для какого-то варианта
    for color, photo_path in photos.items():
        if photo_path and os.path.exists(photo_path):
            return True
    
    return False


def get_cart_display_type(product) -> str:
    """
    Определяет тип отображения для товара в корзине.
    
    Returns:
        str: 'separate' — отдельные карточки для каждого варианта (если есть фото)
             'grouped' — одна карточка со списком вариантов (если фото нет)
    """
    # ✅ ЕСЛИ ЕСТЬ ФОТО ДЛЯ ВАРИАНТОВ — РАЗДЕЛЯЕМ
    if has_photos_for_variants(product):
        return 'separate'
    
    # ✅ ЕСЛИ ФОТО НЕТ — ГРУППИРУЕМ
    return 'grouped'


def format_variant_label(product, item) -> str:
    """
    Формирует строку с атрибутами для варианта товара.
    """
    attrs_parts = []
    
    # Цвет
    color = item.get("color")
    if color:
        attrs_parts.append(f"Цвет: {color}")
    
    # Размер
    size = item.get("size")
    if size:
        attrs_parts.append(f"Размер: {size}")
    
    # Главные атрибуты (кроме цвета)
    main_attrs = product.get_main_attributes()
    for attr_key in main_attrs.keys():
        if attr_key not in ["colors", "цвет", "color"]:
            attr_value = item.get(attr_key)
            if attr_value:
                display_key = attr_key.capitalize()
                attrs_parts.append(f"{display_key}: {attr_value}")
    
    # Дополнительные атрибуты (не главные)
    extra_attrs = product.get_extra_attributes()
    for key in extra_attrs.keys():
        if key not in ["colors", "sizes"]:
            value = item.get(key)
            if value:
                display_key = key.capitalize()
                attrs_parts.append(f"{display_key}: {value}")
    
    return " | ".join(attrs_parts) if attrs_parts else "Стандарт"


def get_photo_for_variant(product, item) -> str:
    """
    Находит фото для конкретного варианта товара.
    """
    # Ищем фото по цвету
    color = item.get("color")
    if color:
        photos = product.photos if hasattr(product, 'photos') else {}
        if isinstance(photos, dict) and color in photos:
            photo_path = photos[color]
            if photo_path and os.path.exists(photo_path):
                return photo_path
    
    # Ищем фото по другим атрибутам
    main_attrs = product.get_main_attributes()
    for attr_key in main_attrs.keys():
        attr_value = item.get(attr_key)
        if attr_value:
            photos = product.photos if hasattr(product, 'photos') else {}
            if isinstance(photos, dict) and attr_value in photos:
                photo_path = photos[attr_value]
                if photo_path and os.path.exists(photo_path):
                    return photo_path
    
    # Если не нашли — возвращаем основное фото
    if product.photo and os.path.exists(product.photo):
        return product.photo
    
    return ""