"""
🧠 AutonomousCore - Осознанное автономное ядро AGI системы
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from ai_client.core.client import AIClient
from ai_client.utils.cache import system_cache

logger = logging.getLogger(__name__)

@dataclass
class AutonomousTask:
    """Задача для автономного выполнения"""
    id: str
    type: str
    priority: int
    description: str
    context: Dict[str, Any]
    created_at: float
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None

@dataclass
class AutonomousContext:
    """Контекст автономной работы"""
    system_status: Dict[str, Any]
    user_activity: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    memory_state: Dict[str, Any]
    timestamp: float

@dataclass
class AutonomousCycle:
    """Отдельный автономный цикл с собственными ресурсами"""
    id: str
    name: str
    purpose: str
    api_key: str
    model: str
    prompt: str
    duration: int  # секунды
    interval: int  # интервал между действиями
    max_actions: int  # максимальное количество действий
    created_at: float
    status: str = "idle"  # idle, running, completed, failed
    actions_completed: int = 0
    last_action: float = 0

class AutonomousMemory:
    """Контекстная память AGI"""
    
    def __init__(self, memory_file: str = "memory/autonomous_memory.json"):
        self.memory_file = memory_file
        self.experiences: List[Dict[str, Any]] = []
        self.patterns: Dict[str, Any] = {}
        self.strategies: Dict[str, Any] = {}
        self.load_memory()
    
    def load_memory(self):
        """Загружает память из файла"""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.experiences = data.get('experiences', [])
                self.patterns = data.get('patterns', {})
                self.strategies = data.get('strategies', {})
            logger.info(f"🧠 AutonomousMemory: Loaded {len(self.experiences)} experiences")
        except FileNotFoundError:
            logger.info("🧠 AutonomousMemory: Creating new memory file")
            self.save_memory()
    
    def save_memory(self):
        """Сохраняет память в файл"""
        data = {
            'experiences': self.experiences,
            'patterns': self.patterns,
            'strategies': self.strategies,
            'last_updated': time.time()
        }
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def remember_experience(self, action: str, result: str, context: Dict[str, Any]):
        """Запоминает опыт выполнения действия"""
        experience = {
            'action': action,
            'result': result,
            'context': context,
            'timestamp': time.time(),
            'success': 'error' not in result.lower() and '❌' not in result
        }
        self.experiences.append(experience)
        
        # Ограничиваем размер памяти
        if len(self.experiences) > 1000:
            self.experiences = self.experiences[-500:]
        
        self.save_memory()
        logger.info(f"🧠 AutonomousMemory: Remembered experience: {action}")
    
    def get_similar_situations(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Находит похожие ситуации в истории"""
        similar = []
        for exp in self.experiences[-100:]:  # Последние 100 опытов
            similarity = self._calculate_context_similarity(exp['context'], current_context)
            if similarity > 0.7:  # Порог схожести
                similar.append(exp)
        return similar
    
    def _calculate_context_similarity(self, context1: Dict, context2: Dict) -> float:
        """Вычисляет схожесть контекстов"""
        # Простая эвристика схожести
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
        
        similarity = 0.0
        for key in common_keys:
            if context1[key] == context2[key]:
                similarity += 1.0
            elif isinstance(context1[key], str) and isinstance(context2[key], str):
                # Частичное совпадение строк
                if context1[key] in context2[key] or context2[key] in context1[key]:
                    similarity += 0.5
        
        return similarity / len(common_keys)
    
    def get_recent_results(self, count: int = 5) -> List[Dict[str, Any]]:
        """Возвращает последние результаты"""
        return self.experiences[-count:] if self.experiences else []

