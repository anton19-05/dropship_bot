# cart_utils.py
import os

def count_total_attributes(product) -> int:
    """Считает общее количество значимых атрибутов у товара"""
    total = 0
    main_attrs = product.get_main_attributes()
    extra_attrs = product.get_extra_attributes()

    for attr_key, attr_value in main_attrs.items():
        variants = attr_value.get('variants', {})
        if isinstance(variants, dict) and variants:
            total += 1
        elif isinstance(variants, list) and variants:
            total += 1

    for key, value in extra_attrs.items():
        if key in ["colors", "sizes"]:
            continue
        if isinstance(value, list) and value:
            total += 1
        elif isinstance(value, dict) and value:
            total += 1

    return total


def has_photos_for_variants(product) -> bool:
    """Проверяет, есть ли фото для вариантов"""
    photos = getattr(product, 'photos', {})
    if not isinstance(photos, dict):
        return False
    for path in photos.values():
        if path and os.path.exists(path):
            return True
    return False


def get_cart_display_mode(product) -> str:
    """
    Определяет режим отображения в корзине:
    - 'separate' → отдельные карточки (1–2 атрибута)
    - 'grouped'  → одна карточка со списком (3+ атрибутов)
    """
    total_attrs = count_total_attributes(product)
    
    if total_attrs <= 2:
        return 'separate'
    return 'grouped'


def should_show_separate_cards(product, variants_count: int) -> bool:
    """
    Определяет, нужно ли показывать отдельные карточки:
    - True  → отдельные карточки (есть фото И вариантов > 1)
    - False → одна карточка (нет фото или всего 1 вариант)
    """
    if variants_count <= 1:
        return False
    return has_photos_for_variants(product)


def format_variant_label(product, item) -> str:
    """Формирует строку с атрибутами для варианта (БЕЗ ДУБЛИРОВАНИЯ)"""
    parts = []

    # Получаем все главные атрибуты
    main_attrs = product.get_main_attributes()
    main_attr_keys = list(main_attrs.keys())
    
    # Получаем все обычные атрибуты
    extra_attrs = product.get_extra_attributes()
    extra_attr_keys = list(extra_attrs.keys())

    # ✅ Добавляем атрибуты из item, но без дублирования
    added_keys = set()

    for key, value in item.items():
        # Пропускаем служебные
        if key in ["product_code", "quantity", "name", "price", "item_key"]:
            continue
        
        # Пропускаем пустые значения
        if not value:
            continue
        
        # Проверяем, не добавлен ли уже этот атрибут (по смыслу)
        # Например, если есть "цвет" и "color" — это одно и то же
        normalized_key = key
        if key in ["color", "цвет"]:
            normalized_key = "цвет"
        
        if normalized_key in added_keys:
            continue
        
        # Добавляем атрибут
        display_name = key.capitalize()
        if key == "color":
            display_name = "Цвет"
        elif key == "цвет":
            display_name = "Цвет"
        elif key == "size":
            display_name = "Размер"
        elif key == "размер":
            display_name = "Размер"
        
        parts.append(f"{display_name}: {value}")
        added_keys.add(normalized_key)

    return " | ".join(parts) if parts else "Стандарт"


def get_photo_for_variant(product, item) -> str:
    """Возвращает фото для варианта (если есть)"""
    photos = getattr(product, 'photos', {})
    if not isinstance(photos, dict):
        return ""

    color = item.get('color') or item.get('цвет')
    if color and color in photos and photos[color] and os.path.exists(photos[color]):
        return photos[color]

    if hasattr(product, 'photo') and product.photo and os.path.exists(product.photo):
        return product.photo

    return ""