"""
AI-Showmaker MCP Servers

This module contains Model Context Protocol (MCP) server implementations
for the AI-Showmaker development agent framework.

Each server provides specialized tools in a specific domain:
- calculation: Mathematical operations and computations
- remote: SSH/server operations and management
- development: Git, file operations, and development workflows
- monitoring: System monitoring and metrics collection
"""

# Import base server first to avoid circular imports
from .base.server import AIShowmakerMCPServer, MCPTool, MCPToolResult

# Import individual servers
from .calculation.server import CalculationMCPServer
from .remote.server import RemoteMCPServer
from .development.server import DevelopmentMCPServer
from .monitoring.server import MonitoringMCPServer

__version__ = "2.0.0"

__all__ = [
    'AIShowmakerMCPServer',
    'MCPTool',
    'MCPToolResult',
    'CalculationMCPServer', 
    'RemoteMCPServer',
    'DevelopmentMCPServer',
    'MonitoringMCPServer'
]