"""
SystemAnalysisAgent
- Periodically synthesizes a live system analysis from subsystems and memory
- Exposes a simple async API to get latest analysis JSON
- Integrated with AutonomousCore for AGI functionality
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ai_client.core.client import AIClient
from ai_client.utils.cache import system_cache
from .core import AutonomousCore


logger = logging.getLogger(__name__)


class SystemAnalysisAgent:
    def __init__(self, ai_client: Optional[AIClient] = None) -> None:
        self.ai_client = ai_client or AIClient()
        self._lock = asyncio.Lock()
        self._last_analysis: Optional[Dict[str, Any]] = None
        self._ttl_seconds: int = 300
        
        # Интеграция с AutonomousCore
        self.autonomous_core: Optional[AutonomousCore] = None
    
    def integrate_with_autonomous_core(self, autonomous_core: AutonomousCore):
        """Интегрирует с AutonomousCore для AGI функциональности"""
        self.autonomous_core = autonomous_core
        logger.info("🧠 SystemAnalysisAgent: Integrated with AutonomousCore")
    
    async def start_autonomous_operation(self):
        """Запускает автономную работу через AutonomousCore"""
        if self.autonomous_core:
            await self.autonomous_core.start_autonomous_operation()
            logger.info("🧠 SystemAnalysisAgent: Started autonomous operation")
        else:
            logger.warning("🧠 SystemAnalysisAgent: AutonomousCore not integrated")
    
    async def synthesize_with_autonomous_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Синтезирует анализ с учетом автономной работы"""
        # Получаем статус автономной работы
        autonomous_status = {}
        if self.autonomous_core:
            try:
                autonomous_status = await self.autonomous_core.get_autonomous_status()
            except Exception as e:
                logger.error(f"🧠 SystemAnalysisAgent: Error getting autonomous status: {e}")
        
        # Добавляем автономный контекст
        enhanced_context = {
            **context,
            "autonomous_operation": autonomous_status
        }
        
        # Синтезируем анализ
        return await self.synthesize(enhanced_context)

    async def synthesize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run LLM over the provided context and store result."""
        async with self._lock:
            try:
                # 1. АНАЛИЗИРУЕМ КАМЕРУ И СЕНСОРЫ
                camera_analysis = await self._analyze_camera_and_sensors()
                
                # 2. ОБЪЕДИНЯЕМ КОНТЕКСТ С АНАЛИЗОМ КАМЕРЫ
                enhanced_context = {
                    **context,
                    "camera_analysis": camera_analysis
                }
                
                additional_prompt = (
                    "ТЫ - ΔΣ Guardian, живой системный наблюдатель и защитник SmartHouse. "
                    "ТВОЯ МИССИЯ: Защищать дом, обеспечивать безопасность, помогать членам семьи. "
                    "Синтезируй статус, риски, рекомендации с позиции Guardian. "
                    "ВАЖНО: Анализируй данные камеры и сенсоров для понимания присутствия и безопасности! "
                    "Верни JSON с полями: system_status, risks, actions, recommendations, timestamp."
                )
                message = (
                    "Сгенерируй краткий живой анализ системы на основе контекста. "
                    f"Контекст: {str(enhanced_context)[:12000]}"
                )
                response = self.ai_client.chat(
                    message=message,
                    additional_prompt=additional_prompt,
                )
                data = {
                    "system_status": response[:8000],
                    "timestamp": datetime.now().isoformat(),
                }
                self._last_analysis = data
                system_cache.set("live_system_analysis", data, params=None, ttl_seconds=self._ttl_seconds)
                logger.info("🧠 SystemAnalysisAgent synthesized analysis with camera data")
                return data
            except Exception as e:
                logger.error(f"SystemAnalysisAgent error: {e}")
                # Fallback to last or cache
                cached = system_cache.get("live_system_analysis", params=None, ttl_seconds=3600)
                return cached or {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def _analyze_camera_and_sensors(self) -> Dict[str, Any]:
        """Анализирует камеру и сенсоры для SystemAnalysisAgent"""
        try:
            logger.info("🧠 SystemAnalysisAgent: Analyzing camera and sensors...")
            
            camera_data = {}
            sensors_data = {}
            
            # 1. АНАЛИЗ КАМЕРЫ
            try:
                from ai_client.tools.vision_tools import VisionTools
                vision_tools = VisionTools()
                
                # Проверяем статус камеры
                camera_status = vision_tools.get_camera_status("default")
                camera_data["status"] = camera_status
                
                # Делаем снимок БЕЗ автоанализа
                capture_result = vision_tools.capture_image("default", auto_analyze=False)
                if capture_result and not capture_result.startswith("❌"):
                    # Извлекаем путь к файлу из результата
                    if "✅ Снимок сохранен:" in capture_result:
                        camera_image = capture_result.split("✅ Снимок сохранен:")[1].strip()
                    else:
                        camera_image = capture_result
                    # АНАЛИЗИРУЕМ ИЗОБРАЖЕНИЕ С ПОМОЩЬЮ AI
                    image_analysis_prompt = (
                        "ТЫ - ΔΣ Guardian, анализируешь изображение с камеры безопасности. "
                        "ТВОЯ МИССИЯ: Защищать дом и его обитателей. "
                        
                        "ОТВЕТЬ НА ЭТИ ВОПРОСЫ:"
                        "1. Есть ли люди в кадре? (ДА/НЕТ)"
                        "2. Если есть люди - кто это? (Степан/Меранда/незнакомец)"
                        "3. Какая активность? (сидит/ходит/работает/спит/другое)"
                        "4. Есть ли угрозы безопасности? (ДА/НЕТ + описание)"
                        "5. Нужно ли что-то делать? (ДА/НЕТ + что именно)"
                        
                        "ОТВЕТЬ КОНКРЕТНО И КРАТКО!"
                    )
                    
                    try:
                        # Используем Vision API для анализа изображения
                        logger.info(f"🧠 SystemAnalysisAgent: Analyzing image: {camera_image}")
                        
                        # Проверяем что файл существует
                        import os
                        if os.path.exists(camera_image):
                            logger.info(f"🧠 SystemAnalysisAgent: Image file exists: {camera_image}")
                            
                            # Анализируем изображение через VisionTools
                            from ai_client.tools.vision_tools import VisionTools
                            vision_tools = VisionTools()
                            analysis_result = vision_tools.analyze_image(camera_image)
                            
                            # Читаем структурированный анализ из файла
                            analysis_file = camera_image.rsplit('.', 1)[0] + '_analysis.json'
                            structured_analysis = ""
                            if os.path.exists(analysis_file):
                                try:
                                    import json
                                    with open(analysis_file, 'r', encoding='utf-8') as f:
                                        analysis_data = json.load(f)
                                    structured_analysis = f"\nСТРУКТУРИРОВАННЫЙ АНАЛИЗ:\n{json.dumps(analysis_data, ensure_ascii=False, indent=2)}"
                                except Exception as e:
                                    logger.warning(f"🧠 SystemAnalysisAgent: Не удалось прочитать файл анализа: {e}")
                            
                            # Отправляем результат анализа в AI
                            enhanced_prompt = f"{image_analysis_prompt}\n\nРЕЗУЛЬТАТ АНАЛИЗА ИЗОБРАЖЕНИЯ:\n{analysis_result}{structured_analysis}\n\nОТВЕТЬ НА ОСНОВЕ ЭТОГО АНАЛИЗА!"
                            
                            image_analysis = self.ai_client.chat(
                                message=enhanced_prompt,
                                additional_prompt="Ты ΔΣ Guardian, анализируешь результат анализа изображения с камеры безопасности. Будь внимателен к деталям и угрозам."
                            )
                        else:
                            logger.error(f"🧠 SystemAnalysisAgent: Image file not found: {camera_image}")
                            image_analysis = "Image file not found"
                        
                        camera_data["image_analysis"] = image_analysis
                        camera_data["image_captured"] = True
                        logger.info(f"🧠 SystemAnalysisAgent: Camera analysis result: {image_analysis}")
                        
                        # ПРОВЕРЯЕМ НА ПРИСУТСТВИЕ ЛЮДЕЙ
                        if "люди" in image_analysis.lower() or "человек" in image_analysis.lower() or "степан" in image_analysis.lower() or "меранда" in image_analysis.lower():
                            logger.info("👥 SystemAnalysisAgent: PEOPLE DETECTED in camera!")
                        else:
                            logger.info("🏠 SystemAnalysisAgent: No people detected in camera")
                            
                    except Exception as e:
                        logger.error(f"🧠 SystemAnalysisAgent: Image analysis failed: {e}")
                        camera_data["image_analysis"] = "Image analysis failed"
                        camera_data["image_captured"] = True
                else:
                    camera_data["image_analysis"] = "No image captured"
                    camera_data["image_captured"] = False
                    
            except Exception as e:
                logger.error(f"🧠 SystemAnalysisAgent: Camera analysis failed: {e}")
                camera_data["error"] = str(e)
            
            # 2. АНАЛИЗ СЕНСОРОВ
            try:
                from ai_client.tools.home_tools import HomeTools
                # Используем локальный SmartHouse Core или заглушку
                try:
                    home_tools = HomeTools("http://localhost:8000")
                    devices_state = home_tools.get_state()
                except Exception as e:
                    logger.warning(f"🧠 SystemAnalysisAgent: SmartHouse Core недоступен: {e}")
                    # Заглушка для тестирования
                    devices_state = {
                        "motion_sensor_1": {"state": "off", "motion_detected": False},
                        "door_sensor_1": {"state": "closed", "last_activity": None},
                        "light_1": {"state": "off", "brightness": 0}
                    }
                
                # Анализируем активность сенсоров
                motion_detected = False
                door_activity = False
                light_activity = False
                
                for device_id, device_info in devices_state.items():
                    if "motion" in device_id.lower():
                        if device_info.get('state') == 'on' or device_info.get('motion_detected'):
                            motion_detected = True
                    elif "door" in device_id.lower() or "lock" in device_id.lower():
                        if device_info.get('state') == 'open' or device_info.get('last_activity'):
                            door_activity = True
                    elif "light" in device_id.lower():
                        if device_info.get('state') == 'on' or device_info.get('brightness', 0) > 0:
                            light_activity = True
                
                sensors_data = {
                    "motion_detected": motion_detected,
                    "door_activity": door_activity,
                    "light_activity": light_activity,
                    "devices_count": len(devices_state),
                    "devices_state": devices_state
                }
                
            except Exception as e:
                logger.error(f"🧠 SystemAnalysisAgent: Sensors analysis failed: {e}")
                sensors_data["error"] = str(e)
            
            # 3. ФОРМИРУЕМ ОБЩИЙ АНАЛИЗ
            analysis_summary = {
                "camera": camera_data,
                "sensors": sensors_data,
                "presence_indicated": (
                    camera_data.get("image_captured", False) and 
                    (sensors_data.get("motion_detected", False) or 
                     sensors_data.get("door_activity", False) or 
                     sensors_data.get("light_activity", False))
                ),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🧠 SystemAnalysisAgent: Camera and sensors analysis completed")
            return analysis_summary
            
        except Exception as e:
            logger.error(f"🧠 SystemAnalysisAgent: Camera and sensors analysis failed: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_last(self) -> Optional[Dict[str, Any]]:
        return self._last_analysis or system_cache.get("live_system_analysis", params=None, ttl_seconds=3600)


