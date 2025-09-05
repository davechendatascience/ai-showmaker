"""
Exception classes for AI-Showmaker MCP servers
"""

class AIShowmakerError(Exception):
    """Base exception for AI-Showmaker errors"""
    pass

class ToolError(AIShowmakerError):
    """Exception raised when tool execution fails"""
    pass

class ValidationError(AIShowmakerError):
    """Exception raised when validation fails"""
    pass

class ConnectionError(AIShowmakerError):
    """Exception raised when connection fails"""
    pass

class SecurityError(AIShowmakerError):
    """Exception raised when security validation fails"""
    pass
