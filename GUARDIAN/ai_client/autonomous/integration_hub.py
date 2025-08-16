"""
🧠 IntegrationHub - Центр синхронизации AGI
Полная синхронизация между SystemAnalysis, Chat и AutonomousCore
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from .core import AutonomousCore, AutonomousTask
from .system_analysis_agent import SystemAnalysisAgent

logger = logging.getLogger(__name__)

@dataclass
class SystemEvent:
    """Событие системы для синхронизации"""
    type: str  # chat_message, system_analysis, autonomous_task, user_activity
    source: str  # chat, analysis, autonomous, user
    data: Dict[str, Any]
    timestamp: float
    priority: int = 1

class IntegrationHub:
    """Центр синхронизации всех компонентов AGI"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
        self.autonomous_core: Optional[AutonomousCore] = None
        self.system_agent: Optional[SystemAnalysisAgent] = None
        
        # Центральная память событий
        self.events: List[SystemEvent] = []
        self.event_lock = asyncio.Lock()
        
        # Состояние синхронизации
        self.last_chat_time = 0
        self.last_analysis_time = 0
        self.last_autonomous_time = 0
        
        # Контекст для всех компонентов
        self.shared_context: Dict[str, Any] = {}
        self.context_lock = asyncio.Lock()
        
        logger.info("🧠 IntegrationHub: Initialized")
    
    def register_components(self, autonomous_core: AutonomousCore, system_agent: SystemAnalysisAgent):
        """Регистрирует компоненты для синхронизации"""
        self.autonomous_core = autonomous_core
        self.system_agent = system_agent
        
        # Интегрируем компоненты
        if self.system_agent:
            self.system_agent.integrate_with_autonomous_core(autonomous_core)
        
        logger.info("🧠 IntegrationHub: Components registered")
    
    async def add_event(self, event: SystemEvent):
        """Добавляет событие в центральную память"""
        async with self.event_lock:
            self.events.append(event)
            
            # Ограничиваем размер памяти событий
            if len(self.events) > 1000:
                self.events = self.events[-500:]
            
            logger.info(f"🧠 IntegrationHub: Added event {event.type} from {event.source}")
    
    async def get_recent_events(self, event_type: Optional[str] = None, limit: int = 10) -> List[SystemEvent]:
        """Получает последние события"""
        async with self.event_lock:
            events = self.events[-limit:] if self.events else []
            if event_type:
                events = [e for e in events if e.type == event_type]
            return events
    
    async def update_shared_context(self, updates: Dict[str, Any]):
        """Обновляет общий контекст"""
        async with self.context_lock:
            self.shared_context.update(updates)
            logger.info(f"🧠 IntegrationHub: Updated shared context with {len(updates)} items")
    
    async def get_shared_context(self) -> Dict[str, Any]:
        """Получает общий контекст"""
        async with self.context_lock:
            return self.shared_context.copy()
    
    # === СИНХРОНИЗАЦИЯ ЧАТА ===
    async def on_chat_message(self, username: str, message: str, ai_response: str):
        """Обрабатывает сообщение из чата"""
        try:
            # Создаем событие чата
            chat_event = SystemEvent(
                type="chat_message",
                source="chat",
                data={
                    "username": username,
                    "message": message,
                    "ai_response": ai_response,
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                priority=2  # Высокий приоритет
            )
            
            await self.add_event(chat_event)
            self.last_chat_time = time.time()
            
            # Обновляем общий контекст
            await self.update_shared_context({
                "last_chat": {
                    "username": username,
                    "message": message,
                    "ai_response": ai_response,
                    "timestamp": time.time()
                },
                "user_activity": True
            })
            
            # Уведомляем AutonomousCore
            if self.autonomous_core:
                await self.autonomous_core.add_context_task({
                    "user_message": message,
                    "ai_response": ai_response,
                    "username": username,
                    "timestamp": time.time(),
                    "source": "chat_integration"
                })
            
            # Запускаем анализ системы с учетом чата
            await self.trigger_system_analysis_with_chat_context(username, message, ai_response)
            
            logger.info(f"🧠 IntegrationHub: Chat message synchronized for {username}")
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error processing chat message: {e}")
    
    async def trigger_system_analysis_with_chat_context(self, username: str, message: str, ai_response: str):
        """Запускает анализ системы с учетом контекста чата"""
        try:
            if not self.system_agent:
                return

            # Создаем расширенный контекст
            enhanced_context = {
                "chat_context": {
                    "username": username,
                    "message": message,
                    "ai_response": ai_response
                },
                "shared_context": await self.get_shared_context(),
                "recent_events": [e.data for e in await self.get_recent_events(limit=5)]
            }
            
            # Запускаем анализ
            analysis_result = await self.system_agent.synthesize_with_autonomous_context(enhanced_context)
            
            # Создаем событие анализа
            analysis_event = SystemEvent(
                type="system_analysis",
                source="analysis",
                data={
                    "analysis_result": analysis_result,
                    "chat_context": enhanced_context["chat_context"],
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                priority=1
            )
            
            await self.add_event(analysis_event)
            self.last_analysis_time = time.time()
            
            # Обновляем общий контекст
            await self.update_shared_context({
                "last_analysis": analysis_result,
                "analysis_timestamp": time.time()
            })
            
            logger.info(f"🧠 IntegrationHub: System analysis triggered with chat context")
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error triggering system analysis: {e}")
    
    # === СИНХРОНИЗАЦИЯ АВТОНОМНОЙ РАБОТЫ ===
    async def on_autonomous_task_completed(self, task: AutonomousTask):
        """Обрабатывает завершение автономной задачи"""
        try:
            # Создаем событие автономной работы
            autonomous_event = SystemEvent(
                type="autonomous_task",
                source="autonomous",
                data={
                    "task_id": task.id,
                    "task_type": task.type,
                    "task_result": task.result,
                    "task_status": task.status,
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                priority=1
            )
            
            await self.add_event(autonomous_event)
            self.last_autonomous_time = time.time()
            
            # Обновляем общий контекст
            await self.update_shared_context({
                "last_autonomous_task": {
                    "type": task.type,
                    "result": task.result,
                    "status": task.status,
                    "timestamp": time.time()
                }
            })
            
            # Если задача важная, запускаем анализ
            if task.priority >= 2 or "error" in task.result.lower():
                await self.trigger_system_analysis_with_autonomous_context(task)
            
            logger.info(f"🧠 IntegrationHub: Autonomous task synchronized: {task.type}")
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error processing autonomous task: {e}")
    
    async def trigger_system_analysis_with_autonomous_context(self, task: AutonomousTask):
        """Запускает анализ системы с учетом автономной работы"""
        try:
            if not self.system_agent:
                return

            # Создаем расширенный контекст
            enhanced_context = {
                "autonomous_context": {
                    "task_type": task.type,
                    "task_result": task.result,
                    "task_status": task.status
                },
                "shared_context": await self.get_shared_context(),
                "recent_events": [e.data for e in await self.get_recent_events(limit=5)]
            }
            
            # Запускаем анализ
            analysis_result = await self.system_agent.synthesize_with_autonomous_context(enhanced_context)
            
            # Создаем событие анализа
            analysis_event = SystemEvent(
                type="system_analysis",
                source="analysis",
                data={
                    "analysis_result": analysis_result,
                    "autonomous_context": enhanced_context["autonomous_context"],
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                priority=1
            )
            
            await self.add_event(analysis_event)
            self.last_analysis_time = time.time()
            
            logger.info(f"🧠 IntegrationHub: System analysis triggered with autonomous context")
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error triggering autonomous analysis: {e}")
    
    # === ПОЛУЧЕНИЕ СИНХРОНИЗИРОВАННОГО КОНТЕКСТА ===
    async def get_synchronized_context(self) -> Dict[str, Any]:
        """Получает полностью синхронизированный контекст"""
        try:
            shared_context = await self.get_shared_context()
            recent_events = await self.get_recent_events(limit=10)
            
            # Создаем синхронизированный контекст
            synchronized_context = {
                "shared_context": shared_context,
                "recent_events": [e.data for e in recent_events],
                "timestamps": {
                    "last_chat": self.last_chat_time,
                    "last_analysis": self.last_analysis_time,
                    "last_autonomous": self.last_autonomous_time
                },
                "system_status": {
                    "autonomous_core_running": self.autonomous_core.is_running if self.autonomous_core else False,
                    "system_agent_available": self.system_agent is not None,
                    "event_count": len(self.events)
                }
            }
            
            return synchronized_context
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error getting synchronized context: {e}")
            return {}
    
    # === ПЕРИОДИЧЕСКАЯ СИНХРОНИЗАЦИЯ ===
    async def run_synchronization_loop(self):
        """Запускает цикл синхронизации"""
        logger.info("🧠 IntegrationHub: Starting synchronization loop")
        
        # ЗАПУСКАЕМ АНАЛИЗ СРАЗУ ПРИ СТАРТЕ!
        logger.info("🧠 IntegrationHub: Running initial analysis...")
        await self.trigger_periodic_analysis()
        
        while True:
            try:
                # Получаем синхронизированный контекст
                context = await self.get_synchronized_context()
                
                # Обновляем контекст в AutonomousCore
                if self.autonomous_core:
                    await self.autonomous_core.update_shared_context(context)
                
                # Проверяем необходимость анализа
                time_since_analysis = time.time() - self.last_analysis_time
                if time_since_analysis > 600:  # 10 минут вместо 5
                    await self.trigger_periodic_analysis()
                
                # Пауза между синхронизациями
                await asyncio.sleep(60)  # 1 минута вместо 30 секунд
                
            except Exception as e:
                logger.error(f"🧠 IntegrationHub: Error in synchronization loop: {e}")
                await asyncio.sleep(60)
    
    async def trigger_periodic_analysis(self):
        """Запускает периодический анализ"""
        try:
            if not self.system_agent:
                return
            
            context = await self.get_synchronized_context()
            analysis_result = await self.system_agent.synthesize_with_autonomous_context(context)
            
            # Создаем событие периодического анализа
            periodic_event = SystemEvent(
                type="periodic_analysis",
                source="integration",
                data={
                    "analysis_result": analysis_result,
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                priority=1
            )
            
            await self.add_event(periodic_event)
            self.last_analysis_time = time.time()
            
            logger.info(f"🧠 IntegrationHub: Periodic analysis completed")
            
        except Exception as e:
            logger.error(f"🧠 IntegrationHub: Error in periodic analysis: {e}")
    
    # === СТАТУС СИНХРОНИЗАЦИИ ===
    async def get_synchronization_status(self) -> Dict[str, Any]:
        """Получает статус синхронизации"""
        return {
            "components_registered": {
                "autonomous_core": self.autonomous_core is not None,
                "system_agent": self.system_agent is not None
            },
            "last_activities": {
                "chat": self.last_chat_time,
                "analysis": self.last_analysis_time,
                "autonomous": self.last_autonomous_time
            },
            "event_stats": {
                "total_events": len(self.events),
                "recent_events": len([e for e in self.events if time.time() - e.timestamp < 300])
            },
            "shared_context_size": len(self.shared_context)
        }


