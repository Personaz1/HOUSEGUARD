"""
ΔΣ Guardian - Автономное ядро
Новая архитектура: "Спящий Guardian" с простыми инструментами и триггерами
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Any

from ..core.client import AIClient
from ..utils.cache import system_cache

logger = logging.getLogger(__name__)

@dataclass
class TriggerEvent:
    """Событие-триггер для пробуждения Guardian"""
    type: str  # 'motion', 'person_detected', 'anomaly', 'system_alert'
    source: str  # 'camera', 'sensors', 'logs', 'system'
    data: Dict[str, Any]
    timestamp: float
    priority: int = 1  # 1-5, где 5 - критично

@dataclass
class ObservationResult:
    """Результат наблюдения"""
    success: bool
    data: Dict[str, Any]
    triggers: List[TriggerEvent]
    next_check_delay: int  # секунды до следующей проверки

class AutonomousCore:
    """
    Спящий Guardian - простая и эффективная архитектура
    
    Принципы:
    1. Спит 10 минут между проверками
    2. Использует простые инструменты наблюдения
    3. Реагирует только на триггеры
    4. Доводит задачи до результата
    """
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.running = False
        self.background_loop = None
        
        # Простые инструменты наблюдения
        self.observation_tools = {
            'camera': self._observe_camera,
            'sensors': self._observe_sensors, 
            'logs': self._observe_logs,
            'system': self._observe_system
        }
        
        # Триггеры для пробуждения
        self.active_triggers: List[TriggerEvent] = []
        
        # Настройки сна
        self.base_sleep_time = 600  # 10 минут
        self.min_sleep_time = 60    # 1 минута минимум
        self.max_sleep_time = 1800  # 30 минут максимум
        
        # Статистика
        self._total_observations = 0
        self._total_triggers = 0
        self._last_work_time = time.time()
        
        logger.info("🧠 AutonomousCore: Initialized (Sleeping Guardian Architecture)")

    async def start_autonomous_operation(self):
        """Запускает спящий Guardian"""
        if self.running:
            logger.warning("🧠 AutonomousCore: Already running")
            return
        
        self.running = True
        self.background_loop = asyncio.create_task(self._sleeping_guardian_loop())
        logger.info("🧠 AutonomousCore: Started sleeping guardian operation")

    async def stop_autonomous_operation(self):
        """Останавливает Guardian"""
        self.running = False
        
        if self.background_loop:
            self.background_loop.cancel()
            try:
                await self.background_loop
            except asyncio.CancelledError:
                pass
        
        logger.info("🧠 AutonomousCore: Stopped")

    async def _sleeping_guardian_loop(self):
        """Основной цикл спящего Guardian"""
        logger.info("🧠 AutonomousCore: Entering sleep cycle")
        
        while self.running:
            try:
                # 1. Проводим наблюдения
                triggers = await self._conduct_observations()
                
                # 2. Обрабатываем триггеры
                if triggers:
                    await self._handle_triggers(triggers)
                    sleep_time = self.min_sleep_time  # Короткий сон после триггеров
                else:
                    sleep_time = self.base_sleep_time  # Обычный сон
                
                # 3. Спим
                logger.info(f"🧠 AutonomousCore: Sleeping for {sleep_time}s")
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info("🧠 AutonomousCore: Sleep cycle cancelled")
                break
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in sleep cycle: {e}")
                await asyncio.sleep(60)  # Короткий сон при ошибке

    async def _conduct_observations(self) -> List[TriggerEvent]:
        """Проводит все наблюдения и собирает триггеры"""
        all_triggers = []
        
        for tool_name, tool_func in self.observation_tools.items():
            try:
                result = await tool_func()
                if result.triggers:
                    all_triggers.extend(result.triggers)
                    logger.info(f"🧠 AutonomousCore: {tool_name} detected {len(result.triggers)} triggers")
                
                self._total_observations += 1
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in {tool_name} observation: {e}")
        
        return all_triggers

    async def _observe_camera(self) -> ObservationResult:
        """Наблюдение за камерой - простой инструмент"""
        try:
            # Получаем снимок камеры
            from ..tools.vision_tools import VisionTools
            vision = VisionTools(self.ai_client)
            
            # Анализируем изображение на предмет людей/движения
            analysis = await vision.analyze_image("camera_snapshot")
            
            triggers = []
            
            # Проверяем на триггеры
            if "person" in analysis.lower() or "человек" in analysis.lower():
                triggers.append(TriggerEvent(
                    type="person_detected",
                    source="camera",
                    data={"analysis": analysis},
                    timestamp=time.time(),
                    priority=3
                ))
            
            if "motion" in analysis.lower() or "движение" in analysis.lower():
                triggers.append(TriggerEvent(
                    type="motion",
                    source="camera", 
                    data={"analysis": analysis},
                    timestamp=time.time(),
                    priority=2
                ))
            
            return ObservationResult(
                success=True,
                data={"analysis": analysis},
                triggers=triggers,
                next_check_delay=300  # 5 минут
            )
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Camera observation error: {e}")
            return ObservationResult(
                success=False,
                data={"error": str(e)},
                triggers=[],
                next_check_delay=60
            )

    async def _observe_sensors(self) -> ObservationResult:
        """Наблюдение за сенсорами"""
        try:
            from ..tools.home_tools import HomeTools
            home = HomeTools()
            
            # Получаем данные сенсоров
            sensor_data = home.get_sensor_data()
            
            triggers = []
            
            # Проверяем на аномалии
            if sensor_data.get("temperature", 0) > 30:  # Высокая температура
                triggers.append(TriggerEvent(
                    type="anomaly",
                    source="sensors",
                    data={"type": "high_temperature", "value": sensor_data["temperature"]},
                    timestamp=time.time(),
                    priority=4
                ))
            
            if sensor_data.get("motion", False):  # Движение
                triggers.append(TriggerEvent(
                    type="motion",
                    source="sensors",
                    data=sensor_data,
                    timestamp=time.time(),
                    priority=2
                ))
            
            return ObservationResult(
                success=True,
                data=sensor_data,
                triggers=triggers,
                next_check_delay=180  # 3 минуты
            )
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Sensor observation error: {e}")
            return ObservationResult(
                success=False,
                data={"error": str(e)},
                triggers=[],
                next_check_delay=60
            )

    async def _observe_logs(self) -> ObservationResult:
        """Наблюдение за логами системы"""
        try:
            # Читаем последние логи
            log_data = self._read_recent_logs()
            
            triggers = []
            
            # Ищем ошибки и предупреждения
            for log_entry in log_data:
                if "ERROR" in log_entry or "CRITICAL" in log_entry:
                    triggers.append(TriggerEvent(
                        type="system_alert",
                        source="logs",
                        data={"log_entry": log_entry},
                        timestamp=time.time(),
                        priority=5
                    ))
                    break  # Одна критическая ошибка достаточно
            
            return ObservationResult(
                success=True,
                data={"logs": log_data},
                triggers=triggers,
                next_check_delay=600  # 10 минут
            )
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Log observation error: {e}")
            return ObservationResult(
                success=False,
                data={"error": str(e)},
                triggers=[],
                next_check_delay=300
            )

    async def _observe_system(self) -> ObservationResult:
        """Наблюдение за состоянием системы"""
        try:
            import psutil
            
            system_data = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
            
            triggers = []
            
            # Проверяем на перегрузку
            if system_data["cpu_percent"] > 80:
                triggers.append(TriggerEvent(
                    type="system_alert",
                    source="system",
                    data={"type": "high_cpu", "value": system_data["cpu_percent"]},
                    timestamp=time.time(),
                    priority=3
                ))
            
            if system_data["memory_percent"] > 90:
                triggers.append(TriggerEvent(
                    type="system_alert", 
                    source="system",
                    data={"type": "high_memory", "value": system_data["memory_percent"]},
                    timestamp=time.time(),
                    priority=4
                ))
            
            return ObservationResult(
                success=True,
                data=system_data,
                triggers=triggers,
                next_check_delay=900  # 15 минут
            )
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: System observation error: {e}")
            return ObservationResult(
                success=False,
                data={"error": str(e)},
                triggers=[],
                next_check_delay=600
            )

    async def _handle_triggers(self, triggers: List[TriggerEvent]):
        """Обрабатывает триггеры и доводит до результата"""
        logger.info(f"🧠 AutonomousCore: Handling {len(triggers)} triggers")
        
        for trigger in triggers:
            try:
                # Доводим каждый триггер до результата
                result = await self._resolve_trigger(trigger)
                logger.info(f"🧠 AutonomousCore: Trigger {trigger.type} resolved: {result}")
                
                self._total_triggers += 1
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error handling trigger {trigger.type}: {e}")

    async def _resolve_trigger(self, trigger: TriggerEvent) -> str:
        """Доводит триггер до результата - как у меня чтение лога"""
        
        if trigger.type == "person_detected":
            return await self._handle_person_detected(trigger)
        elif trigger.type == "motion":
            return await self._handle_motion(trigger)
        elif trigger.type == "anomaly":
            return await self._handle_anomaly(trigger)
        elif trigger.type == "system_alert":
            return await self._handle_system_alert(trigger)
        else:
            return f"Unknown trigger type: {trigger.type}"

    async def _handle_person_detected(self, trigger: TriggerEvent) -> str:
        """Обработка обнаружения человека"""
        prompt = f"""
        ΔΣ Guardian: Обнаружен человек на камере!
        
        Данные: {trigger.data}
        
        Что нужно сделать:
        1. Определить кто это (Stepan, Meranda, посторонний)
        2. Оценить безопасность
        3. Принять решение (приветствовать, предупредить, вызвать помощь)
        
        Действуй как Guardian - защитник дома.
        """
        
        response = self.ai_client.chat(prompt)
        logger.info(f"🧠 AutonomousCore: Person detected response: {response}")
        
        return f"Person detected handled: {response}"

    async def _handle_motion(self, trigger: TriggerEvent) -> str:
        """Обработка движения"""
        prompt = f"""
        ΔΣ Guardian: Обнаружено движение!
        
        Источник: {trigger.source}
        Данные: {trigger.data}
        
        Оцени ситуацию и прими решение.
        """
        
        response = self.ai_client.chat(prompt)
        return f"Motion handled: {response}"

    async def _handle_anomaly(self, trigger: TriggerEvent) -> str:
        """Обработка аномалии"""
        prompt = f"""
        ΔΣ Guardian: Обнаружена аномалия!
        
        Тип: {trigger.data.get('type', 'unknown')}
        Значение: {trigger.data.get('value', 'unknown')}
        
        Прими меры для устранения аномалии.
        """
        
        response = self.ai_client.chat(prompt)
        return f"Anomaly handled: {response}"

    async def _handle_system_alert(self, trigger: TriggerEvent) -> str:
        """Обработка системного предупреждения"""
        prompt = f"""
        ΔΣ Guardian: Системное предупреждение!
        
        Тип: {trigger.data.get('type', 'unknown')}
        Значение: {trigger.data.get('value', 'unknown')}
        
        Прими меры для стабилизации системы.
        """
        
        response = self.ai_client.chat(prompt)
        return f"System alert handled: {response}"

    def _read_recent_logs(self) -> List[str]:
        """Читает последние логи системы"""
        try:
            # Читаем последние 50 строк лога
            with open("app.log", "r") as f:
                lines = f.readlines()
                return lines[-50:] if len(lines) > 50 else lines
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error reading logs: {e}")
            return []

    def get_current_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус Guardian"""
        return {
            "status": "sleeping" if self.running else "stopped",
            "total_observations": self._total_observations,
            "total_triggers": self._total_triggers,
            "active_triggers": len(self.active_triggers),
            "last_work_time": self._last_work_time,
            "architecture": "sleeping_guardian"
        }