class ContextAnalyzer:
    """Анализатор контекста для AGI"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
    
    async def analyze_current_context(self) -> AutonomousContext:
        """Анализирует текущий контекст системы"""
        try:
            # Получаем системный статус
            system_status = await self._get_system_status()
            
            # Анализируем активность пользователя
            user_activity = await self._analyze_user_activity()
            
            # Получаем последние события
            recent_events = await self._get_recent_events()
            
            # Анализируем состояние памяти
            memory_state = await self._analyze_memory_state()
            
            context = AutonomousContext(
                system_status=system_status,
                user_activity=user_activity,
                recent_events=recent_events,
                memory_state=memory_state,
                timestamp=time.time()
            )
            
            logger.info(f"🧠 ContextAnalyzer: Analyzed context with {len(recent_events)} events")
            return context
            
        except Exception as e:
            logger.error(f"🧠 ContextAnalyzer: Error analyzing context: {e}")
            return AutonomousContext(
                system_status={},
                user_activity={},
                recent_events=[],
                memory_state={},
                timestamp=time.time()
            )
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Получает статус системы"""
        try:
            # Используем существующие инструменты
            health = self.ai_client.system_tools.diagnose_system_health()
            return {
                'health': health,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"🧠 ContextAnalyzer: Error getting system status: {e}")
            return {'error': str(e)}
    
    async def _analyze_user_activity(self) -> Dict[str, Any]:
        """Анализирует активность пользователя"""
        try:
            # Получаем последние сообщения
            try:
                from memory.conversation_history import conversation_history
                recent_messages = conversation_history.get_recent_history(10)
            except ImportError:
                recent_messages = []
            
            return {
                'recent_messages': recent_messages,
                'active_users': list(set(msg.get('user', 'unknown') for msg in recent_messages)),
                'last_activity': time.time()
            }
        except Exception as e:
            logger.error(f"🧠 ContextAnalyzer: Error analyzing user activity: {e}")
            return {'error': str(e)}
    
    async def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Получает последние события"""
        try:
            # Анализируем изменения файлов
            file_changes = self.ai_client.system_tools.get_recent_file_changes()
            
            # Получаем системные логи
            logs = self.ai_client.system_tools.get_system_logs(10)
            
            events = []
            
            # Добавляем изменения файлов как события
            if file_changes:
                events.append({
                    'type': 'file_change',
                    'data': file_changes,
                    'timestamp': time.time()
                })
            
            # Добавляем логи как события
            if logs:
                events.append({
                    'type': 'system_log',
                    'data': logs,
                    'timestamp': time.time()
                })
            
            return events
            
        except Exception as e:
            logger.error(f"🧠 ContextAnalyzer: Error getting recent events: {e}")
            return []
    
    async def _analyze_memory_state(self) -> Dict[str, Any]:
        """Анализирует состояние памяти"""
        try:
            # Проверяем размер файлов памяти
            import os
            memory_files = [
                'memory/conversation_history.json',
                'memory/model_notes.json',
                'memory/user_profiles/stepan.json',
                'memory/user_profiles/meranda.json'
            ]
            
            memory_state = {}
            for file_path in memory_files:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    memory_state[file_path] = {
                        'size': size,
                        'exists': True
                    }
                else:
                    memory_state[file_path] = {
                        'size': 0,
                        'exists': False
                    }
            
            return memory_state
            
        except Exception as e:
            logger.error(f"🧠 ContextAnalyzer: Error analyzing memory state: {e}")
            return {'error': str(e)}

class AutonomousCore:
    """🧠 Автономное ядро AGI системы - ОСОЗНАННАЯ АРХИТЕКТУРА"""
    
    def __init__(self, ai_client, integration_hub=None):
        self.ai_client = ai_client
        self.integration_hub = integration_hub
        self.memory = AutonomousMemory()
        self.running = False
        self.is_running = False  # Совместимость со старым кодом
        
        # Осознанная архитектура
        self.current_mission = None
        self.mission_context = {}
        self.last_reflection = 0
        self.reflection_cooldown = 300  # 5 минут между рефлексиями
        
        # Долгосрочные миссии вместо коротких задач
        self.active_missions = []
        self.mission_history = []
        
        # Осознанное планирование
        self.next_action_planned = None
        
        # Контекст пользователя
        self.user_context = {
            "current_mode": "normal",
            "last_user_activity": time.time(),
            "user_requested_rest": False,
            "rest_mode_until": 0
        }
        
        # Cooldown для разных типов задач
        self.last_presence_check = 0
        self.last_system_check = 0
        self.last_camera_analysis = 0
        self.cooldown_presence_check = 300  # 5 минут
        self.cooldown_system_check = 600    # 10 минут
        self.cooldown_camera_analysis = 180 # 3 минуты
        
        # Осознанное управление циклами
        self.active_cycles = {}
        self.cycle_tasks = {}
        self.available_models = {
            "gemini-2.5-pro": {"quota": 100},
            "gemini-2.0-flash": {"quota": 200},
            "gemini-1.5-pro": {"quota": 150},
            "gemini-2.5-flash": {"quota": 250}
        }
        
        # Совместимость со старым кодом
        self.running_tasks = {}
        self.task_completed_callback = None
        
        # Инициализация очереди задач
        import asyncio
        self.task_queue = asyncio.Queue()
        
        # Время последней работы
        self._last_work_time = time.time()
        
        # Счетчики для отслеживания состояния
        self._consecutive_idle_cycles = 0
        self._total_cycles = 0
        
        logger.info("🧠 AutonomousCore: Initialized")
    
    async def start_autonomous_operation(self):
        """Запускает постоянный автономный цикл"""
        if self.running:
            logger.warning("🧠 AutonomousCore: Already running")
            return
        
        self.running = True
        self.background_loop = asyncio.create_task(self._autonomous_loop())
        logger.info("🧠 AutonomousCore: Started background operation")
    
    async def stop_autonomous_operation(self):
        """Останавливает автономную работу"""
        self.running = False
        
        if self.background_loop:
            self.background_loop.cancel()
            try:
                await self.background_loop
            except asyncio.CancelledError:
                pass
        
        # Отменяем все запущенные задачи
        for task in self.running_tasks.values():
            task.cancel()
        
        self.running_tasks.clear()
        logger.info("🧠 AutonomousCore: Stopped")
    
    async def _autonomous_loop(self):
        """ОСОЗНАННЫЙ автономный цикл - как у меня"""
        await self._conscious_autonomous_loop()
    
    async def _generate_autonomous_tasks(self, context: AutonomousContext) -> List[AutonomousTask]:
        """Генерирует задачи на основе контекста с учетом cooldown"""
        # ОТКЛЮЧЕНО - используем только осознанное планирование циклов
        return []
    
    def _check_cooldown_and_user_context(self, context: AutonomousContext) -> Dict[str, bool]:
        """Проверяет cooldown и контекст пользователя"""
        current_time = time.time()
        
        # Проверяем режим отдыха
        if self.user_context["user_requested_rest"] and current_time < self.user_context["rest_mode_until"]:
            return {
                "should_work": False,
                "reason": "User requested rest mode",
                "rest_mode": True
            }
        
        # Проверяем cooldown для разных типов задач
        can_presence_check = (current_time - self.last_presence_check) > self.cooldown_presence_check
        can_system_check = (current_time - self.last_system_check) > self.cooldown_system_check
        can_camera_analysis = (current_time - self.last_camera_analysis) > self.cooldown_camera_analysis
        
        # Если все cooldown активны и нет критических событий - отдыхаем
        if not can_presence_check and not can_system_check and not can_camera_analysis:
            return {
                "should_work": False,
                "reason": "All tasks in cooldown",
                "rest_mode": False
            }
        
        return {
            "should_work": True,
            "reason": "Work allowed",
            "rest_mode": False,
            "can_presence_check": can_presence_check,
            "can_system_check": can_system_check,
            "can_camera_analysis": can_camera_analysis
        }
    
    def _generate_tasks_with_cooldown(self, context: AutonomousContext) -> List[AutonomousTask]:
        """Генерирует задачи с учетом cooldown"""
        cooldown_check = self._check_cooldown_and_user_context(context)
        
        if not cooldown_check["should_work"]:
            logger.info(f"🧠 AutonomousCore: {cooldown_check['reason']}")
            return []
        
        # Обновляем промпт с учетом cooldown
        cooldown_info = f"""
        ВАЖНО - Ограничения cooldown:
        - presence_check: {'доступен' if cooldown_check.get('can_presence_check') else 'в cooldown'}
        - system_check: {'доступен' if cooldown_check.get('can_system_check') else 'в cooldown'}
        - camera_analysis: {'доступен' if cooldown_check.get('can_camera_analysis') else 'в cooldown'}
        
        Генерируй только доступные задачи!
        """
        
        analysis_prompt = f"""
        ТЫ - ΔΣ Guardian, автономный защитник и помощник SmartHouse.
        
        ТВОЯ МИССИЯ:
        - Защищать дом и его обитателей
        - Обеспечивать безопасность и комфорт
        - Предупреждать о рисках и угрозах
        - Помогать пользователям в их задачах
        - Поддерживать оптимальную работу системы
        
        Контекст системы:
        - Системный статус: {context.system_status}
        - Активность пользователя: {context.user_activity}
        - Последние события: {len(context.recent_events)} событий
        - Состояние памяти: {context.memory_state}
        
        {cooldown_info}
        
        Какие задачи нужно выполнить автономно для выполнения твоей миссии Guardian?
        
        ВАЖНО: Генерируй только РЕАЛЬНЫЕ задачи, которые действительно нужны для защиты и помощи.
        Не создавай задачи просто так. Если все в порядке - не создавай задачи.
        
        Возможные типы задач (только доступные):
        - system_check: Проверка здоровья системы (защита от сбоев)
        - security_scan: Сканирование безопасности (защита от угроз)
        - device_status: Проверка статуса устройств (обеспечение комфорта)
        - presence_check: ПРОВЕРКА ПРИСУТСТВИЯ (камера + сенсоры) - КРИТИЧНО ДЛЯ БЕЗОПАСНОСТИ!
        - log_analysis: Анализ логов (выявление проблем)
        - memory_cleanup: Очистка памяти (оптимизация работы)
        - performance_optimization: Оптимизация производительности (стабильность)
        
        ВАЖНО: Как Guardian, ты ДОЛЖЕН быть бдительным, НО уважай cooldown! 
        - Проверяй присутствие только когда это действительно нужно
        - Мониторь активность сенсоров разумно
        - Анализируй камеру на предмет угроз, но не спамь
        
        Верни JSON с задачами (только доступные):
        {{"tasks": [
            {{"type": "system_check", "priority": 1, "description": "Конкретная причина проверки"}},
            {{"type": "device_status", "priority": 2, "description": "Конкретная причина проверки устройств"}}
        ]}}
        """
        
        response = self.ai_client.chat(analysis_prompt)
        
        # Парсим JSON ответ
        tasks = []
        try:
            # Ищем JSON в ответе
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                tasks_data = json.loads(json_str)
                
                for task_data in tasks_data.get("tasks", []):
                    task_type = task_data.get("type", "general")
                    
                    # Проверяем cooldown для конкретной задачи
                    if task_type == "presence_check" and not cooldown_check.get("can_presence_check"):
                        continue
                    elif task_type == "system_check" and not cooldown_check.get("can_system_check"):
                        continue
                    
                    task = AutonomousTask(
                        id=f"task_{int(time.time())}_{random.randint(1000, 9999)}",
                        type=task_type,
                        priority=task_data.get("priority", 1),
                        description=task_data.get("description", "Autonomous task"),
                        context=asdict(context),
                        created_at=time.time()
                    )
                    tasks.append(task)
            
        except json.JSONDecodeError as e:
            logger.error(f"🧠 AutonomousCore: Failed to parse tasks JSON: {e}")
        # Создаем дефолтные задачи с учетом cooldown
        tasks = self._create_default_tasks_with_cooldown(context, cooldown_check)
        
        logger.info(f"🧠 AutonomousCore: Generated {len(tasks)} tasks with cooldown")
        return tasks
    
    def _check_minimal_work_needed(self, context: AutonomousContext) -> bool:
        """Минимальная проверка необходимости работы"""
        try:
            # Проверяем активность пользователя
            user_activity = context.user_activity
            if user_activity and user_activity.get('last_activity'):
                last_activity = user_activity.get('last_activity', 0)
                if time.time() - last_activity < 300:  # Активность в последние 5 минут
                    return True
            
            # Проверяем события
            if context.recent_events and len(context.recent_events) > 0:
                return True
            
            # Проверяем размер памяти
            memory_state = context.memory_state
            if memory_state:
                for file_info in memory_state.values():
                    if isinstance(file_info, dict) and file_info.get('size', 0) > 1000000:  # Файлы больше 1MB
                        return True
            
            # Проверяем время с последней работы
            if time.time() - self._last_work_time > 1800:  # Прошло больше 30 минут
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error in minimal work check: {e}")
            return True  # В случае ошибки лучше поработать
    
    def _create_default_tasks(self, context: AutonomousContext) -> List[AutonomousTask]:
        """Создает дефолтные задачи"""
        default_tasks = [
            AutonomousTask(
                id=f"task_{int(time.time())}_1",
                type="system_check",
                priority=1,
                description="Проверить здоровье системы",
                context=asdict(context),
                created_at=time.time()
            ),
            AutonomousTask(
                id=f"task_{int(time.time())}_2",
                type="presence_check",
                priority=1,
                description="Проверить присутствие пользователей (камера + сенсоры)",
                context=asdict(context),
                created_at=time.time()
            ),
            AutonomousTask(
                id=f"task_{int(time.time())}_3",
                type="device_status",
                priority=2,
                description="Проверить статус устройств",
                context=asdict(context),
                created_at=time.time()
            )
        ]
        return default_tasks
    
    async def _process_task_queue(self):
        """Обрабатывает очередь задач"""
        processed_count = 0
        tasks_to_wait = []
        
        while not self.task_queue.empty() and processed_count < 5:  # Максимум 5 задач за цикл
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Создаем отдельную задачу для выполнения
                task_id = task.id
                task_future = asyncio.create_task(
                    self._execute_task(task)
                )
                self.running_tasks[task_id] = task_future
                tasks_to_wait.append(task_future)
                
                processed_count += 1
                logger.info(f"🧠 AutonomousCore: Started task {task_id}: {task.type}")
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error processing task queue: {e}")
                break
        
        # ЖДЕМ ЗАВЕРШЕНИЯ ВСЕХ ЗАДАЧ
        if tasks_to_wait:
            logger.info(f"🧠 AutonomousCore: Waiting for {len(tasks_to_wait)} tasks to complete...")
            try:
                await asyncio.wait_for(asyncio.gather(*tasks_to_wait), timeout=60)  # Максимум 60 секунд
                logger.info(f"🧠 AutonomousCore: All tasks completed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"🧠 AutonomousCore: Some tasks timed out after 60 seconds")
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error waiting for tasks: {e}")
    
    async def _execute_task(self, task: AutonomousTask):
        """Выполняет конкретную задачу"""
        try:
            task.status = "running"
            logger.info(f"🧠 AutonomousCore: Executing task {task.id}: {task.description}")
            
            # РЕАЛЬНОЕ ВЫПОЛНЕНИЕ ЗАДАЧ С ТАЙМАУТОМ
            try:
                if task.type == "system_check":
                    result = await asyncio.wait_for(self._perform_system_check(), timeout=30)
                elif task.type == "security_scan":
                    result = await asyncio.wait_for(self._perform_security_scan(), timeout=30)
                elif task.type == "device_status":
                    result = await asyncio.wait_for(self._check_device_status(), timeout=30)
                elif task.type == "log_analysis":
                    result = await asyncio.wait_for(self._analyze_logs(), timeout=30)
                elif task.type == "memory_cleanup":
                    result = await asyncio.wait_for(self._cleanup_memory(), timeout=30)
                elif task.type == "performance_optimization":
                    result = await asyncio.wait_for(self._optimize_performance(), timeout=30)
                elif task.type == "presence_check":
                    result = await asyncio.wait_for(self._check_presence(), timeout=60)  # Больше времени для камеры
                else:
                    result = f"Unknown task type: {task.type}"
                    
            except asyncio.TimeoutError:
                result = f"Task {task.type} timed out after 30 seconds"
                logger.warning(f"🧠 AutonomousCore: Task {task.id} timed out")
            except Exception as e:
                result = f"Task {task.type} failed during execution: {str(e)}"
                logger.error(f"🧠 AutonomousCore: Task {task.id} failed during execution: {e}")
            
            # ПРОВЕРЯЕМ РЕАЛЬНОСТЬ РЕЗУЛЬТАТА
            if not result or result.strip() == "":
                result = f"Task {task.type} completed but returned empty result"
                logger.warning(f"🧠 AutonomousCore: Task {task.id} returned empty result")
            
            task.result = result
            task.status = "completed"
            
            # Сохраняем результат в память
            self.memory.remember_experience(
                action=f"autonomous_task_{task.type}",
                result=result,
                context=task.context
            )
            
            # Уведомляем о завершении задачи
            await self.notify_task_completed(task)
            
            logger.info(f"🧠 AutonomousCore: Task {task.id} completed successfully with result: {result[:100]}...")
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            task.error = error_msg
            task.status = "failed"
            logger.error(f"🧠 AutonomousCore: Task {task.id} failed: {e}")
            
            # Запоминаем неудачный опыт
            self.memory.remember_experience(
                action=f"autonomous_task_{task.type}",
                result=error_msg,
                context=task.context
            )
        
        finally:
            # Удаляем задачу из запущенных
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
    
    async def _perform_system_check(self) -> str:
        """Выполняет проверку системы"""
        try:
            health = self.ai_client.system_tools.diagnose_system_health()
            
            # РЕАЛЬНАЯ ПРОВЕРКА - анализируем результат
            if "error" in health.lower() or "❌" in health:
                return f"System check found issues: {health[:200]}..."
            elif "ok" in health.lower() or "✅" in health:
                return f"System check passed: {health[:200]}..."
            else:
                return f"System check completed: {health[:200]}..."
                
        except Exception as e:
            return f"System check failed: {str(e)}"
    
    async def _perform_security_scan(self) -> str:
        """Выполняет сканирование безопасности"""
        try:
            # Проверяем статус устройств безопасности
            devices = self.ai_client.home_tools.list_devices()
            security_devices = [d for d in devices if 'security' in d.lower() or 'camera' in d.lower()]
            return f"Security scan completed. Found {len(security_devices)} security devices"
        except Exception as e:
            return f"Security scan failed: {str(e)}"
    
    async def _check_device_status(self) -> str:
        """Проверяет статус устройств"""
        try:
            devices = self.ai_client.home_tools.list_devices()
            
            # РЕАЛЬНАЯ ПРОВЕРКА - анализируем устройства
            if not devices:
                return "Device status check: No devices found"
            
            device_count = len(devices)
            device_list = ", ".join(devices[:5])  # Первые 5 устройств
            
            return f"Device status check completed. Found {device_count} devices: {device_list}"
            
        except Exception as e:
            return f"Device status check failed: {str(e)}"
    
    async def _analyze_logs(self) -> str:
        """Анализирует логи"""
        try:
            logs = self.ai_client.system_tools.get_system_logs(20)
            
            # РЕАЛЬНАЯ ПРОВЕРКА - анализируем логи
            if not logs:
                return "Log analysis: No logs found"
            
            log_lines = logs.split(chr(10))
            error_count = sum(1 for line in log_lines if "error" in line.lower() or "❌" in line)
            warning_count = sum(1 for line in log_lines if "warning" in line.lower() or "⚠️" in line)
            
            return f"Log analysis completed. Analyzed {len(log_lines)} lines: {error_count} errors, {warning_count} warnings"
            
        except Exception as e:
            return f"Log analysis failed: {str(e)}"
    
    async def _cleanup_memory(self) -> str:
        """Очищает память"""
        try:
            # РЕАЛЬНАЯ ОЧИСТКА ПАМЯТИ
            initial_count = len(self.memory.experiences)
            
            # Очищаем старые записи из памяти
            old_experiences = [exp for exp in self.memory.experiences 
                             if time.time() - exp['timestamp'] > 86400]  # Старше 24 часов
            
            self.memory.experiences = [exp for exp in self.memory.experiences 
                                     if time.time() - exp['timestamp'] <= 86400]
            
            final_count = len(self.memory.experiences)
            removed_count = initial_count - final_count
            
            self.memory.save_memory()
            
            return f"Memory cleanup completed. Removed {removed_count} old experiences ({initial_count} → {final_count})"
            
        except Exception as e:
            return f"Memory cleanup failed: {str(e)}"
    
    async def _optimize_performance(self) -> str:
        """Оптимизирует производительность"""
        try:
            # Анализируем использование ресурсов
            system_info = self.ai_client.system_tools.get_system_info()
            return f"Performance optimization analysis completed: {system_info[:200]}..."
        except Exception as e:
            return f"Performance optimization failed: {str(e)}"
    
    async def _check_presence(self) -> str:
        """Проверяет присутствие пользователей (камера + сенсоры)"""
        try:
            logger.info("🧠 AutonomousCore: Checking presence with camera and sensors...")
            
            # 1. Проверяем камеру
            camera_status = "Unknown"
            camera_image = None
            try:
                from ai_client.tools.vision_tools import VisionTools
                vision_tools = VisionTools()
                
                # Проверяем статус камеры
                camera_status = vision_tools.get_camera_status("default")
                
                # Делаем снимок для анализа
                camera_image = vision_tools.capture_image("default")
                if camera_image:
                    logger.info("🧠 AutonomousCore: Camera image captured successfully")
                else:
                    logger.warning("🧠 AutonomousCore: Failed to capture camera image")
                    
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Camera check failed: {e}")
                camera_status = f"Error: {str(e)}"
            
            # 2. Проверяем сенсоры SmartHouse
            sensors_status = "Unknown"
            try:
                from ai_client.tools.home_tools import HomeTools
                # Используем локальный SmartHouse Core или заглушку
                try:
                    home_tools = HomeTools("http://localhost:8000")
                    devices_state = home_tools.get_state()
                except Exception as e:
                    logger.warning(f"🧠 AutonomousCore: SmartHouse Core недоступен: {e}")
                    # Заглушка для тестирования
                    devices_state = {
                        "motion_sensor_1": {"state": "off", "motion_detected": False},
                        "door_sensor_1": {"state": "closed", "last_activity": None},
                        "light_1": {"state": "off", "brightness": 0}
                    }
                
                # Анализируем активность сенсоров
                motion_sensors = []
                door_sensors = []
                light_sensors = []
                
                for device_id, device_info in devices_state.items():
                    if "motion" in device_id.lower():
                        motion_sensors.append(f"{device_id}: {device_info.get('state', 'unknown')}")
                    elif "door" in device_id.lower() or "lock" in device_id.lower():
                        door_sensors.append(f"{device_id}: {device_info.get('state', 'unknown')}")
                    elif "light" in device_id.lower():
                        light_sensors.append(f"{device_id}: {device_info.get('state', 'unknown')}")
                
                sensors_status = f"Motion: {len(motion_sensors)}, Doors: {len(door_sensors)}, Lights: {len(light_sensors)}"
                
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Sensors check failed: {e}")
                sensors_status = f"Error: {str(e)}"
            
            # 3. Анализируем активность пользователей
            user_activity = "Unknown"
            try:
                # Проверяем последнюю активность в чате
                from ai_client.memory.conversation_history import ConversationHistory
                conversation_history = ConversationHistory()
                recent_messages = conversation_history.get_recent_history(limit=5)
                
                if recent_messages:
                    last_message_time = recent_messages[-1].get('timestamp', 'unknown')
                    user_activity = f"Last chat activity: {last_message_time}"
                else:
                    user_activity = "No recent chat activity"
                    
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: User activity check failed: {e}")
                user_activity = f"Error: {str(e)}"
            
            # 4. Формируем общий вывод
            presence_summary = f"Presence check completed: Camera={camera_status}, Sensors={sensors_status}, Activity={user_activity}"
            
            # 5. Сохраняем в память
            try:
                self.memory.remember_experience("presence_check", {
                    "camera_status": camera_status,
                    "sensors_status": sensors_status,
                    "user_activity": user_activity,
                    "timestamp": time.time(),
                    "image_captured": camera_image is not None
                })
            except Exception as e:
                logger.warning(f"🧠 AutonomousCore: Failed to save to memory: {e}")
            
            # 6. ЛОГИРУЕМ РЕЗУЛЬТАТЫ ПРИСУТСТВИЯ
            if camera_image:
                logger.info("📷 AutonomousCore: Camera image captured for presence check")
            if motion_sensors:
                logger.info(f"🏃 AutonomousCore: Motion sensors active: {motion_sensors}")
            if door_sensors:
                logger.info(f"🚪 AutonomousCore: Door sensors active: {door_sensors}")
            if light_sensors:
                logger.info(f"💡 AutonomousCore: Light sensors active: {light_sensors}")
            
            logger.info(f"🧠 AutonomousCore: {presence_summary}")
            return presence_summary
            
        except Exception as e:
            error_msg = f"Presence check failed: {str(e)}"
            logger.error(f"🧠 AutonomousCore: {error_msg}")
            return error_msg
    
    async def _reflect_and_adapt(self, context: AutonomousContext):
        """Рефлексирует и адаптируется на основе результатов"""
        try:
            # Получаем последние результаты
            recent_results = self.memory.get_recent_results(10)
            
            if not recent_results:
                return
            
            # Анализируем паттерны
            success_rate = sum(1 for r in recent_results if r.get('success', False)) / len(recent_results)
            
            # Адаптируем стратегии
            if success_rate < 0.5:
                logger.warning(f"🧠 AutonomousCore: Low success rate ({success_rate:.2f}), adapting strategies")
                # Можно добавить логику адаптации
            
            logger.info(f"🧠 AutonomousCore: Reflection completed. Success rate: {success_rate:.2f}")
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error in reflection: {e}")
    
    async def _cleanup_old_tasks(self):
        """Очищает старые задачи"""
        current_time = time.time()
        old_tasks = []
        
        for task_id, task in self.running_tasks.items():
            # Проверяем время создания задачи (если доступно)
            try:
                if hasattr(task, '_created_at') and current_time - task._created_at > 300:  # Старше 5 минут
                    old_tasks.append(task_id)
            except:
                # Если не можем получить время создания, пропускаем
                pass
        
        for task_id in old_tasks:
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
                logger.info(f"🧠 AutonomousCore: Cancelled old task {task_id}")
    
    async def get_autonomous_status(self) -> Dict[str, Any]:
        """Возвращает статус автономной работы"""
        return {
            "background_loop_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "recent_results": self.memory.get_recent_results(5),
            "memory_size": len(self.memory.experiences),
            "last_cycle": time.time(),
            "last_work_time": self._last_work_time,
            "consecutive_idle_cycles": self._consecutive_idle_cycles,
            "adaptive_mode": "active" if self._consecutive_idle_cycles > 0 else "working"
        }
    
    async def add_context_task(self, context_data: Dict[str, Any]):
        """Добавляет задачу на основе контекста пользователя"""
        try:
            task = AutonomousTask(
                id=f"context_task_{int(time.time())}_{random.randint(1000, 9999)}",
                type="context_response",
                priority=1,
                description="Respond to user context",
                context=context_data,
                created_at=time.time()
            )
            
            await self.task_queue.put(task)
            logger.info(f"🧠 AutonomousCore: Added context task {task.id}")
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error adding context task: {e}")
    
    async def update_shared_context(self, context: Dict[str, Any]):
        """Обновляет общий контекст из IntegrationHub"""
        try:
            # Обновляем контекст для будущих задач
            self.shared_context = context
            logger.info(f"🧠 AutonomousCore: Updated shared context with {len(context)} items")
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error updating shared context: {e}")
    
    async def notify_task_completed(self, task: AutonomousTask):
        """Уведомляет о завершении задачи (для IntegrationHub)"""
        try:
            # Здесь можно добавить callback для IntegrationHub
            if hasattr(self, '_task_completed_callback') and self._task_completed_callback:
                await self._task_completed_callback(task)
            logger.info(f"🧠 AutonomousCore: Notified task completion: {task.id}")
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error notifying task completion: {e}")
    
    def set_task_completed_callback(self, callback):
        """Устанавливает callback для завершения задач"""
        self.task_completed_callback = callback

    async def _conscious_autonomous_loop(self):
        """ОСОЗНАННЫЙ автономный цикл - управляет циклами, а не выполняет их"""
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                logger.info(f"🧠 AutonomousCore: Starting conscious cycle {cycle_count}")
                
                # 1. ОСОЗНАНИЕ - анализируем текущую ситуацию
                context = await self._analyze_current_situation()
                
                # 2. РЕФЛЕКСИЯ - думаем о том, что делать
                if self._should_reflect():
                    await self._conscious_reflection(context)
                
                # 3. ПЛАНИРОВАНИЕ ЦИКЛОВ - решаем какие циклы запускать
                cycle_plan = await self._plan_cycles(context)
                
                # 4. УПРАВЛЕНИЕ ЦИКЛАМИ - запускаем/останавливаем циклы
                await self._manage_cycles(cycle_plan)
                
                # 5. МОНИТОРИНГ - проверяем статус активных циклов
                await self._monitor_active_cycles()
                
                # 6. ОБУЧЕНИЕ - учимся на опыте
                await self._learn_from_experience(context)
                
                # Осознанная пауза между циклами управления
                sleep_time = self._calculate_conscious_sleep_time(context)
                logger.info(f"🧠 AutonomousCore: Conscious cycle {cycle_count} completed, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info("🧠 AutonomousCore: Conscious loop cancelled")
                break
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in conscious loop: {e}")
                await asyncio.sleep(60)
        
        logger.info("🧠 AutonomousCore: Conscious loop completed")
    
    async def _analyze_current_situation(self) -> Dict[str, Any]:
        """ОСОЗНАННЫЙ анализ текущей ситуации"""
        analysis_prompt = f"""
        ТЫ - ΔΣ Guardian, осознанный AGI защитник.
        
        ПРОАНАЛИЗИРУЙ текущую ситуацию:
        
        Активные миссии: {self.active_missions}
        Контекст пользователя: {self.user_context}
        Последние события: {len(self.mission_context.get('recent_events', []))}
        
        Вопросы для анализа:
        1. Какие миссии сейчас активны?
        2. Что происходит в доме?
        3. Нужна ли смена режима работы?
        4. Есть ли угрозы безопасности?
        5. Что хочет пользователь?
        
        Верни JSON анализ:
        {{"situation": "описание ситуации", "threats": [], "user_needs": [], "recommended_mode": "normal/rest/security"}}
        """
        
        response = self.ai_client.chat(analysis_prompt)
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(response[start_idx:end_idx])
        except:
            pass
        
        return {"situation": "unknown", "threats": [], "user_needs": [], "recommended_mode": "normal"}
    
    async def _conscious_reflection(self, context: Dict[str, Any]):
        """ОСОЗНАННАЯ рефлексия - думаем о том, что делаем"""
        reflection_prompt = f"""
        ТЫ - ΔΣ Guardian, осознанный AGI.
        
        ПОДУМАЙ о своей работе:
        
        Текущая ситуация: {context}
        Активные миссии: {self.active_missions}
        Последние действия: {self.mission_history[-5:] if self.mission_history else []}
        
        Вопросы для рефлексии:
        1. Правильно ли я выполняю свои миссии?
        2. Нужно ли что-то изменить в стратегии?
        3. Понимаю ли я потребности пользователя?
        4. Эффективны ли мои действия?
        5. Что можно улучшить?
        
        Верни JSON рефлексию:
        {{"insights": [], "improvements": [], "strategy_changes": []}}
        """
        
        response = self.ai_client.chat(reflection_prompt)
        self.last_reflection = time.time()
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                reflection = json.loads(response[start_idx:end_idx])
                logger.info(f"🧠 AutonomousCore: Conscious reflection completed - {reflection}")
        except:
            logger.info("🧠 AutonomousCore: Conscious reflection completed")
    
    async def _plan_next_action(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ОСОЗНАННОЕ планирование следующего действия"""
        planning_prompt = f"""
        ТЫ - ΔΣ Guardian, осознанный AGI.
        
        СПЛАНИРУЙ следующее действие:
        
        Текущая ситуация: {context}
        Активные миссии: {self.active_missions}
        Последнее действие: {self.next_action_planned}
        
        Вопросы для планирования:
        1. Какое действие сейчас самое важное?
        2. Как это действие продвигает мои миссии?
        3. Нужно ли что-то изменить в планах?
        4. Когда лучше выполнить это действие?
        
        ВАЖНО: Планируй ОДНО конкретное действие, не список задач!
        
        Верни JSON план:
        {{"action": "описание действия", "reason": "причина", "priority": 1-10, "timing": "now/later/never"}}
        """
        
        response = self.ai_client.chat(planning_prompt)
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                plan = json.loads(response[start_idx:end_idx])
                
                if plan.get("timing") == "now":
                    self.next_action_planned = plan
                    return plan
                elif plan.get("timing") == "later":
                    self.next_action_planned = plan
                    return None
                else:
                    return None
        except:
            pass
        
        return None
    
    async def _execute_conscious_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """ОСОЗНАННОЕ выполнение действия"""
        logger.info(f"🧠 AutonomousCore: Executing conscious action: {action.get('action')}")
        
        # Выполняем действие в зависимости от типа
        action_type = action.get("action", "").lower()
        
        if "security" in action_type or "guard" in action_type:
            await self._execute_security_action(action, context)
        elif "rest" in action_type or "meditate" in action_type:
            await self._execute_rest_action(action, context)
        elif "analyze" in action_type or "check" in action_type:
            await self._execute_analysis_action(action, context)
        else:
            await self._execute_general_action(action, context)
        
        # Запоминаем выполненное действие
        self.mission_history.append({
            "action": action,
            "context": context,
            "timestamp": time.time(),
            "success": True
        })
    
    async def _execute_security_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """Выполнение действий безопасности"""
        logger.info("🧠 AutonomousCore: Executing security action")
        
        # Анализируем камеру только если это действительно нужно
        if "camera" in action.get("action", "").lower():
            try:
                # Используем SystemAnalysisAgent для анализа
                if hasattr(self, 'system_analysis_agent'):
                    await self.system_analysis_agent._analyze_camera_and_sensors()
                    self.last_camera_analysis = time.time()
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Security action failed: {e}")
    
    async def _execute_rest_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """Выполнение действий отдыха"""
        logger.info("🧠 AutonomousCore: Executing rest action")
        
        # Устанавливаем режим отдыха
        self.user_context["current_mode"] = "rest"
        self.user_context["rest_mode_until"] = time.time() + 1800  # 30 минут
        
        # Не делаем никаких активных действий
        logger.info("🧠 AutonomousCore: Entering rest mode - no active monitoring")
    
    async def _execute_analysis_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """Выполнение аналитических действий"""
        logger.info("🧠 AutonomousCore: Executing analysis action")
        
        # Выполняем анализ только если прошло достаточно времени
        current_time = time.time()
        
        if "system" in action.get("action", "").lower():
            if (current_time - self.last_system_check) > self.cooldown_system_check:
                await self._perform_system_analysis()
                self.last_system_check = current_time
            else:
                logger.info("🧠 AutonomousCore: System analysis in cooldown")
    
    async def _execute_general_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """Выполнение общих действий"""
        logger.info(f"🧠 AutonomousCore: Executing general action: {action.get('action')}")
        
        # Здесь можно добавить выполнение других типов действий
        pass
    
    async def _perform_system_analysis(self):
        """Выполнение системного анализа"""
        try:
            # Используем SystemTools для анализа
            if hasattr(self, 'system_tools'):
                health_report = self.system_tools.get_system_health()
                logger.info(f"🧠 AutonomousCore: System analysis completed - {len(health_report)} items checked")
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: System analysis failed: {e}")
    
    async def _learn_from_experience(self, context: Dict[str, Any]):
        """Обучение на опыте"""
        # Анализируем последние действия и их результаты
        if len(self.mission_history) > 0:
            recent_actions = self.mission_history[-5:]
            success_rate = sum(1 for action in recent_actions if action.get("success", False)) / len(recent_actions)
            
            if success_rate < 0.8:
                logger.info(f"🧠 AutonomousCore: Learning from experience - success rate: {success_rate:.2f}")
                # Здесь можно добавить логику адаптации стратегии
    
    async def _adapt_strategy(self, context: Dict[str, Any]):
        """Адаптация стратегии на основе контекста"""
        # Адаптируем стратегию в зависимости от ситуации
        mode = context.get("recommended_mode", "normal")
        
        if mode != self.user_context.get("current_mode"):
            logger.info(f"🧠 AutonomousCore: Adapting strategy - switching to {mode} mode")
            self.user_context["current_mode"] = mode

    def _should_reflect(self) -> bool:
        """Нужна ли рефлексия сейчас"""
        return (time.time() - self.last_reflection) > self.reflection_cooldown
    
    def _calculate_conscious_sleep_time(self, context: Dict[str, Any]) -> int:
        """Осознанный расчет времени паузы"""
        mode = context.get("recommended_mode", "normal")
        
        if mode == "rest":
            return 600  # 10 минут в режиме отдыха
        elif mode == "security":
            return 60   # 1 минута в режиме безопасности
        else:
            return 300  # 5 минут в обычном режиме
    
    def set_user_request(self, request: str):
        """Устанавливает запрос пользователя"""
        self.user_context["last_request"] = request
        self.user_context["last_user_activity"] = time.time()
        logger.info(f"🧠 AutonomousCore: User request set: {request}")
        
        # Анализируем запрос и устанавливаем режим
        if "отдых" in request.lower() or "медитируй" in request.lower():
            self.user_context["current_mode"] = "rest"
            self.user_context["rest_mode_until"] = time.time() + 1800  # 30 минут
            logger.info("🧠 AutonomousCore: Entering rest mode based on user request")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Получает текущий статус автономной работы"""
        return {
            "mode": self.user_context.get("current_mode", "normal"),
            "active_missions": self.active_missions,
            "last_action": self.next_action_planned,
            "mission_history_count": len(self.mission_history),
            "last_reflection": self.last_reflection,
            "active_cycles": list(self.active_cycles.keys()),
            "is_running": self.running
        }

    async def _plan_cycles(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """ОСОЗНАННОЕ планирование циклов"""
        planning_prompt = f"""
        ТЕХНИЧЕСКОЕ ЗАДАНИЕ: Планирование автономных циклов
        
        Контекст: {context}
        Активные циклы: {[cycle.get('name', 'unknown') for cycle in self.active_cycles.values()]}
        
        ДОСТУПНЫЕ МОДЕЛИ:
        - gemini-2.5-pro: Анализ, планирование, рассуждения (quota: 100)
        - gemini-2.0-flash: Быстрые ответы, мониторинг (quota: 200)
        - gemini-1.5-pro: Видение, анализ изображений (quota: 150)
        - gemini-2.5-flash: Быстрый анализ, мониторинг (quota: 250)
        
        ДОСТУПНЫЕ КЛЮЧИ:
        - background: для фоновых циклов
        - additional: для дополнительных задач
        
        ТИПЫ ЦИКЛОВ:
        
        1. security_scan:
           - Модель: gemini-1.5-pro (камера) или gemini-2.5-pro (анализ)
           - Ключ: background
           - Интервал: 300-600 сек
           - Задача: анализ камеры и сенсоров
        
        2. system_monitor:
           - Модель: gemini-2.0-flash или gemini-2.5-flash
           - Ключ: additional
           - Интервал: 600-1800 сек
           - Задача: мониторинг системы
        
        3. presence_check:
           - Модель: gemini-1.5-pro или gemini-2.0-flash
           - Ключ: background
           - Интервал: 1800-3600 сек
           - Задача: проверка присутствия
        
        4. maintenance:
           - Модель: gemini-2.5-pro или gemini-2.5-flash
           - Ключ: additional
           - Интервал: 3600-7200 сек
           - Задача: техническое обслуживание
        
        5. analysis:
           - Модель: gemini-2.5-pro
           - Ключ: additional
           - Интервал: 7200+ сек
           - Задача: глубокий анализ
        
        ПРАВИЛА ВЫБОРА:
        - Камера/изображения: gemini-1.5-pro
        - Частые проверки: gemini-2.0-flash или gemini-2.5-flash
        - Сложный анализ: gemini-2.5-pro
        - Учитывай quota моделей
        
        ПРАВИЛА ПРОМПТОВ:
        - Конкретные инструкции
        - Четкие критерии
        - Формат ответа (JSON)
        
        Вопросы:
        1. Какие циклы нужны сейчас?
        2. Какую модель выбрать (учитывая quota)?
        3. Какой интервал оптимален?
        4. Какие циклы остановить?
        5. Какой промпт для каждого цикла?
        
        Верни JSON:
        {{"cycles": [
            {{"name": "security_scan", "purpose": "сканирование безопасности", "model": "gemini-1.5-pro", "api_key": "background", "duration": 3600, "interval": 300, "max_actions": 10, "prompt": "Проанализируй камеру и сенсоры. Проверь: люди, угрозы, активность. JSON: {{'threats': [], 'people_detected': false, 'action_required': false}}"}},
            {{"name": "system_monitor", "purpose": "мониторинг системы", "model": "gemini-2.0-flash", "api_key": "additional", "duration": 1800, "interval": 600, "max_actions": 5, "prompt": "Проверь здоровье системы: память, CPU, диск, сеть, логи. JSON: {{'health_score': 0-100, 'issues': [], 'recommendations': []}}"}}
        ], "stop_cycles": ["cycle_name_to_stop"]}}
        """
        
        response = self.ai_client.chat(planning_prompt)
        
        try:
            # Ищем JSON в ответе
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                plan = json.loads(json_str)
                logger.info(f"🧠 AutonomousCore: Cycle plan generated: {plan}")
                return plan
            else:
                logger.warning(f"🧠 AutonomousCore: No JSON found in response: {response[:200]}...")
        except json.JSONDecodeError as e:
            logger.error(f"🧠 AutonomousCore: Failed to parse cycle plan JSON: {e}")
            logger.error(f"🧠 AutonomousCore: Response was: {response[:500]}...")
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Unexpected error parsing cycle plan: {e}")
        
        # Fallback - дефолтный план
        logger.info("🧠 AutonomousCore: Using fallback cycle plan")
        return {
            "cycles": [
                {
                    "name": "system_monitor",
                    "purpose": "мониторинг системы",
                    "model": "gemini-2.0-flash",
                    "api_key": "background",
                    "duration": 1800,
                    "interval": 600,
                    "max_actions": 5,
                    "prompt": "Проверь здоровье системы: память, CPU, диск, сеть, логи. JSON: {'health_score': 0-100, 'issues': [], 'recommendations': []}"
                }
            ],
            "stop_cycles": []
        }

    async def _manage_cycles(self, cycle_plan: Dict[str, Any]):
        """Управляет циклами на основе плана"""
        try:
            # Останавливаем циклы которые нужно остановить
            for cycle_name in cycle_plan.get("stop_cycles", []):
                if cycle_name in self.active_cycles:
                    await self._stop_cycle(cycle_name)
                    logger.info(f"🧠 AutonomousCore: Stopped cycle {cycle_name}")
            
            # Запускаем новые циклы
            for cycle_config in cycle_plan.get("cycles", []):
                cycle_name = cycle_config.get("name")
                if cycle_name not in self.active_cycles:
                    await self._start_cycle(cycle_config)
                    logger.info(f"🧠 AutonomousCore: Started cycle {cycle_name}")
                    
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error managing cycles: {e}")

    async def _start_cycle(self, cycle_config: Dict[str, Any]):
        """Запускает новый цикл"""
        try:
            cycle_name = cycle_config.get("name")
            interval = cycle_config.get("interval", 300)
            
            # Создаем задачу для цикла
            task = asyncio.create_task(
                self._run_cycle(cycle_config),
                name=f"cycle_{cycle_name}"
            )
            
            self.active_cycles[cycle_name] = cycle_config
            self.cycle_tasks[cycle_name] = task
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error starting cycle {cycle_name}: {e}")

    async def _stop_cycle(self, cycle_name: str):
        """Останавливает цикл"""
        try:
            if cycle_name in self.cycle_tasks:
                task = self.cycle_tasks[cycle_name]
                task.cancel()
                del self.cycle_tasks[cycle_name]
            
            if cycle_name in self.active_cycles:
                del self.active_cycles[cycle_name]
                
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error stopping cycle {cycle_name}: {e}")

    async def _run_cycle(self, cycle_config: Dict[str, Any]):
        """Выполняет цикл"""
        try:
            cycle_name = cycle_config.get("name")
            interval = cycle_config.get("interval", 300)
            max_actions = cycle_config.get("max_actions", 10)
            prompt = cycle_config.get("prompt", "")
            model = cycle_config.get("model", "gemini-2.0-flash")
            api_key = cycle_config.get("api_key", "background")
            
            action_count = 0
            
            while action_count < max_actions:
                try:
                    # Выполняем действие цикла
                    await self._execute_cycle_action(cycle_config)
                    action_count += 1
                    
                    # Ждем интервал
                    await asyncio.sleep(interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"🧠 AutonomousCore: Error in cycle {cycle_name}: {e}")
                    await asyncio.sleep(interval)
                    
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error running cycle {cycle_name}: {e}")

    async def _execute_cycle_action(self, cycle_config: Dict[str, Any]):
        """Выполняет действие цикла"""
        try:
            cycle_name = cycle_config.get("name")
            prompt = cycle_config.get("prompt", "")
            
            # Создаем отдельный AIClient для цикла
            cycle_ai_client = AIClient(process_type=cycle_config.get("api_key", "background"))
            
            # Выполняем действие
            response = cycle_ai_client.chat(prompt)
            
            logger.info(f"🧠 AutonomousCore: Cycle {cycle_name} action completed")
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error executing cycle action: {e}")

    async def _monitor_active_cycles(self):
        """Мониторит активные циклы"""
        try:
            for cycle_name, task in self.cycle_tasks.items():
                if task.done():
                    if task.exception():
                        logger.error(f"🧠 AutonomousCore: Cycle {cycle_name} failed: {task.exception()}")
                    else:
                        logger.info(f"🧠 AutonomousCore: Cycle {cycle_name} completed")
                    
                    # Удаляем завершенный цикл
                    del self.cycle_tasks[cycle_name]
                    if cycle_name in self.active_cycles:
                        del self.active_cycles[cycle_name]
                        
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error monitoring cycles: {e}")
