# debug.py - Система отладки бота

import logging
from datetime import datetime

# Настройка цветного вывода в терминале
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log(level, module, message, data=None):
    """Универсальная функция логирования"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    colors = {
        "INFO": Colors.GREEN,
        "DEBUG": Colors.CYAN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "SUCCESS": Colors.GREEN
    }
    
    color = colors.get(level, Colors.BLUE)
    
    print(f"{color}[{timestamp}] [{level}] [{module}] {message}{Colors.END}")
    
    if data:
        print(f"{Colors.CYAN}  └─ Данные: {data}{Colors.END}")

def info(module, message, data=None):
    log("INFO", module, message, data)

def debug(module, message, data=None):
    log("DEBUG", module, message, data)

def warning(module, message, data=None):
    log("WARNING", module, message, data)

def error(module, message, data=None):
    log("ERROR", module, message, data)

def success(module, message, data=None):
    log("SUCCESS", module, message, data)

def separator():
    print(f"{Colors.BLUE}{'='*50}{Colors.END}")

def print_state(module, user_id, context_data):
    """Печатает состояние пользователя для отладки"""
    print(f"{Colors.CYAN}[{module}] Состояние пользователя {user_id}:{Colors.END}")
    for key, value in context_data.items():
        if key.startswith("_"):
            continue
        print(f"  └─ {key}: {value}")
