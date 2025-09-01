"""
MCP-Zero: Dynamic Tool Discovery & Runtime Extensibility

This package provides the foundation for making AI-Showmaker dynamically extensible
through local plugin discovery and runtime tool registration.
"""

from .server_discovery import MCPServerDiscovery
from .plugin_validator import PluginValidator

__all__ = [
    'MCPServerDiscovery',
    'PluginValidator'
]

__version__ = "1.0.0"
