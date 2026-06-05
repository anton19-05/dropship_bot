# payments.py - Работа с платежами ЮMoney

import uuid
from datetime import datetime
from products_config import YOOMONEY_WALLET

def create_payment_link(amount, description, order_id):
    """Создать ссылку на оплату через ЮMoney (без API)"""
    # Простая ссылка на оплату через форму ЮMoney
    # Пользователь сам вводит сумму и переводит
    wallet = YOOMONEY_WALLET
    comment = f"Заказ {order_id}"
    
    # Ссылка на оплату с предзаполненными данными
    payment_url = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={wallet}&quickpay-form=small&targets={description}&sum={amount}&paymentType=SB&comment={comment}"
    
    return payment_url

def get_wallet_number():
    """Получить номер кошелька для ручного перевода"""
    return YOOMONEY_WALLET
