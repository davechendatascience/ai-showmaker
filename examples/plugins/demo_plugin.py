"""
Demo Plugin for MCP-Zero

This is a simple example plugin that demonstrates how to create
custom MCP servers that can be discovered and loaded dynamically.
"""

from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool
from typing import Dict, Any


class DemoPluginServer(AIShowmakerMCPServer):
    """
    Demo plugin server with example tools.
    
    This server demonstrates the MCP-Zero plugin system by providing
    simple utility tools that can be discovered and used by the agent.
    """
    
    def __init__(self):
        super().__init__(
            name="demo_plugin",
            version="1.0.0",
            description="Demo plugin server for MCP-Zero testing"
        )
        
    async def initialize(self) -> None:
        """Initialize the demo plugin server."""
        # Register demo tools
        self.register_tool(MCPTool(
            name="demo_hello",
            description="A simple hello world tool",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to greet"
                    }
                },
                "required": ["name"]
            },
            execute_func=self.demo_hello,
            category="demo",
            version="1.0.0"
        ))
        
        self.register_tool(MCPTool(
            name="demo_calculator",
            description="A simple calculator tool",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Mathematical operation (add, subtract, multiply, divide)",
                        "enum": ["add", "subtract", "multiply", "divide"]
                    },
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["operation", "a", "b"]
            },
            execute_func=self.demo_calculator,
            category="demo",
            version="1.0.0"
        ))
        
        self.register_tool(MCPTool(
            name="demo_status",
            description="Get the status of the demo plugin",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            execute_func=self.demo_status,
            category="demo",
            version="1.0.0"
        ))
        
        self.logger.info(f"Demo plugin initialized with {len(self.tools)} tools")
        
    async def demo_hello(self, name: str) -> str:
        """Demo hello world tool."""
        return f"Hello, {name}! Welcome to MCP-Zero plugin system! 🎉"
        
    async def demo_calculator(self, operation: str, a: float, b: float) -> str:
        """Demo calculator tool."""
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return "Error: Division by zero"
                result = a / b
            else:
                return f"Error: Unknown operation '{operation}'"
                
            return f"{a} {operation} {b} = {result}"
            
        except Exception as e:
            return f"Error in calculation: {str(e)}"
            
    async def demo_status(self) -> str:
        """Get demo plugin status."""
        return f"Demo plugin is running! Server: {self.name}, Version: {self.version}, Tools: {len(self.tools)}"
        
    async def shutdown(self) -> None:
        """Shutdown the demo plugin server."""
        self.logger.info("Demo plugin server shutting down")

