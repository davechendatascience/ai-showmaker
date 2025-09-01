"""
AI-Showmaker Core Module

This module contains the core agent logic, configuration management,
and base classes for the AI-Showmaker development agent framework.
"""

# Core exports
from .config import ConfigManager
from .exceptions import AIShowmakerError, ToolError, ConnectionError
from .agent import UnifiedAIShowmakerAgent, AIShowmakerAgent

__version__ = "2.0.0"
__author__ = "AI-Showmaker Team"

__all__ = [
    'ConfigManager', 
    'AIShowmakerError',
    'ToolError',
    'ConnectionError',
    'UnifiedAIShowmakerAgent',
    'AIShowmakerAgent'
]