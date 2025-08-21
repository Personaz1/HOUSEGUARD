"""
🧠 AutonomousCore - Сердце AGI системы
Постоянный автономный цикл работы с контекстной памятью и адаптивным планированием
"""

import asyncio
import json
import time
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import logging
from ..utils.cache import SystemCache

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
    """Центральный компонент AGI - постоянный автономный цикл"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
        self.memory = AutonomousMemory()
        self.context_analyzer = ContextAnalyzer(ai_client)
        self.task_queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.background_loop: Optional[asyncio.Task] = None
        self.is_running = False
        self._last_work_time = time.time()
        self._consecutive_idle_cycles = 0
        self._task_completed_callback = None
        
        # Общий контекст для интеграции
        self.shared_context: Dict[str, Any] = {}
        
        # Кэш для результатов
        self.cache = SystemCache()
        
        logger.info("🧠 AutonomousCore: Initialized")
    
    async def start_autonomous_operation(self):
        """Запускает постоянный автономный цикл"""
        if self.is_running:
            logger.warning("🧠 AutonomousCore: Already running")
            return
        
        self.is_running = True
        self.background_loop = asyncio.create_task(self._autonomous_loop())
        logger.info("🧠 AutonomousCore: Started background operation")
    
    async def stop_autonomous_operation(self):
        """Останавливает автономную работу"""
        self.is_running = False
        
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
        """Постоянный цикл автономной работы"""
        cycle_count = 0
        
        while self.is_running:
            try:
                cycle_count += 1
                logger.info(f"🧠 AutonomousCore: Starting cycle {cycle_count}")
                
                # 1. Анализируем контекст
                context = await self.context_analyzer.analyze_current_context()
                
                # 2. Генерируем задачи на основе контекста
                tasks = await self._generate_autonomous_tasks(context)
                
                # 3. Добавляем задачи в очередь (если есть)
                if tasks:
                    for task in tasks:
                        await self.task_queue.put(task)
                    logger.info(f"🧠 AutonomousCore: Added {len(tasks)} tasks to queue")
                else:
                    logger.info(f"🧠 AutonomousCore: No tasks needed, system is stable")
                
                # 4. Обрабатываем очередь задач
                await self._process_task_queue()
                
                # 5. Рефлексируем и адаптируемся (только если были задачи)
                if tasks:
                    await self._reflect_and_adapt(context)
                
                # 6. Очищаем старые задачи
                await self._cleanup_old_tasks()
                
                # 7. УБЕЖДАЕМСЯ ЧТО ВСЕ ЗАДАЧИ ЗАВЕРШЕНЫ
                if self.running_tasks:
                    logger.warning(f"🧠 AutonomousCore: {len(self.running_tasks)} tasks still running, waiting...")
                    try:
                        await asyncio.wait_for(asyncio.gather(*list(self.running_tasks.values())), timeout=10)
                        logger.info(f"🧠 AutonomousCore: All remaining tasks completed")
                    except asyncio.TimeoutError:
                        logger.warning(f"🧠 AutonomousCore: Some tasks still running after timeout")
                    except Exception as e:
                        logger.error(f"🧠 AutonomousCore: Error waiting for remaining tasks: {e}")
                
                if tasks:
                    logger.info(f"🧠 AutonomousCore: Completed cycle {cycle_count} with {len(tasks)} tasks")
                    self._consecutive_idle_cycles = 0  # Сбрасываем счетчик
                    self._last_work_time = time.time()
                    sleep_time = 30  # Обычная пауза
                else:
                    self._consecutive_idle_cycles += 1
                    logger.info(f"🧠 AutonomousCore: Completed cycle {cycle_count} - system stable, no work needed (idle cycles: {self._consecutive_idle_cycles})")
                    
                    # Адаптивная пауза - увеличиваем время если система стабильна
                    if self._consecutive_idle_cycles >= 5:
                        sleep_time = 120  # 2 минуты после 5 пустых циклов
                    elif self._consecutive_idle_cycles >= 3:
                        sleep_time = 60   # 1 минута после 3 пустых циклов
                    else:
                        sleep_time = 30   # Обычная пауза
                
                # Пауза между циклами (адаптивная)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info("🧠 AutonomousCore: Loop cancelled")
                break
            except Exception as e:
                logger.error(f"🧠 AutonomousCore: Error in loop: {e}")
                await asyncio.sleep(60)  # Увеличенная пауза при ошибке
        
        # Цикл завершен, но не останавливаем систему
        logger.info("🧠 AutonomousCore: Loop completed, but system continues running")
    
    async def _generate_autonomous_tasks(self, context: AutonomousContext) -> List[AutonomousTask]:
        """Генерирует задачи на основе контекста"""
        tasks = []
        
        try:
            # Сначала проверяем - нужно ли вообще что-то делать
            should_work_prompt = f"""
            ТЫ - ΔΣ Guardian, автономный ассистент, защитник, помощник, и любимый член семьи Степана и Меранды.
            
            ТВОЯ МИССИЯ: Защищать и обсдуживать дом, обеспечивать безопасность, помогать членам семьи.
            
            Контекст системы:
            - Системный статус: {context.system_status}
            - Активность пользователя: {context.user_activity}
            - Последние события: {len(context.recent_events)} событий
            - Состояние памяти: {context.memory_state}
            
            Вопрос: Нужно ли выполнять какие-то автономные задачи прямо сейчас?
            
            ВАЖНО: Как Guardian, ты должен быть бдительным! 
            - Всегда проверяй присутствие для безопасности
            - Мониторь активность сенсоров
            - Анализируй камеру на предмет угроз
            - Если давно не проверял камеру и сенсоры - ОБЯЗАТЕЛЬНО добавь presence_check!
            
            Критерии для выполнения задач:
            - Есть ли проблемы в системе?
            - Была ли активность пользователя?
            - Есть ли новые события?
            - Нужна ли очистка памяти?
            - Прошло ли достаточно времени с последней проверки?
            
            Верни JSON ответ:
            {{"should_work": true/false, "reason": "причина"}}
            """
            
            should_work_response = self.ai_client.chat(should_work_prompt)
            
            # Парсим ответ о необходимости работы
            try:
                start_idx = should_work_response.find('{')
                end_idx = should_work_response.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = should_work_response[start_idx:end_idx]
                    should_work_data = json.loads(json_str)
                    
                    should_work = should_work_data.get("should_work", True)
                    reason = should_work_data.get("reason", "No reason provided")
                    
                    if not should_work:
                        logger.info(f"🧠 AutonomousCore: No work needed - {reason}")
                        return []  # Возвращаем пустой список задач
                    
                    logger.info(f"🧠 AutonomousCore: Work needed - {reason}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"🧠 AutonomousCore: Failed to parse should_work JSON: {e}")
                # Если не можем разобрать, делаем минимальную проверку
                should_work = self._check_minimal_work_needed(context)
                if not should_work:
                    logger.info(f"🧠 AutonomousCore: No work needed based on minimal check")
                    return []
            
            # Если нужно работать, генерируем задачи
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
            
            Какие задачи нужно выполнить автономно для выполнения твоей миссии Guardian?
            
            ВАЖНО: Генерируй только РЕАЛЬНЫЕ задачи, которые действительно нужны для защиты и помощи.
            Не создавай задачи просто так. Если все в порядке - не создавай задачи.
            
            Возможные типы задач:
            - system_check: Проверка здоровья системы (защита от сбоев)
            - security_scan: Сканирование безопасности (защита от угроз)
            - device_status: Проверка статуса устройств (обеспечение комфорта)
            - presence_check: ПРОВЕРКА ПРИСУТСТВИЯ (камера + сенсоры) - КРИТИЧНО ДЛЯ БЕЗОПАСНОСТИ!
            - log_analysis: Анализ логов (выявление проблем)
            - memory_cleanup: Очистка памяти (оптимизация работы)
            - performance_optimization: Оптимизация производительности (стабильность)
            
            ВАЖНО: Как Guardian, ты ДОЛЖЕН быть бдительным! 
            - Всегда проверяй присутствие для безопасности
            - Мониторь активность сенсоров
            - Анализируй камеру на предмет угроз
            - Если давно не проверял присутствие - ОБЯЗАТЕЛЬНО добавь presence_check!
            
            Верни JSON с задачами:
            {{"tasks": [
                {{"type": "system_check", "priority": 1, "description": "Конкретная причина проверки"}},
                {{"type": "device_status", "priority": 2, "description": "Конкретная причина проверки устройств"}}
            ]}}
            """
            
            response = self.ai_client.chat(analysis_prompt)
            
            # Парсим JSON ответ
            try:
                # Ищем JSON в ответе
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx]
                    tasks_data = json.loads(json_str)
                    
                    for task_data in tasks_data.get("tasks", []):
                        task = AutonomousTask(
                            id=f"task_{int(time.time())}_{random.randint(1000, 9999)}",
                            type=task_data.get("type", "general"),
                            priority=task_data.get("priority", 1),
                            description=task_data.get("description", "Autonomous task"),
                            context=asdict(context),
                            created_at=time.time()
                        )
                        tasks.append(task)
                
            except json.JSONDecodeError as e:
                logger.error(f"🧠 AutonomousCore: Failed to parse tasks JSON: {e}")
                # Создаем дефолтные задачи
                tasks = self._create_default_tasks(context)
            
        except Exception as e:
            logger.error(f"🧠 AutonomousCore: Error generating tasks: {e}")
            tasks = self._create_default_tasks(context)
        
        logger.info(f"🧠 AutonomousCore: Generated {len(tasks)} tasks")
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
                self.memory.add_experience("presence_check", {
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
        """Устанавливает callback для уведомления о завершении задач"""
        self._task_completed_callback = callback
