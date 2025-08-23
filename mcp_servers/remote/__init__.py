"""
Remote Operations MCP Server

This server provides secure remote server management tools including:
- SSH command execution
- SFTP file operations
- Interactive command support
- Connection pooling and management
"""

from .server import RemoteMCPServer

__all__ = ['RemoteMCPServer']