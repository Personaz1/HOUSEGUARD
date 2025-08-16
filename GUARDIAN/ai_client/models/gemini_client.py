"""
Gemini API клиент - УПРОЩЕННАЯ АРХИТЕКТУРА
"""

import os
import time
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime
import json

import google.generativeai as genai
from google.cloud import vision

from ..utils.config import Config
from ..utils.logger import Logger
from ..utils.error_handler import ErrorHandler

logger = Logger()

class GeminiClient:
    """Упрощенный класс для работы с Gemini API"""
    
    def __init__(self, process_type: str = "chat"):
        """Инициализация Gemini клиента"""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.process_type = process_type
        
        # Управление ключами и моделями
        self.available_keys = [
            self.config.get_gemini_api_key("chat"),
            self.config.get_gemini_api_key("background"), 
            self.config.get_gemini_api_key("additional")
        ]
        # Убираем дубликаты и None значения
        self.available_keys = list(set([k for k in self.available_keys if k]))
        
        self.current_key_index = 0
        self.current_model_index = 0
        
        # Инициализируем Gemini с первым ключом
        self._configure_gemini_with_current_key()
        
        # Google Cloud Vision API (опционально)
        self.vision_client = None
        self.vision_api_key = None
        
        # Проверяем доступность Google Cloud Vision API
        try:
            vision_api_key = self.config.get_vision_api_key()
            if vision_api_key:
                self.vision_api_key = vision_api_key
                logger.info("✅ Google Cloud Vision API enabled - available for deep analysis")
            else:
                logger.info("⚠️ Google Cloud Vision API key not configured - using Gemini Vision only")
        except Exception as e:
            logger.warning(f"⚠️ Google Cloud Vision API initialization failed: {e} - using Gemini Vision only")
        
        # Определяем доступные модели - приоритет быстрым и дешёвым по умолчанию
        self.models = [
            {'name': 'gemini-2.0-flash', 'quota': 200},         # DEFAULT
            {'name': 'gemini-2.5-flash', 'quota': 250},
            {'name': 'gemini-1.5-flash', 'quota': 500},
            {'name': 'gemini-2.0-flash-lite', 'quota': 1000},
            {'name': 'gemini-2.5-flash-lite', 'quota': 1000},
            {'name': 'gemini-2.5-pro', 'quota': 100},
            {'name': 'gemini-1.5-pro', 'quota': 150}
        ]

    def _configure_gemini_with_current_key(self):
        """Настроить Gemini с текущим ключом"""
        if self.available_keys:
            current_key = self.available_keys[self.current_key_index]
            genai.configure(api_key=current_key)
            logger.info(f"🔑 Configured Gemini with key {self.current_key_index + 1}/{len(self.available_keys)}")
        else:
            logger.error("❌ No available API keys!")
    
    def _switch_to_next_key(self):
        """Переключиться на следующий ключ"""
        if len(self.available_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.available_keys)
            self.current_model_index = 0  # Сбрасываем модель к лучшей
            self._configure_gemini_with_current_key()
            logger.info(f"🔑 Switched to API key {self.current_key_index + 1}/{len(self.available_keys)}")
            return True
        else:
            logger.warning("⚠️ Only one API key available - cannot switch")
            return False
    
    def _get_current_model(self):
        """Получить текущую модель"""
        return self.models[self.current_model_index]['name']
    
    def _switch_to_next_model(self):
        """Переключиться на следующую модель"""
        # Пропускаем модели с низким качеством если есть лучшие альтернативы
        current_quota = self.models[self.current_model_index]['quota']
        
        # Ищем следующую модель с похожим или лучшим качеством
        for i in range(1, len(self.models)):
            next_index = (self.current_model_index + i) % len(self.models)
            next_quota = self.models[next_index]['quota']
            
            # Если следующая модель имеет похожий или лучший лимит, используем её
            if next_quota >= current_quota * 0.5:  # Не падаем слишком сильно
                self.current_model_index = next_index
                model_name = self.models[self.current_model_index]['name']
                logger.info(f"🚀 Switched to model: {model_name} (quota: {next_quota})")
                return model_name
        
        # Если не нашли подходящую, просто переходим к следующей
        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        model_name = self.models[self.current_model_index]['name']
        logger.info(f"🚀 Using model: {model_name}")
        return model_name
    
    def _handle_quota_error(self):
        """Обработать ошибку квоты - сначала ключ, потом модель"""
        logger.warning("⚠️ Quota exceeded, switching...")
        
        # Сначала пробуем переключить ключ
        if self._switch_to_next_key():
            return True
        
        # Если ключи закончились, переключаем модель
        self._switch_to_next_model()
        return True
    
    def _parse_gemini_response(self, response) -> str:
        """УНИВЕРСАЛЬНЫЙ ПАРСЕР - обрабатывает любой формат ответа Gemini"""
        try:
            # Проверяем finish_reason
            if hasattr(response, 'finish_reason'):
                finish_reason = response.finish_reason
                if finish_reason == 1:  # SAFETY
                    logger.warning("⚠️ Gemini response blocked by safety - trying to extract partial content")
                    # Пытаемся извлечь частичный контент вместо полной блокировки
                elif finish_reason == 2:  # RECITATION
                    logger.warning("⚠️ Gemini response blocked by recitation")
                    return "❌ Ответ заблокирован из-за рецитации"
                elif finish_reason == 3:  # OTHER
                    logger.warning("⚠️ Gemini response blocked by other reasons")
                    return "❌ Ответ заблокирован по другим причинам"
                elif finish_reason == 12:  # SAFETY_BLOCK
                    logger.warning("⚠️ Gemini response blocked by safety block")
                    return "❌ Ответ заблокирован системой безопасности (SAFETY_BLOCK)"
            
            # Способ 1: прямой доступ к text
            if hasattr(response, 'text') and response.text:
                return response.text
            
            # Способ 2: через parts
            if hasattr(response, 'parts') and response.parts:
                text_parts = []
                for part in response.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return "".join(text_parts)
            
            # Способ 3: через candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            return "".join(text_parts)
                    elif hasattr(candidate.content, 'text') and candidate.content.text:
                        return candidate.content.text
            
            return "❌ Не удалось сгенерировать ответ"
            
        except Exception as e:
            logger.error(f"❌ Error parsing Gemini response: {e}")
            return f"❌ Error parsing response: {str(e)}"
    
    def switch_to_model(self, model_name: str) -> bool:
        """Переключиться на конкретную модель"""
        for i, model in enumerate(self.models):
            if model['name'] == model_name:
                self.current_model_index = i
                logger.info(f"🚀 Switched to model: {model_name}")
                return True
        logger.error(f"❌ Model {model_name} not found")
        return False
    
    def get_model_status(self) -> Dict[str, Any]:
        """Получить статус моделей и ключей"""
        current_model = self._get_current_model()
        
        available_models = []
        for i, model in enumerate(self.models):
            model_info = {
                'name': model['name'],
                'quota': model.get('quota', 'undefined'),
                'has_error': False
            }
            available_models.append(model_info)
        
        return {
            'current_model': current_model,
            'current_quota': "undefined",
            'model_index': self.current_model_index,
            'total_models': len(self.models),
            'available_models': available_models,
            'model_errors': 0,
            'current_key_index': self.current_key_index,
            'total_keys': len(self.available_keys),
            'keys_available': len(self.available_keys) > 0
        }
    
    def get_current_model(self) -> str:
        """Получить имя текущей модели"""
        return self._get_current_model()
    
    def _build_prompt(self, system_prompt: str, user_message: str, context: Optional[str] = None, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """Строим промпт с reasoning и chain of thoughts"""
        prompt_parts = []
        
        # System prompt
        prompt_parts.append(system_prompt)
        
        # Context if provided
        if context:
            prompt_parts.append(f"\n**CONTEXT:**\n{context}")
        
        # User profile if provided
        if user_profile:
            prompt_parts.append(f"\n**USER PROFILE:**\n{json.dumps(user_profile, indent=2)}")
        
        # User message
        prompt_parts.append(f"\n**USER MESSAGE:**\n{user_message}")
        

        
        return "\n".join(prompt_parts)
    
    async def generate_streaming_response(self, system_prompt: str, user_message: str, context: Optional[str] = None, user_profile: Optional[Dict[str, Any]] = None, image_path: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Streaming ответ - УПРОЩЕННАЯ ВЕРСИЯ с поддержкой изображений"""
        try:
            model_name = self._get_current_model()
            model = genai.GenerativeModel(model_name)
            
            full_prompt = self._build_prompt(system_prompt, user_message, context, user_profile)
            
            # Если есть изображение, добавляем его к промпту
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    # Определяем MIME тип
                    mime_type = "image/jpeg"  # По умолчанию
                    if image_path.lower().endswith('.png'):
                        mime_type = "image/png"
                    elif image_path.lower().endswith('.gif'):
                        mime_type = "image/gif"
                    elif image_path.lower().endswith('.webp'):
                        mime_type = "image/webp"
                    
                    # Создаем parts с изображением и текстом
                    parts = [
                        {"mime_type": mime_type, "data": image_data},
                        {"text": full_prompt}
                    ]
                    
                    response = model.generate_content(parts, stream=True)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load image {image_path}: {e}")
                    # Fallback к текстовому режиму
                    response = model.generate_content(full_prompt, stream=True)
            else:
                response = model.generate_content(full_prompt, stream=True)
            
            # Обрабатываем streaming ответ через универсальный парсер
            for chunk in response:
                # Используем универсальный парсер для каждого chunk
                chunk_text = self._parse_gemini_response(chunk)
                if chunk_text and not chunk_text.startswith("❌"):
                    yield chunk_text
                    
        except Exception as e:
            error_msg = str(e)
            # Сокращаем длинные ошибки
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            logger.error(f"❌ Gemini streaming error: {error_msg}")
            
            # Fallback с защитой от бесконечной рекурсии
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning("⚠️ Quota exceeded, switching...")
                self._handle_quota_error()
                # Пробуем еще раз с новыми настройками
                try:
                    model_name = self._get_current_model()
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(full_prompt)
                    result = self._parse_gemini_response(response)
                    yield result
                except Exception as retry_error:
                    logger.error(f"❌ Retry failed: {retry_error}")
                    yield f"❌ All API keys and models exhausted: {error_msg}"
            else:
                yield f"❌ Error: {error_msg}"
    
    def chat(self, message: str, user_profile: Optional[Dict[str, Any]] = None, conversation_context: Optional[str] = None, system_prompt: Optional[str] = None, image_path: Optional[str] = None) -> str:
        """Основной метод чата - УПРОЩЕННАЯ ВЕРСИЯ с поддержкой изображений"""
        try:
            if not system_prompt:
                system_prompt = "You are a helpful AI assistant."
            
            model_name = self._get_current_model()
            model = genai.GenerativeModel(model_name)
            
            full_prompt = self._build_prompt(system_prompt, message, conversation_context, user_profile)
            
            # Если есть изображение, добавляем его к промпту
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    # Определяем MIME тип
                    mime_type = "image/jpeg"  # По умолчанию
                    if image_path.lower().endswith('.png'):
                        mime_type = "image/png"
                    elif image_path.lower().endswith('.gif'):
                        mime_type = "image/gif"
                    elif image_path.lower().endswith('.webp'):
                        mime_type = "image/webp"
                    
                    # Создаем parts с изображением и текстом
                    parts = [
                        {"mime_type": mime_type, "data": image_data},
                        {"text": full_prompt}
                    ]
                    
                    response = model.generate_content(parts)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load image {image_path}: {e}")
                    # Fallback к текстовому режиму
                    response = model.generate_content(full_prompt)
            else:
                response = model.generate_content(full_prompt)
            
            return self._parse_gemini_response(response)
            
        except Exception as e:
            error_msg = str(e)
            # Сокращаем длинные ошибки
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            logger.error(f"❌ Chat error: {error_msg}")
            
            # Fallback с защитой от бесконечной рекурсии
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning("⚠️ Quota exceeded, switching...")
                self._handle_quota_error()
                # Пробуем еще раз с новыми настройками
                try:
                    model_name = self._get_current_model()
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(full_prompt)
                    return self._parse_gemini_response(response)
                except Exception as retry_error:
                    logger.error(f"❌ Retry failed: {retry_error}")
                    return f"❌ All API keys and models exhausted: {error_msg}"
            else:
                return f"❌ Error: {error_msg}"

    def analyze_image_with_files_api(
        self,
        image_path: str,
        prompt_text: str = "Describe the image",
        preferred_model: str = "gemini-1.5-pro"
    ) -> str:
        """
        Анализ изображения через официальную схему Files API + мультимодель Gemini.
        - По умолчанию использует "gemini-1.5-pro"; при 429 делает fallback на "gemini-1.5-flash".
        - Если загрузка через Files API не удалась, делает безопасный fallback на inline bytes.
        """
        try:
            if not os.path.exists(image_path):
                return f"❌ Image not found: {image_path}"

            # Определяем MIME
            mime_type = "image/jpeg"
            lp = image_path.lower()
            if lp.endswith(".png"):
                mime_type = "image/png"
            elif lp.endswith(".gif"):
                mime_type = "image/gif"
            elif lp.endswith(".webp"):
                mime_type = "image/webp"

            target_models = [preferred_model, "gemini-1.5-flash"]
            last_error: Optional[str] = None

            for model_name in target_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Шаг 1: upload через Files API
                    try:
                        uploaded = genai.upload_file(image_path, mime_type=mime_type)
                        parts = [
                            {"text": prompt_text},
                            {"file_data": {"file_uri": uploaded.uri, "mime_type": mime_type}}
                        ]
                        response = model.generate_content(parts)
                        return self._parse_gemini_response(response)
                    except Exception as upload_error:
                        # Fallback: inline bytes (на случай проблем Files API)
                        try:
                            with open(image_path, "rb") as f:
                                image_data = f.read()
                            parts = [
                                {"mime_type": mime_type, "data": image_data},
                                {"text": prompt_text}
                            ]
                            response = model.generate_content(parts)
                            return self._parse_gemini_response(response)
                        except Exception as inline_error:
                            last_error = f"Upload fail: {upload_error}; Inline fail: {inline_error}"
                            continue
                except Exception as e:
                    # Переключаем модель при квоте/ошибке
                    last_error = str(e)
                    continue

            return f"❌ Gemini Vision error: {last_error or 'unknown'}"
        except Exception as e:
            return f"❌ Gemini Vision error: {str(e)}"
    
    def _analyze_image_with_vision_api(self, image_path: str) -> str:
        """Анализ изображения через Vision API"""
        try:
            if not self.config.is_vision_configured():
                return "❌ Vision API not configured"
            
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            import requests
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.vision_api_key}"
            
            request_data = {
                "requests": [
                    {
                        "image": {"content": content.decode('latin1')},
                        "features": [
                            {"type": "LABEL_DETECTION", "maxResults": 10},
                            {"type": "TEXT_DETECTION"},
                            {"type": "FACE_DETECTION"},
                            {"type": "OBJECT_LOCALIZATION", "maxResults": 5}
                        ]
                    }
                ]
            }
            
            response = requests.post(url, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                analysis = []
                
                if 'labelAnnotations' in result['responses'][0]:
                    labels = [label['description'] for label in result['responses'][0]['labelAnnotations']]
                    analysis.append(f"Labels: {', '.join(labels)}")
                
                if 'textAnnotations' in result['responses'][0]:
                    text = result['responses'][0]['textAnnotations'][0]['description']
                    analysis.append(f"Text: {text}")
                
                if 'faceAnnotations' in result['responses'][0]:
                    faces = len(result['responses'][0]['faceAnnotations'])
                    analysis.append(f"Faces detected: {faces}")
                
                if 'localizedObjectAnnotations' in result['responses'][0]:
                    objects = [obj['name'] for obj in result['responses'][0]['localizedObjectAnnotations']]
                    analysis.append(f"Objects: {', '.join(objects)}")
                
                return " | ".join(analysis)
            else:
                return f"❌ Vision API error: {response.status_code}"
                
        except Exception as e:
            return f"❌ Vision API error: {str(e)}" 