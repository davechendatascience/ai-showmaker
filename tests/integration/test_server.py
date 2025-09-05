#!/usr/bin/env python3
"""
Simple MCP Server for testing TypeScript communication
"""

import json
import sys
import time
from typing import Dict, Any

class SimpleMCPServer:
    def __init__(self):
        self.name = "test_server"
        self.version = "1.0.0"
        self.tools = {
            "calculate": {
                "name": "calculate",
                "description": "Calculate mathematical expressions",
                "parameters": {"expression": "string"},
                "category": "mathematics"
            },
            "echo": {
                "name": "echo",
                "description": "Echo back the input",
                "parameters": {"message": "string"},
                "category": "utility"
            }
        }
        
    def list_tools(self) -> list:
        """List available tools"""
        return list(self.tools.values())
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool"""
        if tool_name == "calculate":
            try:
                expression = params.get("expression", "0")
                result = eval(expression)
                return {"result": result, "expression": expression}
            except Exception as e:
                return {"error": str(e), "expression": params.get("expression")}
        
        elif tool_name == "echo":
            message = params.get("message", "")
            return {"echo": message, "timestamp": time.time()}
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def run(self):
        """Run the server in a simple loop"""
        print(f"🚀 Starting {self.name} v{self.version}", file=sys.stderr)
        print(f"📋 Available tools: {list(self.tools.keys())}", file=sys.stderr)
        
        try:
            while True:
                # Simple command loop for testing
                command = input().strip()
                if command == "list_tools":
                    response = self.list_tools()
                    print(json.dumps(response))
                elif command == "exit":
                    break
                elif command.startswith("execute:"):
                    try:
                        parts = command.split(":", 2)
                        tool_name = parts[1]
                        params_str = parts[2] if len(parts) > 2 else "{}"
                        params = json.loads(params_str)
                        result = self.execute_tool(tool_name, params)
                        print(json.dumps(result))
                    except Exception as e:
                        print(json.dumps({"error": str(e)}))
                else:
                    print(json.dumps({"error": f"Unknown command: {command}"}))
                    
        except KeyboardInterrupt:
            print("🛑 Server stopped by user", file=sys.stderr)
        except EOFError:
            print("🛑 Server stopped (EOF)", file=sys.stderr)
        finally:
            print("✅ Server shutdown complete", file=sys.stderr)

if __name__ == "__main__":
    server = SimpleMCPServer()
    server.run()
