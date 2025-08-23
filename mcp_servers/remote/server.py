"""
Remote Operations MCP Server Implementation

Provides secure SSH/SFTP operations with connection pooling,
security validation, and comprehensive error handling.
"""

import os
import json
import time
import paramiko
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Optional

from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool
from core.exceptions import SecurityError, ConnectionError


class SSHConnectionPool:
    """Thread-safe SSH connection pool for reusing connections."""
    
    def __init__(self, max_connections: int = 5, connection_timeout: int = 300):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.connections = {}
        self.lock = threading.Lock()
    
    def _create_connection(self) -> paramiko.SSHClient:
        """Create a new SSH connection."""
        key = paramiko.Ed25519Key.from_private_key_file(os.environ["PEM_PATH"])
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=os.environ["AWS_HOST"],
            username=os.environ["AWS_USER"],
            pkey=key,
            timeout=30
        )
        return ssh
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)."""
        connection_key = f"{os.environ['AWS_HOST']}:{os.environ['AWS_USER']}"
        
        with self.lock:
            if connection_key not in self.connections:
                self.connections[connection_key] = {
                    'client': self._create_connection(),
                    'last_used': time.time(),
                    'in_use': False
                }
        
        conn_info = self.connections[connection_key]
        
        # Check if connection is still alive
        try:
            transport = conn_info['client'].get_transport()
            if not transport or not transport.is_active():
                conn_info['client'] = self._create_connection()
        except:
            conn_info['client'] = self._create_connection()
        
        conn_info['in_use'] = True
        conn_info['last_used'] = time.time()
        
        try:
            yield conn_info['client']
        finally:
            conn_info['in_use'] = False


def validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attacks."""
    # Convert to Path object for better handling
    path = Path(filename)
    
    # Check for path traversal attempts
    if '..' in filename or filename.startswith('/'):
        raise SecurityError(f"Path traversal detected in '{filename}'")
    
    # Check for absolute paths on Windows
    if path.is_absolute():
        raise SecurityError(f"Absolute paths not allowed '{filename}'")
    
    # Restrict to reasonable file extensions
    allowed_extensions = {'.py', '.txt', '.js', '.html', '.css', '.json', '.md', '.yml', '.yaml', '.sh', '.conf'}
    if path.suffix and path.suffix.lower() not in allowed_extensions:
        raise SecurityError(f"File extension '{path.suffix}' not allowed. Allowed: {sorted(allowed_extensions)}")
    
    return filename


