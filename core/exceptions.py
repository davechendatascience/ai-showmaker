"""
Custom exceptions for AI-Showmaker agent framework.
"""

class AIShowmakerError(Exception):
    """Base exception for all AI-Showmaker related errors."""
    pass

class ToolError(AIShowmakerError):
    """Exception raised when a tool fails to execute properly."""
    
    def __init__(self, tool_name: str, message: str, details: str = None):
        self.tool_name = tool_name
        self.details = details
        super().__init__(f"Tool '{tool_name}' failed: {message}")

class ConnectionError(AIShowmakerError):
    """Exception raised when connection to remote server fails."""
    
    def __init__(self, host: str, message: str, port: int = 22):
        self.host = host
        self.port = port
        super().__init__(f"Connection to {host}:{port} failed: {message}")

class ConfigurationError(AIShowmakerError):
    """Exception raised when configuration is invalid or missing."""
    pass

class SecurityError(AIShowmakerError):
    """Exception raised when security validation fails."""
    pass

class ValidationError(AIShowmakerError):
    """Exception raised when input validation fails."""
    pass