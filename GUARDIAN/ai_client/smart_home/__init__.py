"""
Smart Home Module for ΔΣ Stack
Умный дом с интеграцией AI и систем безопасности

STATUS: Legacy. For reference/local experiments only.
Production control path is handled by SmartHouse Core via ai_client.tools.home_tools.HomeTools.
"""

from .core import SmartHomeController
from .sensors import SensorManager
from .actuators import ActuatorManager
from .automation import AutomationEngine
from .llm_integration import LLMHomeAssistant

__version__ = "1.0.0"
__all__ = [
    "SmartHomeController",
    "SensorManager", 
    "ActuatorManager",
    "AutomationEngine",
    "LLMHomeAssistant"
] 