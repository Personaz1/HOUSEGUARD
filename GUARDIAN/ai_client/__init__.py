"""
ΔΣ Guardian AI Client - Модульная архитектура
"""

from .core.client import AIClient
from .tools.home_tools import HomeTools

__all__ = ['AIClient', 'HomeTools']
__version__ = '2.0.0'