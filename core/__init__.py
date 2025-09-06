"""
Core module for AI-Showmaker MCP servers
Minimal implementation to support MCP server functionality
"""

from .exceptions import ToolError, ValidationError, ConnectionError, SecurityError

__version__ = "2.0.0"
__author__ = "AI-Showmaker Team"

__all__ = [
    'ToolError',
    'ValidationError',
    'ConnectionError',
    'SecurityError'
]
