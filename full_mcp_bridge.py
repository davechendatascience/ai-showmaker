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
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List
import threading
import uuid
try:
    import paramiko  # type: ignore
except Exception:
    paramiko = None
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path so we can import MCP servers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class FullMCPBridge:
    """Full bridge that loads all available MCP servers."""
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        # Remote logs pub/sub
        self._remote_log_subscribers: List[Any] = []
        self._remote_log_buffer: List[str] = []
        # Interactive SSH sessions
        self._remote_sessions: Dict[str, Dict[str, Any]] = {}
        
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

            # Map MCPToolResult to HTTP response honoring success/error
            if hasattr(result, 'result_type'):
                status_obj = getattr(result, 'result_type')
                status_val = getattr(status_obj, 'value', str(status_obj)).lower()
                success = status_val == 'success'
            else:
                success = True

            resp = {
                "success": success,
                "result": getattr(result, 'data', None),
                "message": getattr(result, 'message', "Tool executed successfully"),
                "execution_time": getattr(result, 'execution_time', 0.0),
                "server": server_name,
                "tool": tool_name
            }
            if not success:
                resp["error"] = getattr(result, 'message', 'Tool execution failed')
            return resp
            
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

    # --- Remote Logs Pub/Sub ---
    def _publish_remote_log(self, line: str):
        try:
            self._remote_log_buffer.append(line)
            if len(self._remote_log_buffer) > 500:
                self._remote_log_buffer = self._remote_log_buffer[-500:]
            for cb in list(self._remote_log_subscribers):
                try:
                    cb(line)
                except Exception:
                    pass
        except Exception:
            pass

    def subscribe_remote_logs(self, callback):
        self._remote_log_subscribers.append(callback)
        return lambda: self._remote_log_subscribers.remove(callback)

    def get_remote_log_buffer(self):
        return list(self._remote_log_buffer)

    # ---- Interactive SSH session helpers ----
    def _get_remote_server(self):
        return self.servers.get('remote', {}).get('instance') if 'remote' in self.servers else None

    def create_remote_session(self, cwd: str = None) -> Dict[str, Any]:
        if paramiko is None:
            raise RuntimeError("paramiko not available on bridge host")
        remote = self._get_remote_server()
        if not remote:
            raise RuntimeError("Remote server not loaded")

        # Create a dedicated SSH connection
        try:
            client = remote.ssh_pool._create_connection()  # type: ignore[attr-defined]
            client.get_transport().set_keepalive(30)
        except Exception as e:
            raise RuntimeError(f"SSH connection failed: {e}")

        try:
            chan = client.invoke_shell(term='xterm', width=120, height=32)
            try:
                chan.set_combine_stderr(True)
            except Exception:
                pass
            chan.settimeout(0.0)
        except Exception as e:
            try:
                client.close()
            except Exception:
                pass
            raise RuntimeError(f"Failed to open interactive shell: {e}")

        session_id = str(uuid.uuid4())
        session = {
            'id': session_id,
            'client': client,
            'channel': chan,
            'buffer': [],
            'subscribers': [],
            'closed': False,
        }

        def publish(text: str):
            try:
                session['buffer'].append(text)
                if len(session['buffer']) > 2000:
                    session['buffer'] = session['buffer'][-2000:]
                for cb in list(session['subscribers']):
                    try:
                        cb(text)
                    except Exception:
                        pass
            except Exception:
                pass

        def reader():
            try:
                while not session['closed']:
                    try:
                        if chan.recv_ready():
                            data = chan.recv(4096)
                            if not data:
                                break
                            text = data.decode('utf-8', errors='replace')
                            publish(text)
                        else:
                            time.sleep(0.03)
                    except Exception:
                        time.sleep(0.05)
            finally:
                session['closed'] = True
                try:
                    chan.close()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        if cwd:
            try:
                chan.send(f"cd {cwd}\n")
            except Exception:
                pass
        # Nudge prompt to appear
        try:
            chan.send('\r')
        except Exception:
            pass

        self._remote_sessions[session_id] = session
        return {'session_id': session_id}

    def close_remote_session(self, session_id: str) -> Dict[str, Any]:
        session = self._remote_sessions.get(session_id)
        if not session:
            return {'ok': False, 'message': 'Unknown session'}
        session['closed'] = True
        try:
            session['channel'].close()
        except Exception:
            pass
        try:
            session['client'].close()
        except Exception:
            pass
        return {'ok': True}

    def send_remote_session(self, session_id: str, data: str) -> Dict[str, Any]:
        session = self._remote_sessions.get(session_id)
        if not session or session.get('closed'):
            return {'ok': False, 'message': 'Session not available'}
        try:
            # Normalize to LF for shell and ensure newline at end
            payload = data.replace('\r\n', '\n').replace('\r', '\n')
            if not payload.endswith('\n'):
                payload += '\n'
            # Also send CR to satisfy shells expecting carriage return
            payload += '\r'
            # Publish a mirror of user input for UI visibility
            try:
                preview = data.replace('\r', '').replace('\n', '')
                for cb in list(session['subscribers']):
                    try:
                        cb(f"$ {preview}")
                    except Exception:
                        pass
            except Exception:
                pass
            sent = session['channel'].send(payload)
            try:
                print(f"[remote/session/send] wrote={sent}/{len(payload.encode('utf-8', errors='ignore'))} bytes")
            except Exception:
                pass
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    def subscribe_remote_session(self, session_id: str, callback):
        session = self._remote_sessions.get(session_id)
        if not session:
            raise RuntimeError('Unknown session')
        session['subscribers'].append(callback)
        return lambda: session['subscribers'].remove(callback)

    def get_remote_session_buffer(self, session_id: str):
        session = self._remote_sessions.get(session_id)
        return list(session['buffer']) if session else []

class FullMCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the full MCP bridge."""
    protocol_version = "HTTP/1.1"
    
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
            
            elif path == '/execute_get':
                # Execute tool via GET to avoid body issues on some clients
                qs = parse_qs(parsed_path.query)
                tool_name = (qs.get('tool_name') or [''])[0]
                params_raw = (qs.get('params') or ['{}'])[0]
                try:
                    params = json.loads(params_raw)
                except Exception:
                    params = {}
                if not tool_name:
                    self.send_json_response(400, { 'success': False, 'error': 'tool_name is required' })
                else:
                    result = self.bridge.execute_tool_sync(tool_name, params)
                    self.send_json_response(200, result)
            
            elif path == '/remote-logs':
                # SSE stream of remote logs
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()

                def send_sse(data: str):
                    try:
                        for line in str(data).splitlines() or ['']:
                            self.wfile.write(f"data: {line}\n".encode('utf-8', errors='ignore'))
                        self.wfile.write(b"\n")
                    except Exception:
                        try:
                            unsubscribe()
                        except Exception:
                            pass

                for line in self.bridge.get_remote_log_buffer():
                    send_sse(line)

                unsubscribe = self.bridge.subscribe_remote_logs(send_sse)
                try:
                    while True:
                        time.sleep(15)
                        try:
                            self.wfile.write(b": keep-alive\n\n")
                        except Exception:
                            break
                finally:
                    try:
                        unsubscribe()
                    except Exception:
                        pass

            elif path == '/remote/session/stream':
                # Interactive SSH session stream via SSE
                qs = parse_qs(parsed_path.query)
                session_id = (qs.get('id') or [''])[0]
                if not session_id:
                    self.send_json_response(400, {"error": "Missing session id"}); return

                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()

                def send_line(data: str):
                    try:
                        for line in str(data).splitlines() or ['']:
                            self.wfile.write(f"data: {line}\n".encode('utf-8', errors='ignore'))
                        self.wfile.write(b"\n")
                    except Exception:
                        try:
                            unsubscribe()
                        except Exception:
                            pass

                for line in self.bridge.get_remote_session_buffer(session_id):
                    send_line(line)

                try:
                    unsubscribe = self.bridge.subscribe_remote_session(session_id, send_line)
                except Exception as e:
                    self.send_json_response(404, {"error": str(e)}); return
                try:
                    while True:
                        time.sleep(15)
                        try:
                            self.wfile.write(b": keep-alive\n\n")
                        except Exception:
                            break
                finally:
                    try:
                        unsubscribe()
                    except Exception:
                        pass
                
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not found')
                
        except Exception as e:
            print(f"❌ GET request error: {e}")
            self.send_json_response(500, {"error": str(e)})
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            print(f"[HTTP] POST {self.path}")
        except Exception:
            pass
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
        elif self.path == '/remote/session/start':
            try:
                content_length = int(self.headers.get('Content-Length', 0) or 0)
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                cwd = data.get('cwd')
                result = self.bridge.create_remote_session(cwd)
                self.send_json_response(200, {'success': True, **result})
            except Exception as e:
                self.send_json_response(400, {'success': False, 'error': str(e)})
        elif self.path == '/remote/session/send':
            try:
                content_length = int(self.headers.get('Content-Length', 0) or 0)
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                sid = data.get('session_id'); payload = data.get('data', '')
                if not sid:
                    raise ValueError('Missing session_id')
                # Debug log for troubleshooting input path
                try:
                    print(f"[remote/session/send] sid={sid} bytes={len(payload.encode('utf-8', errors='ignore'))}")
                except Exception:
                    pass
                result = self.bridge.send_remote_session(sid, payload)
                self.send_json_response(200, result)
            except Exception as e:
                self.send_json_response(400, {'ok': False, 'error': str(e)})
        elif self.path == '/remote/session/close':
            try:
                content_length = int(self.headers.get('Content-Length', 0) or 0)
                raw = self.rfile.read(content_length) if content_length else b'{}'
                data = json.loads(raw.decode('utf-8')) if raw else {}
                sid = data.get('session_id')
                if not sid:
                    raise ValueError('Missing session_id')
                result = self.bridge.close_remote_session(sid)
                self.send_json_response(200, result)
            except Exception as e:
                self.send_json_response(400, {'ok': False, 'error': str(e)})
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
    
    def send_json_response(self, status_code: int, data: Any):
        """Send a JSON response."""
        try:
            body = json.dumps(data).encode('utf-8')
        except Exception:
            body = b'{}'
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass
    
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
    # Attach remote server log handler after initialization
    try:
        import logging
        remote = bridge.servers.get('remote', {}).get('instance') if 'remote' in bridge.servers else None
        if remote and getattr(remote, 'logger', None):
            class BridgeLogHandler(logging.Handler):
                def __init__(self, bridge_ref):
                    super().__init__()
                    self.bridge_ref = bridge_ref
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        self.bridge_ref._publish_remote_log(msg)
                    except Exception:
                        pass
            handler = BridgeLogHandler(bridge)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            remote.logger.addHandler(handler)
            remote.logger.propagate = False
    except Exception as e:
        print(f"⚠️ Failed to attach remote log handler: {e}")
    
    # Create HTTP server
    port = 8000
    handler = create_handler(bridge)
    
    try:
        class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
        with ThreadingHTTPServer(('localhost', port), handler) as httpd:
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
