#!/usr/bin/env python3
"""
Full MCP Bridge - Loads all available MCP servers for testing
"""

import asyncio
import json
import sys
import os
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, Any, List

# Add the parent directory to the path so we can import MCP servers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class FullMCPBridge:
    """Full bridge that loads all available MCP servers."""
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the bridge with all available servers."""
        print("🔍 Initializing Full MCP Bridge...")
        
        # List of servers to load
        server_configs = [
            ("calculation", "mcp_servers.calculation.server", "CalculationMCPServer"),
            ("development", "mcp_servers.development.server", "DevelopmentMCPServer"),
            ("monitoring", "mcp_servers.monitoring.server", "MonitoringMCPServer"),
            ("remote", "mcp_servers.remote.server", "RemoteMCPServer"),
            ("websearch", "mcp_servers.websearch.server", "WebSearchMCPServer"),
        ]
        
        for server_name, module_path, class_name in server_configs:
            try:
                await self.load_server(server_name, module_path, class_name)
            except Exception as e:
                print(f"⚠️ Failed to load {server_name} server: {e}")
                # Continue loading other servers even if one fails
        
        print(f"✅ Full MCP Bridge initialized with {len(self.servers)} servers and {len(self.tools)} tools")
    
    async def load_server(self, server_name: str, module_path: str, class_name: str):
        """Load a single MCP server."""
        print(f"🔧 Loading {server_name} server...")
        
        try:
            # Import the server module
            module = __import__(module_path, fromlist=[class_name])
            server_class = getattr(module, class_name)
            
            # Create and initialize the server
            server_instance = server_class()
            await server_instance.initialize()
            
            # Store the server
            self.servers[server_name] = {
                'instance': server_instance,
                'name': server_name,
                'tools': {}
            }
            
            # Extract tools
            for tool_name, tool in server_instance.tools.items():
                self.tools[tool_name] = {
                    'name': tool_name,
                    'description': tool.description,
                    'parameters': tool.parameters,
                    'server': server_name
                }
                self.servers[server_name]['tools'][tool_name] = tool
            
            print(f"✅ Loaded {server_name} server with {len(server_instance.tools)} tools")
            
        except Exception as e:
            print(f"❌ Failed to load {server_name} server: {e}")
            traceback.print_exc()
            raise
    
    def list_tools(self):
        """List all available tools."""
        return list(self.tools.values())
    
    def execute_tool_sync(self, tool_name: str, params: Dict[str, Any]):
        """Execute a tool synchronously."""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        tool_info = self.tools[tool_name]
        server_name = tool_info['server']
        
        if server_name not in self.servers:
            return {
                "success": False,
                "error": f"Server '{server_name}' not found"
            }
        
        try:
            # Execute the tool synchronously using a new event loop
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def run_in_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        server_instance = self.servers[server_name]['instance']
                        result = loop.run_until_complete(server_instance.execute_tool(tool_name, params))
                        result_queue.put(('success', result))
                    finally:
                        loop.close()
                except Exception as e:
                    result_queue.put(('error', e))
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                return {
                    "success": False,
                    "error": "Tool execution timeout",
                    "server": server_name,
                    "tool": tool_name
                }
            
            if result_queue.empty():
                return {
                    "success": False,
                    "error": "No result from tool execution",
                    "server": server_name,
                    "tool": tool_name
                }
            
            result_type, result = result_queue.get()
            
            if result_type == 'error':
                return {
                    "success": False,
                    "error": str(result),
                    "server": server_name,
                    "tool": tool_name
                }
            
            return {
                "success": True,
                "result": result.data if hasattr(result, 'data') else str(result),
                "message": result.message if hasattr(result, 'message') else "Tool executed successfully",
                "execution_time": result.execution_time if hasattr(result, 'execution_time') else 0.0,
                "server": server_name,
                "tool": tool_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server": server_name,
                "tool": tool_name
            }
    
    def get_server_info(self):
        """Get server information."""
        server_info = {}
        for server_name, server_data in self.servers.items():
            server_info[server_name] = {
                "name": server_name,
                "tools": list(server_data['tools'].keys()),
                "tool_count": len(server_data['tools'])
            }
        
        return {
            "servers": server_info,
            "total_servers": len(self.servers),
            "total_tools": len(self.tools)
        }
    
    def check_health(self):
        """Check bridge health."""
        return {
            "status": "healthy",
            "servers": len(self.servers),
            "tools": len(self.tools),
            "timestamp": time.time()
        }

class FullMCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the full MCP bridge."""
    
    def __init__(self, bridge, *args, **kwargs):
        self.bridge = bridge
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            if path == '/health':
                response = self.bridge.check_health()
                self.send_json_response(200, response)
                
            elif path == '/tools':
                response = self.bridge.list_tools()
                self.send_json_response(200, response)
                
            elif path == '/servers':
                response = self.bridge.get_server_info()
                self.send_json_response(200, response)
                
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not found')
                
        except Exception as e:
            print(f"❌ GET request error: {e}")
            self.send_json_response(500, {"error": str(e)})
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/execute':
            try:
                # Read request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                print(f"[DEBUG] Received POST data: {post_data.decode('utf-8')}")
                data = json.loads(post_data.decode('utf-8'))
                tool_name = data.get('tool_name')
                params = data.get('params', {})
                
                print(f"[DEBUG] Tool name: {tool_name}, Params: {params}")
                
                if not tool_name:
                    raise ValueError("Tool name is required")
                
                # Execute the tool
                result = self.bridge.execute_tool_sync(tool_name, params)
                print(f"[DEBUG] Tool execution result: {result}")
                
                self.send_json_response(200, result)
                
            except Exception as e:
                print(f"[DEBUG] Error in POST handler: {e}")
                traceback.print_exc()
                self.send_json_response(400, {
                    'error': str(e),
                    'success': False
                })
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
    
    def send_json_response(self, status_code: int, data: Any):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Override to reduce log noise."""
        pass

def create_handler(bridge):
    """Create a request handler with the bridge instance."""
    def handler(*args, **kwargs):
        return FullMCPRequestHandler(bridge, *args, **kwargs)
    return handler

async def run_full_bridge():
    """Run the full MCP bridge."""
    print("🚀 Starting Full MCP Bridge initialization...")
    
    # Initialize bridge
    bridge = FullMCPBridge()
    await bridge.initialize()
    
    # Create HTTP server
    port = 8000
    handler = create_handler(bridge)
    
    try:
        with HTTPServer(('localhost', port), handler) as httpd:
            print(f"🚀 Starting Full MCP Bridge on http://localhost:{port}")
            print("📋 Available endpoints:")
            print("   GET  /tools     - List all tools")
            print("   GET  /servers   - Get server information")
            print("   POST /execute   - Execute a tool")
            print("   GET  /health    - Health check")
            print(f"📋 Loaded {len(bridge.servers)} servers with {len(bridge.tools)} tools")
            print("💡 Press Ctrl+C to stop the server")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Full MCP Bridge...")
        print("✅ Full MCP Bridge stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_full_bridge())
