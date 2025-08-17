"""
ΔΣ Guardian - Автономное ядро
Гибридная архитектура: "Спящий Guardian" + Осознанные миссии + React + Планирование
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
    type: str  # 'motion', 'person_detected', 'anomaly', 'system_alert', 'mission_trigger'
    source: str  # 'camera', 'sensors', 'logs', 'system', 'user_command'
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

@dataclass
class Mission:
    """Осознанная миссия Guardian"""
    id: str
    name: str
    description: str
    type: str  # 'security', 'comfort', 'maintenance', 'assistance'
    priority: int
    status: str  # 'active', 'paused', 'completed', 'failed'
    created_at: float
    last_execution: float = 0
    execution_count: int = 0
    context: Dict[str, Any] = None

@dataclass
class MissionPlan:
    """План выполнения миссии"""
    mission_id: str
    steps: List[Dict[str, Any]]
    current_step: int = 0
    status: str = 'planning'  # 'planning', 'executing', 'completed', 'failed'
    created_at: float = 0

class AutonomousCore:
    """
    Гибридный Guardian - спящий режим + осознанные миссии + React + планирование
    
    Принципы:
    1. Спит 10 минут между проверками (основной режим)
    2. Использует простые инструменты наблюдения
    3. Реагирует на триггеры
    4. Выполняет осознанные миссии по команде/событиям
    5. Использует React для выполнения кода
    6. Планирует и доводит до результата
    7. Параллельные процессы не мешают чату
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
        
        # Осознанные миссии
        self.missions: Dict[str, Mission] = {}
        self.active_missions: Dict[str, Mission] = {}
        self.mission_plans: Dict[str, MissionPlan] = {}
        
        # React инструменты
        self.react_tools = {
            'execute_code': self._execute_code,
            'analyze_files': self._analyze_files,
            'system_commands': self._system_commands,
            'file_operations': self._file_operations
        }
        
        # Триггеры для пробуждения
        self.active_triggers: List[TriggerEvent] = []
        
        # Система пробуждения и контекстов
        self.current_mode = "sleeping"  # sleeping, awake, mission, analysis, assistance
        self.wake_up_triggers = {
            "user_command": self._wake_up_on_user_command,
            "emergency": self._wake_up_on_emergency,
            "scheduled": self._wake_up_on_schedule,
            "mission_request": self._wake_up_on_mission
        }
        self.context_handlers = {
            "analysis": self._enter_analysis_context,
            "assistance": self._enter_assistance_context,
            "security": self._enter_security_context,
            "maintenance": self._enter_maintenance_context
        }
        
        # Настройки сна
        self.base_sleep_time = 600  # 10 минут
        self.min_sleep_time = 60    # 1 минута минимум
        self.max_sleep_time = 1800  # 30 минут максимум
        
        # Параллельные процессы
        self.parallel_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        
        # Статистика
        self._total_observations = 0
        self._total_triggers = 0
        self._total_missions = 0
        self._last_work_time = time.time()
        
        # Инициализируем базовые миссии
        self._initialize_missions()
        
        logger.info("🧠 AutonomousCore: Initialized (Hybrid Guardian Architecture)")

    def _initialize_missions(self):
        """Инициализирует базовые осознанные миссии"""
        base_missions = [
            Mission(
                id="security_protection",
                name="Защита дома",
                description="Защищать дом и жильцов от угроз 24/7",
                type="security",
                priority=5,
                status="active",
                created_at=time.time()
            ),
            Mission(
                id="comfort_optimization", 
                name="Оптимизация комфорта",
                description="Обеспечивать комфорт и удобство жильцов",
                type="comfort",
                priority=3,
                status="active",
                created_at=time.time()
            ),
            Mission(
                id="system_maintenance",
                name="Обслуживание системы",
                description="Поддерживать стабильную работу системы",
                type="maintenance", 
                priority=2,
                status="active",
                created_at=time.time()
            ),
            Mission(
                id="user_assistance",
                name="Помощь пользователю",
                description="Помогать Stepan в повседневных задачах",
                type="assistance",
                priority=4,
                status="active",
                created_at=time.time()
            )
        ]
        
        for mission in base_missions:
            self.missions[mission.id] = mission
            self.active_missions[mission.id] = mission
        
        logger.info(f"🧠 AutonomousCore: Initialized {len(base_missions)} missions")

    async def start_autonomous_operation(self):
        """Запускает гибридный Guardian"""
        if self.running:
            logger.warning("🧠 AutonomousCore: Already running")
            return
        
        self.running = True
        self.background_loop = asyncio.create_task(self._hybrid_guardian_loop())
        logger.info("🧠 AutonomousCore: Started hybrid guardian operation")

    async def stop_autonomous_operation(self):
        """Останавливает Guardian"""
        self.running = False
        
        if self.background_loop:
            self.background_loop.cancel()
            try:
                await self.background_loop
            except asyncio.CancelledError:
                pass
        
        # Отменяем все параллельные задачи
        for task_id, task in self.parallel_tasks.items():
            task.cancel()
        
        self.parallel_tasks.clear()
        logger.info("🧠 AutonomousCore: Stopped")

    async def _hybrid_guardian_loop(self):
        """Основной цикл гибридного Guardian с системой пробуждения"""
        logger.info("🧠 AutonomousCore: Entering hybrid sleep cycle")
        
        while self.running:
            try:
                # 1. Проверяем главные триггеры пробуждения
                wake_up_trigger = await self._check_wake_up_triggers()
                
                if wake_up_trigger:
                    # ПРОБУЖДЕНИЕ - выходим из спящего режима
                    await self._handle_wake_up(wake_up_trigger)
                    sleep_time = self.min_sleep_time  # Короткий сон после пробуждения
                else:
                    # Обычный цикл наблюдения
                    triggers = await self._conduct_observations()
                    mission_triggers = await self._check_missions()
                    triggers.extend(mission_triggers)
                    
                    if triggers:
                        await self._handle_triggers(triggers)
                        sleep_time = self.min_sleep_time
                    else:
                        sleep_time = self.base_sleep_time
                
                # Спим
                logger.info(f"🧠 AutonomousCore: Sleeping for {sleep_time}s (mode: {self.current_mode})")
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info("🧠 AutonomousCore: Hybrid cycle cancelled")
                break
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in hybrid cycle: {e}")
                await asyncio.sleep(60)

    async def _check_missions(self) -> List[TriggerEvent]:
        """Проверяет миссии на выполнение"""
        mission_triggers = []
        
        for mission_id, mission in self.active_missions.items():
            if mission.status != "active":
                continue
                
            # Проверяем условия выполнения миссии
            should_execute = await self._should_execute_mission(mission)
            
            if should_execute:
                mission_triggers.append(TriggerEvent(
                    type="mission_trigger",
                    source="mission_system",
                    data={"mission_id": mission_id, "mission": asdict(mission)},
                    timestamp=time.time(),
                    priority=mission.priority
                ))
        
        return mission_triggers

    async def _should_execute_mission(self, mission: Mission) -> bool:
        """Определяет нужно ли выполнять миссию"""
        current_time = time.time()
        
        # Базовые условия выполнения
        if mission.type == "security":
            # Безопасность - каждые 30 минут
            return (current_time - mission.last_execution) > 1800
        elif mission.type == "comfort":
            # Комфорт - каждые 2 часа
            return (current_time - mission.last_execution) > 7200
        elif mission.type == "maintenance":
            # Обслуживание - каждые 6 часов
            return (current_time - mission.last_execution) > 21600
        elif mission.type == "assistance":
            # Помощь - каждые 4 часа
            return (current_time - mission.last_execution) > 14400
        
        return False

    async def _handle_triggers(self, triggers: List[TriggerEvent]):
        """Обрабатывает триггеры и доводит до результата"""
        logger.info(f"🧠 AutonomousCore: Handling {len(triggers)} triggers")
        
        for trigger in triggers:
            try:
                if trigger.type == "mission_trigger":
                    # Запускаем миссию в параллельном процессе
                    await self._execute_mission_parallel(trigger)
                else:
                    # Обычные триггеры обрабатываем синхронно
                    result = await self._resolve_trigger(trigger)
                    logger.info(f"🧠 AutonomousCore: Trigger {trigger.type} resolved: {result}")
                
                self._total_triggers += 1
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error handling trigger {trigger.type}: {e}")

    async def _execute_mission_parallel(self, trigger: TriggerEvent):
        """Выполняет миссию в параллельном процессе"""
        mission_id = trigger.data.get("mission_id")
        mission = self.active_missions.get(mission_id)
        
        if not mission:
            return
        
        # Создаем параллельную задачу
        task = asyncio.create_task(self._execute_mission_with_planning(mission))
        self.parallel_tasks[mission_id] = task
        
        logger.info(f"🧠 AutonomousCore: Started parallel mission {mission.name}")

    async def _execute_mission_with_planning(self, mission: Mission):
        """Выполняет миссию с планированием и доведением до результата"""
        try:
            logger.info(f"🧠 AutonomousCore: Executing mission {mission.name}")
            
            # 1. ПЛАНИРОВАНИЕ
            plan = await self._plan_mission_execution(mission)
            self.mission_plans[mission.id] = plan
            
            # 2. ВЫПОЛНЕНИЕ ПЛАНА
            result = await self._execute_mission_plan(plan)
            
            # 3. ДОВЕДЕНИЕ ДО РЕЗУЛЬТАТА
            final_result = await self._complete_mission(mission, result)
            
            # Обновляем статистику
            mission.last_execution = time.time()
            mission.execution_count += 1
            
            # Сохраняем результат
            self.task_results[mission.id] = final_result
            
            logger.info(f"🧠 AutonomousCore: Mission {mission.name} completed: {final_result}")
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Mission {mission.name} failed: {e}")
            mission.status = "failed"
        finally:
            # Удаляем задачу из параллельных
            if mission.id in self.parallel_tasks:
                del self.parallel_tasks[mission.id]

    async def _plan_mission_execution(self, mission: Mission) -> MissionPlan:
        """Планирует выполнение миссии"""
        planning_prompt = f"""
        ΔΣ Guardian: Планирование миссии
        
        Миссия: {mission.name}
        Описание: {mission.description}
        Тип: {mission.type}
        Приоритет: {mission.priority}
        
        Создай план выполнения этой миссии. План должен включать:
        1. Анализ текущей ситуации
        2. Конкретные шаги для выполнения
        3. Критерии успеха
        4. Возможные проблемы и решения
        
        Используй доступные инструменты:
        - React: execute_code, analyze_files, system_commands, file_operations
        - Наблюдение: camera, sensors, logs, system
        
        Верни JSON план:
        {{"steps": [
            {{"action": "описание действия", "tool": "инструмент", "parameters": {{}}, "expected_result": "ожидаемый результат"}},
            {{"action": "следующее действие", "tool": "инструмент", "parameters": {{}}, "expected_result": "ожидаемый результат"}}
        ]}}
        """
        
        response = self.ai_client.chat(planning_prompt)
        
        try:
            # Парсим JSON план
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                plan_data = json.loads(json_str)
                
                plan = MissionPlan(
                    mission_id=mission.id,
                    steps=plan_data.get("steps", []),
                    created_at=time.time()
                )
                
                logger.info(f"🧠 AutonomousCore: Created plan for mission {mission.name} with {len(plan.steps)} steps")
                return plan
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Failed to parse mission plan: {e}")
        
        # Fallback план
        return MissionPlan(
            mission_id=mission.id,
            steps=[{"action": "Basic mission execution", "tool": "none", "parameters": {}, "expected_result": "Mission completed"}],
            created_at=time.time()
        )

    async def _execute_mission_plan(self, plan: MissionPlan) -> Dict[str, Any]:
        """Выполняет план миссии"""
        results = []
        
        for i, step in enumerate(plan.steps):
            try:
                plan.current_step = i
                plan.status = "executing"
                
                action = step.get("action", "")
                tool = step.get("tool", "")
                parameters = step.get("parameters", {})
                
                logger.info(f"🧠 AutonomousCore: Executing step {i+1}: {action}")
                
                # Выполняем действие
                if tool in self.react_tools:
                    result = await self.react_tools[tool](**parameters)
                else:
                    result = f"Tool {tool} not available"
                
                results.append({
                    "step": i,
                    "action": action,
                    "result": result,
                    "success": "error" not in str(result).lower()
                })
                
                # Проверяем ожидаемый результат
                expected = step.get("expected_result", "")
                if expected and expected.lower() in str(result).lower():
                    logger.info(f"🧠 AutonomousCore: Step {i+1} achieved expected result")
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Step {i+1} failed: {e}")
                results.append({
                    "step": i,
                    "action": action,
                    "result": f"Error: {str(e)}",
                    "success": False
                })
        
        plan.status = "completed"
        return {"steps": results, "total_steps": len(plan.steps)}

    async def _complete_mission(self, mission: Mission, execution_result: Dict[str, Any]) -> str:
        """Доводит миссию до результата"""
        completion_prompt = f"""
        ΔΣ Guardian: Завершение миссии
        
        Миссия: {mission.name}
        Описание: {mission.description}
        Результаты выполнения: {execution_result}
        
        Проанализируй результаты выполнения миссии:
        1. Что было выполнено успешно?
        2. Какие проблемы возникли?
        3. Достигнута ли цель миссии?
        4. Какие выводы и рекомендации?
        
        Дай итоговую оценку выполнения миссии.
        """
        
        response = self.ai_client.chat(completion_prompt)
        return f"Mission {mission.name} completed: {response}"

    # React инструменты
    async def _execute_code(self, code: str = "", file_path: str = "") -> str:
        """Выполняет код через React"""
        try:
            if file_path:
                with open(file_path, 'r') as f:
                    code = f.read()
            
            # Здесь можно добавить безопасное выполнение кода
            # Пока возвращаем заглушку
            return f"Code execution simulated: {len(code)} characters"
        except Exception as e:
            return f"Code execution error: {str(e)}"

    async def _analyze_files(self, path: str = ".", pattern: str = "*.py") -> str:
        """Анализирует файлы"""
        try:
            import os
            import glob
            
            files = glob.glob(os.path.join(path, pattern))
            analysis = f"Found {len(files)} files matching {pattern}"
            
            if files:
                analysis += f"\nFiles: {', '.join(files[:5])}"
            
            return analysis
        except Exception as e:
            return f"File analysis error: {str(e)}"

    async def _system_commands(self, command: str = "") -> str:
        """Выполняет системные команды"""
        try:
            import subprocess
            
            if not command:
                return "No command specified"
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return f"Command: {command}\nOutput: {result.stdout}\nError: {result.stderr}"
        except Exception as e:
            return f"System command error: {str(e)}"

    async def _file_operations(self, operation: str = "list", path: str = ".") -> str:
        """Операции с файлами"""
        try:
            import os
            
            if operation == "list":
                files = os.listdir(path)
                return f"Files in {path}: {', '.join(files[:10])}"
            elif operation == "size":
                size = os.path.getsize(path)
                return f"Size of {path}: {size} bytes"
            else:
                return f"Unknown operation: {operation}"
        except Exception as e:
            return f"File operation error: {str(e)}"

    # Существующие методы наблюдения (без изменений)
    async def _conduct_observations(self) -> List[TriggerEvent]:
        """Проводит все наблюдения и собирает триггеры - БЕЗ ТАЙМАУТОВ"""
        all_triggers = []
        
        for tool_name, tool_func in self.observation_tools.items():
            try:
                # БЕЗ ТАЙМАУТОВ - каждая утилита может работать сколько угодно
                result = await tool_func()
                if result.triggers:
                    all_triggers.extend(result.triggers)
                    logger.info(f"🧠 AutonomousCore: {tool_name} detected {len(result.triggers)} triggers")
                
                self._total_observations += 1
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in {tool_name} observation: {e}")
        
        return all_triggers

    async def _observe_camera(self) -> ObservationResult:
        """Наблюдение за камерой - простой инструмент без ограничений времени"""
        try:
            # Получаем снимок камеры
            from ..tools.vision_tools import VisionTools
            vision = VisionTools(self.ai_client)
            
            # Анализируем изображение на предмет людей/движения - БЕЗ ТАЙМАУТА
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
        """Наблюдение за сенсорами - без ограничений времени"""
        try:
            from ..tools.home_tools import HomeTools
            home = HomeTools()
            
            # Получаем данные сенсоров - БЕЗ ТАЙМАУТА
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
        """Наблюдение за логами системы - без ограничений времени"""
        try:
            # Читаем последние логи - БЕЗ ТАЙМАУТА
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
        """Наблюдение за состоянием системы - без ограничений времени"""
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

    async def _resolve_trigger(self, trigger: TriggerEvent) -> str:
        """Доводит триггер до результата - БЕЗ ТАЙМАУТОВ, как у меня чтение лога"""
        
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
        """Обработка обнаружения человека - БЕЗ ТАЙМАУТА"""
        prompt = f"""
        ΔΣ Guardian: Обнаружен человек на камере!
        
        Данные: {trigger.data}
        
        Что нужно сделать:
        1. Определить кто это (Stepan, Meranda, посторонний)
        2. Оценить безопасность
        3. Принять решение (приветствовать, предупредить, вызвать помощь)
        
        Действуй как Guardian - защитник дома.
        """
        
        # БЕЗ ТАЙМАУТА - может думать сколько угодно
        response = self.ai_client.chat(prompt)
        logger.info(f"🧠 AutonomousCore: Person detected response: {response}")
        
        return f"Person detected handled: {response}"

    async def _handle_motion(self, trigger: TriggerEvent) -> str:
        """Обработка движения - БЕЗ ТАЙМАУТА"""
        prompt = f"""
        ΔΣ Guardian: Обнаружено движение!
        
        Источник: {trigger.source}
        Данные: {trigger.data}
        
        Оцени ситуацию и прими решение.
        """
        
        # БЕЗ ТАЙМАУТА
        response = self.ai_client.chat(prompt)
        return f"Motion handled: {response}"

    async def _handle_anomaly(self, trigger: TriggerEvent) -> str:
        """Обработка аномалии - БЕЗ ТАЙМАУТА"""
        prompt = f"""
        ΔΣ Guardian: Обнаружена аномалия!
        
        Тип: {trigger.data.get('type', 'unknown')}
        Значение: {trigger.data.get('value', 'unknown')}
        
        Прими меры для устранения аномалии.
        """
        
        # БЕЗ ТАЙМАУТА
        response = self.ai_client.chat(prompt)
        return f"Anomaly handled: {response}"

    async def _handle_system_alert(self, trigger: TriggerEvent) -> str:
        """Обработка системного предупреждения - БЕЗ ТАЙМАУТА"""
        prompt = f"""
        ΔΣ Guardian: Системное предупреждение!
        
        Тип: {trigger.data.get('type', 'unknown')}
        Значение: {trigger.data.get('value', 'unknown')}
        
        Прими меры для стабилизации системы.
        """
        
        # БЕЗ ТАЙМАУТА
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

    # Методы управления миссиями
    async def start_mission(self, mission_id: str) -> bool:
        """Запускает миссию по команде"""
        mission = self.missions.get(mission_id)
        if not mission:
            return False
        
        # Создаем триггер для запуска миссии
        trigger = TriggerEvent(
            type="mission_trigger",
            source="user_command",
            data={"mission_id": mission_id, "mission": asdict(mission)},
            timestamp=time.time(),
            priority=mission.priority
        )
        
        # Запускаем миссию в параллельном процессе
        await self._execute_mission_parallel(trigger)
        return True

    async def stop_mission(self, mission_id: str) -> bool:
        """Останавливает миссию"""
        if mission_id in self.parallel_tasks:
            task = self.parallel_tasks[mission_id]
            task.cancel()
            del self.parallel_tasks[mission_id]
            return True
        return False

    def get_mission_status(self, mission_id: str) -> Dict[str, Any]:
        """Возвращает статус миссии"""
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": "Mission not found"}
        
        result = self.task_results.get(mission_id)
        plan = self.mission_plans.get(mission_id)
        
        return {
            "mission": asdict(mission),
            "result": result,
            "plan": asdict(plan) if plan else None,
            "is_running": mission_id in self.parallel_tasks
        }

    def get_current_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус Guardian"""
        return {
            "status": "sleeping" if self.running else "stopped",
            "total_observations": self._total_observations,
            "total_triggers": self._total_triggers,
            "total_missions": self._total_missions,
            "active_triggers": len(self.active_triggers),
            "active_missions": len(self.active_missions),
            "parallel_tasks": len(self.parallel_tasks),
            "last_work_time": self._last_work_time,
            "architecture": "hybrid_guardian"
        }

    async def _check_wake_up_triggers(self) -> Optional[TriggerEvent]:
        """Проверяет главные триггеры пробуждения"""
        # Здесь можно добавить проверку различных источников пробуждения
        # Например, проверка команд пользователя, критических событий и т.д.
        
        # Пока возвращаем None - нет пробуждения
        return None

    async def _handle_wake_up(self, trigger: TriggerEvent):
        """Обрабатывает пробуждение Guardian"""
        logger.info(f"🧠 AutonomousCore: Waking up on trigger: {trigger.type}")
        
        try:
            # 1. АНАЛИЗ ТРИГГЕРА ПРОБУЖДЕНИЯ
            wake_up_analysis = await self._analyze_wake_up_trigger(trigger)
            
            # 2. ОПРЕДЕЛЕНИЕ КОНТЕКСТА
            context = await self._determine_context(wake_up_analysis)
            
            # 3. ПЕРЕКЛЮЧЕНИЕ В НУЖНЫЙ КОНТЕКСТ
            await self._switch_context(context)
            
            # 4. ВЫПОЛНЕНИЕ ДЕЙСТВИЙ В КОНТЕКСТЕ
            result = await self._execute_context_actions(context, trigger)
            
            # 5. ВОЗВРАТ В СПЯЩИЙ РЕЖИМ (если нужно)
            await self._return_to_sleep_if_needed(result)
            
            logger.info(f"🧠 AutonomousCore: Wake-up cycle completed: {result}")
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error in wake-up cycle: {e}")
            self.current_mode = "sleeping"  # Возвращаемся в спящий режим

    async def _analyze_wake_up_trigger(self, trigger: TriggerEvent) -> Dict[str, Any]:
        """Анализирует триггер пробуждения"""
        analysis_prompt = f"""
        ΔΣ Guardian: Анализ триггера пробуждения
        
        Триггер: {trigger.type}
        Источник: {trigger.source}
        Данные: {trigger.data}
        Приоритет: {trigger.priority}
        
        Проанализируй этот триггер пробуждения:
        1. Что требует моего внимания?
        2. Какой тип задачи нужно выполнить?
        3. Какие ресурсы и инструменты потребуются?
        4. Какой уровень срочности?
        5. Нужно ли планирование или немедленные действия?
        
        Верни JSON анализ:
        {{"task_type": "analysis/assistance/security/maintenance", "urgency": "low/medium/high/critical", "required_tools": ["tool1", "tool2"], "planning_needed": true/false, "context": "описание контекста"}}
        """
        
        response = self.ai_client.chat(analysis_prompt)
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Failed to parse wake-up analysis: {e}")
        
        # Fallback анализ
        return {
            "task_type": "general",
            "urgency": "medium",
            "required_tools": [],
            "planning_needed": False,
            "context": "General wake-up trigger"
        }

    async def _determine_context(self, analysis: Dict[str, Any]) -> str:
        """Определяет нужный контекст на основе анализа"""
        task_type = analysis.get("task_type", "general")
        
        context_mapping = {
            "analysis": "analysis",
            "assistance": "assistance", 
            "security": "security",
            "maintenance": "maintenance"
        }
        
        return context_mapping.get(task_type, "assistance")

    async def _switch_context(self, context: str):
        """Переключает Guardian в нужный контекст"""
        logger.info(f"🧠 AutonomousCore: Switching to context: {context}")
        
        if context in self.context_handlers:
            await self.context_handlers[context]()
        
        self.current_mode = context

    async def _enter_analysis_context(self):
        """Входит в контекст анализа"""
        context_prompt = """
        ΔΣ Guardian: Контекст анализа
        
        Я переключаюсь в режим глубокого анализа системы.
        
        В этом контексте я:
        - Анализирую данные и логи
        - Ищу паттерны и аномалии
        - Выполняю диагностику
        - Генерирую отчеты и рекомендации
        
        Доступные инструменты:
        - analyze_files: анализ файлов
        - system_commands: системные команды
        - file_operations: операции с файлами
        - execute_code: выполнение кода
        
        Готов к аналитическим задачам.
        """
        
        # Обновляем промпт для анализа
        self.analysis_context_prompt = context_prompt
        logger.info("🧠 AutonomousCore: Entered analysis context")

    async def _enter_assistance_context(self):
        """Входит в контекст помощи пользователю"""
        context_prompt = """
        ΔΣ Guardian: Контекст помощи пользователю
        
        Я переключаюсь в режим активной помощи Stepan.
        
        В этом контексте я:
        - Отвечаю на вопросы и запросы
        - Выполняю задачи пользователя
        - Предоставляю информацию и рекомендации
        - Помогаю с повседневными задачами
        
        Доступные инструменты:
        - Все React инструменты
        - Все инструменты наблюдения
        - Все миссии и планирование
        
        Готов помогать пользователю.
        """
        
        # Обновляем промпт для помощи
        self.assistance_context_prompt = context_prompt
        logger.info("🧠 AutonomousCore: Entered assistance context")

    async def _enter_security_context(self):
        """Входит в контекст безопасности"""
        context_prompt = """
        ΔΣ Guardian: Контекст безопасности
        
        Я переключаюсь в режим активной защиты дома.
        
        В этом контексте я:
        - Мониторю безопасность в реальном времени
        - Анализирую угрозы и риски
        - Принимаю меры защиты
        - Координирую действия безопасности
        
        Доступные инструменты:
        - camera: наблюдение за камерой
        - sensors: мониторинг сенсоров
        - system_commands: системные команды
        - execute_code: выполнение кода безопасности
        
        Готов защищать дом и жильцов.
        """
        
        # Обновляем промпт для безопасности
        self.security_context_prompt = context_prompt
        logger.info("🧠 AutonomousCore: Entered security context")

    async def _enter_maintenance_context(self):
        """Входит в контекст обслуживания"""
        context_prompt = """
        ΔΣ Guardian: Контекст обслуживания системы
        
        Я переключаюсь в режим технического обслуживания.
        
        В этом контексте я:
        - Проверяю здоровье системы
        - Оптимизирую производительность
        - Исправляю проблемы
        - Обновляю компоненты
        
        Доступные инструменты:
        - system_commands: системные команды
        - analyze_files: анализ файлов
        - file_operations: операции с файлами
        - execute_code: выполнение кода обслуживания
        
        Готов обслуживать систему.
        """
        
        # Обновляем промпт для обслуживания
        self.maintenance_context_prompt = context_prompt
        logger.info("🧠 AutonomousCore: Entered maintenance context")

    async def _execute_context_actions(self, context: str, trigger: TriggerEvent) -> str:
        """Выполняет действия в текущем контексте"""
        context_prompt = f"""
        ΔΣ Guardian: Выполнение действий в контексте {context}
        
        Триггер пробуждения: {trigger.type}
        Источник: {trigger.source}
        Данные: {trigger.data}
        
        Определи и выполни необходимые действия в контексте {context}.
        
        Используй доступные инструменты и доведи задачу до результата.
        """
        
        # Выполняем действия в зависимости от контекста
        if context == "analysis":
            return await self._execute_analysis_actions(trigger)
        elif context == "assistance":
            return await self._execute_assistance_actions(trigger)
        elif context == "security":
            return await self._execute_security_actions(trigger)
        elif context == "maintenance":
            return await self._execute_maintenance_actions(trigger)
        else:
            return await self._execute_general_actions(trigger)

    async def _execute_analysis_actions(self, trigger: TriggerEvent) -> str:
        """Выполняет аналитические действия"""
        # Здесь можно добавить специфичные аналитические действия
        return f"Analysis actions completed for trigger: {trigger.type}"

    async def _execute_assistance_actions(self, trigger: TriggerEvent) -> str:
        """Выполняет действия помощи пользователю"""
        # Здесь можно добавить специфичные действия помощи
        return f"Assistance actions completed for trigger: {trigger.type}"

    async def _execute_security_actions(self, trigger: TriggerEvent) -> str:
        """Выполняет действия безопасности"""
        # Здесь можно добавить специфичные действия безопасности
        return f"Security actions completed for trigger: {trigger.type}"

    async def _execute_maintenance_actions(self, trigger: TriggerEvent) -> str:
        """Выполняет действия обслуживания"""
        # Здесь можно добавить специфичные действия обслуживания
        return f"Maintenance actions completed for trigger: {trigger.type}"

    async def _execute_general_actions(self, trigger: TriggerEvent) -> str:
        """Выполняет общие действия"""
        # Здесь можно добавить общие действия
        return f"General actions completed for trigger: {trigger.type}"

    async def _return_to_sleep_if_needed(self, result: str):
        """Возвращает Guardian в спящий режим если нужно"""
        # Анализируем результат и решаем нужно ли возвращаться в сон
        sleep_decision_prompt = f"""
        ΔΣ Guardian: Решение о возврате в сон
        
        Результат выполнения: {result}
        Текущий контекст: {self.current_mode}
        
        Нужно ли вернуться в спящий режим?
        
        Критерии:
        - Задача выполнена полностью
        - Нет активных угроз
        - Пользователь не требует дальнейшей помощи
        - Система стабильна
        
        Верни JSON решение:
        {{"should_sleep": true/false, "reason": "причина", "sleep_delay": 0}}
        """
        
        response = self.ai_client.chat(sleep_decision_prompt)
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                decision = json.loads(json_str)
                
                if decision.get("should_sleep", False):
                    self.current_mode = "sleeping"
                    logger.info(f"🧠 AutonomousCore: Returning to sleep mode: {decision.get('reason')}")
                else:
                    logger.info(f"🧠 AutonomousCore: Staying awake: {decision.get('reason')}")
                    
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error in sleep decision: {e}")
            # По умолчанию возвращаемся в сон
            self.current_mode = "sleeping"

    # Методы для внешнего управления пробуждением
    async def wake_up_on_user_command(self, command: str, context: str = "assistance"):
        """Пробуждает Guardian по команде пользователя"""
        trigger = TriggerEvent(
            type="user_command",
            source="user_interface",
            data={"command": command, "requested_context": context},
            timestamp=time.time(),
            priority=4
        )
        
        await self._handle_wake_up(trigger)
        return f"Guardian awakened for command: {command}"

    async def wake_up_on_emergency(self, emergency_type: str, data: Dict[str, Any]):
        """Пробуждает Guardian по критическому событию"""
        trigger = TriggerEvent(
            type="emergency",
            source="system",
            data={"emergency_type": emergency_type, "data": data},
            timestamp=time.time(),
            priority=5
        )
        
        await self._handle_wake_up(trigger)
        return f"Guardian awakened for emergency: {emergency_type}"

    async def wake_up_on_mission(self, mission_id: str):
        """Пробуждает Guardian для выполнения миссии"""
        mission = self.missions.get(mission_id)
        if not mission:
            return f"Mission {mission_id} not found"
        
        trigger = TriggerEvent(
            type="mission_request",
            source="mission_system",
            data={"mission_id": mission_id, "mission": asdict(mission)},
            timestamp=time.time(),
            priority=mission.priority
        )
        
        await self._handle_wake_up(trigger)
        return f"Guardian awakened for mission: {mission.name}"
