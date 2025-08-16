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
    
    def __init__(self):
        """Инициализация Gemini клиента"""
        self.config = Config()
        self.error_handler = ErrorHandler()
        
        # Инициализируем Gemini
        api_key = self.config.get_gemini_api_key()
        genai.configure(api_key=api_key)
        
        # Google Cloud Vision API отключен - используем только Gemini Vision
        self.vision_client = None
        self.vision_api_key = None
        logger.info("✅ Google Cloud Vision API disabled - using Gemini Vision only")
        
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

        self.current_model_index = 0  # gemini-2.0-flash
    
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
        """Получить статус моделей"""
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
            'model_errors': 0
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
            
            # Простой fallback - переключаем модель и пробуем еще раз
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning("⚠️ Quota exceeded, switching model...")
                self._switch_to_next_model()
                # Рекурсивно пробуем с новой моделью
                async for chunk in self.generate_streaming_response(system_prompt, user_message, context, user_profile):
                    yield chunk
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
            
            # Простой fallback
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning("⚠️ Quota exceeded, switching model...")
                self._switch_to_next_model()
                return self.chat(message, user_profile, conversation_context, system_prompt)
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