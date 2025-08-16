"""
🧠 Autonomous Module - AGI автономные компоненты
"""

from .core import AutonomousCore, AutonomousMemory, ContextAnalyzer, AutonomousTask, AutonomousContext
from .system_analysis_agent import SystemAnalysisAgent
from .background_loop import AutonomousSupervisor
from .integration_hub import IntegrationHub, SystemEvent

__all__ = [
    'AutonomousCore',
    'AutonomousMemory', 
    'ContextAnalyzer',
    'AutonomousTask',
    'AutonomousContext',
    'SystemAnalysisAgent',
    'AutonomousSupervisor',
    'IntegrationHub',
    'SystemEvent'
]


