"""
Конфигурация системы
"""

import os
from typing import Dict, Any

class Config:
    """Класс для управления конфигурацией системы"""
    
    def __init__(self):
        """Инициализация конфигурации"""
        # Основные ключи Gemini для разных процессов
        self.gemini_api_key_chat = os.getenv('GEMINI_API_KEY_CHAT')
        self.gemini_api_key_background = os.getenv('GEMINI_API_KEY_BACKGROUND')
        self.gemini_api_key_additional = os.getenv('GEMINI_API_KEY_ADDITIONAL')
        self.gemini_api_key_vision = os.getenv('GOOGLE_CLOUD_VISION_API_KEY')  # Vision использует отдельный ключ
        
        # Fallback на старый ключ для совместимости
        self.gemini_api_key = self.gemini_api_key_chat or os.getenv('GEMINI_API_KEY')
        
        self.vision_api_key = os.getenv('GOOGLE_CLOUD_VISION_API_KEY')
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Валидация обязательных переменных
        # Не падаем без GEMINI_API_KEY: чат/LLM потребуют ключ, но системные пути (HomeTools) должны жить
        # if not self.gemini_api_key:
        #     raise ValueError("GEMINI_API_KEY не установлен в переменных окружения")
    
    def get_gemini_api_key(self, process_type: str = "chat") -> str:
        """Получить API ключ Gemini для конкретного процесса"""
        if process_type == "chat":
            return self.gemini_api_key_chat or self.gemini_api_key
        elif process_type == "background":
            return self.gemini_api_key_background or self.gemini_api_key
        elif process_type == "additional":
            return self.gemini_api_key_additional or self.gemini_api_key
        elif process_type == "vision":
            return self.gemini_api_key_vision or self.gemini_api_key
        else:
            return self.gemini_api_key
    
    def get_vision_api_key(self) -> str:
        """Получить API ключ Vision"""
        return self.vision_api_key
    
    def get_project_root(self) -> str:
        """Получить корневую директорию проекта"""
        return self.project_root
    
    def is_vision_configured(self) -> bool:
        """Проверить настройку Vision API"""
        return bool(self.vision_api_key) 