"""
AI-Showmaker Core Module

This module contains the core agent logic, configuration management,
and base classes for the AI-Showmaker development agent framework.
"""

from .agent import AIShowmakerAgent
from .config import ConfigManager
from .exceptions import AIShowmakerError, ToolError, ConnectionError

__version__ = "2.0.0"
__author__ = "AI-Showmaker Team"

__all__ = [
    'AIShowmakerAgent',
    'ConfigManager', 
    'AIShowmakerError',
    'ToolError',
    'ConnectionError'
]