class RemoteMCPServer(AIShowmakerMCPServer):
    """MCP Server for remote server operations via SSH/SFTP."""
    
    def __init__(self):
        super().__init__(
            name="remote",
            version="2.0.0",
            description="Secure remote server operations with SSH and SFTP"
        )
        self.ssh_pool = SSHConnectionPool()
    
    async def initialize(self) -> None:
        """Initialize the remote server and register tools."""
        
        # Register command execution tool
        execute_command_tool = MCPTool(
            name="execute_command",
            description="Execute commands on remote server. Required parameter: command (string). Optional: input_data (string for interactive programs)",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute on remote server"
                    },
                    "input_data": {
                        "type": "string",
                        "description": "Optional input data for interactive programs (use \\n for newlines)",
                        "default": ""
                    }
                },
                "required": ["command"]
            },
            execute_func=self._execute_command,
            category="execution",
            timeout=60
        )
        self.register_tool(execute_command_tool)
        
        # Register file writing tool
        write_file_tool = MCPTool(
            name="write_file", 
            description="Write files to remote server via SFTP. Required parameters: filename (string) and content (string)",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of file to create (relative path only)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["filename", "content"]
            },
            execute_func=self._write_file,
            category="files",
            timeout=30
        )
        self.register_tool(write_file_tool)
        
        # Register file reading tool
        read_file_tool = MCPTool(
            name="read_file",
            description="Read file content from remote server via SFTP. Required parameter: filename (string)", 
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of file to read"
                    }
                },
                "required": ["filename"]
            },
            execute_func=self._read_file,
            category="files",
            timeout=30
        )
        self.register_tool(read_file_tool)
        
        # Register directory listing tool
        list_directory_tool = MCPTool(
            name="list_directory",
            description="List contents of directory on remote server. Optional parameter: path (string, defaults to current directory)",
            parameters={
                "type": "object", 
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current directory)",
                        "default": "."
                    }
                }
            },
            execute_func=self._list_directory,
            category="files",
            timeout=15
        )
        self.register_tool(list_directory_tool)
        
        self.logger.info(f"Remote MCP Server initialized with {len(self.tools)} tools")
    
    async def _execute_command(self, command: str, input_data: str = "") -> str:
        """Execute command on remote server with optional input."""
        try:
            # Create command with input piping if needed
            if input_data:
                # Use printf to handle newlines properly for interactive programs
                piped_command = f"printf '{input_data}\\n' | {command}"
            else:
                piped_command = command
            
            with self.ssh_pool.get_connection() as ssh:
                # Execute command with timeout
                stdin, stdout, stderr = ssh.exec_command(piped_command, timeout=30)
                
                # Wait for command completion and get exit code
                exit_code = stdout.channel.recv_exit_status()
                
                # Read output with proper decoding
                stdout_text = stdout.read().decode('utf-8', errors='replace')
                stderr_text = stderr.read().decode('utf-8', errors='replace')
                
                # Format output with exit code
                result = f"Exit Code: {exit_code}\\n"
                if stdout_text:
                    result += f"STDOUT:\\n{stdout_text}"
                if stderr_text:
                    result += f"STDERR:\\n{stderr_text}"
                if not stdout_text and not stderr_text:
                    result += "No output"
                
                self.logger.info(f"Executed command: {command} (exit code: {exit_code})")
                return result
                
        except paramiko.AuthenticationException:
            raise ConnectionError(os.environ.get("AWS_HOST", "unknown"), "SSH authentication failed")
        except paramiko.SSHException as e:
            raise ConnectionError(os.environ.get("AWS_HOST", "unknown"), f"SSH error: {str(e)}")
        except Exception as e:
            raise Exception(f"Command execution failed: {str(e)}")
    
    async def _write_file(self, filename: str, content: str) -> str:
        """Write file to remote server via SFTP."""
        try:
            # Validate filename for security
            filename = validate_filename(filename)
            
            with self.ssh_pool.get_connection() as ssh:
                sftp = ssh.open_sftp()
                
                # Create directory if it doesn't exist
                file_path = Path(filename)
                if file_path.parent != Path('.'):
                    try:
                        sftp.mkdir(str(file_path.parent))
                    except FileExistsError:
                        pass  # Directory already exists
                    except Exception:
                        # Try to create parent directories recursively
                        try:
                            ssh.exec_command(f"mkdir -p {file_path.parent}")
                        except:
                            pass  # Continue anyway, might still work
                
                # Write file
                with sftp.open(filename, 'w') as f:
                    f.write(content)
                
                # Get file size for confirmation
                stat = sftp.stat(filename)
                file_size = stat.st_size
                
                sftp.close()
                
                self.logger.info(f"Wrote file: {filename} ({file_size} bytes)")
                return f"File '{filename}' written successfully ({file_size} bytes)"
                
        except SecurityError as e:
            raise e
        except Exception as e:
            raise Exception(f"File write failed: {str(e)}")
    
    async def _read_file(self, filename: str) -> str:
        """Read file from remote server via SFTP."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                sftp = ssh.open_sftp()
                
                try:
                    with sftp.open(filename, 'r') as f:
                        content = f.read()
                    
                    self.logger.info(f"Read file: {filename} ({len(content)} bytes)")
                    return content
                    
                except FileNotFoundError:
                    raise Exception(f"File '{filename}' not found")
                finally:
                    sftp.close()
                    
        except Exception as e:
            raise Exception(f"File read failed: {str(e)}")
    
    async def _list_directory(self, path: str = ".") -> str:
        """List directory contents on remote server."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                stdin, stdout, stderr = ssh.exec_command(f"ls -la {path}")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    output = stdout.read().decode('utf-8', errors='replace')
                    self.logger.info(f"Listed directory: {path}")
                    return output
                else:
                    error = stderr.read().decode('utf-8', errors='replace')
                    raise Exception(f"Directory listing failed: {error}")
                    
        except Exception as e:
            raise Exception(f"Directory listing failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown the remote server."""
        self.logger.info("Remote MCP Server shutting down")
        # Close any active connections
        for conn_info in self.ssh_pool.connections.values():
            try:
                conn_info['client'].close()
            except:
                pass
        self.ssh_pool.connections.clear()