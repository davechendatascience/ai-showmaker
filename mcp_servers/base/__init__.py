"""
Base MCP Server Classes

This module provides the foundational classes and interfaces for all
AI-Showmaker MCP servers. All domain-specific servers inherit from these base classes.
"""

from .server import AIShowmakerMCPServer, MCPTool, MCPToolResult

__all__ = [
    'AIShowmakerMCPServer',
    'MCPTool',
    'MCPToolResult'
]