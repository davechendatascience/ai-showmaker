"""
Remote Operations MCP Server Implementation

Provides secure SSH/SFTP operations with connection pooling,
security validation, and comprehensive error handling.
Includes repository management for remote development.
"""

import os
import json
import time
import paramiko
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List

from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool
from core.exceptions import SecurityError, ConnectionError


class RepositoryManager:
    """Manages repositories on the remote server."""
    
    def __init__(self, ssh_pool):
        self.ssh_pool = ssh_pool
        self.workspace_path = "/home/ec2-user/workspace"
        self.current_repo = None
        self.repositories = {}
    
    async def initialize_workspace(self) -> str:
        """Initialize the workspace directory on remote server."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                # Create workspace directory
                ssh.exec_command(f"mkdir -p {self.workspace_path}")
                ssh.exec_command(f"chmod 755 {self.workspace_path}")
                
                # Create repositories subdirectory
                repos_path = f"{self.workspace_path}/repositories"
                ssh.exec_command(f"mkdir -p {repos_path}")
                
                return f"Workspace initialized at {self.workspace_path}"
        except Exception as e:
            raise Exception(f"Failed to initialize workspace: {str(e)}")
    
    async def clone_repository(self, repo_url: str, repo_name: str, auth_token: str = None) -> str:
        """Clone a repository to the remote workspace."""
        try:
            repo_path = f"{self.workspace_path}/repositories/{repo_name}"
            
            with self.ssh_pool.get_connection() as ssh:
                # Check if repository already exists
                stdin, stdout, stderr = ssh.exec_command(f"test -d {repo_path} && echo 'exists'")
                if stdout.read().decode().strip() == 'exists':
                    return f"Repository '{repo_name}' already exists at {repo_path}"
                
                # Clone repository
                if auth_token:
                    # Use token authentication
                    if repo_url.startswith('https://'):
                        # For HTTPS with token
                        auth_url = repo_url.replace('https://', f'https://{auth_token}@')
                    else:
                        # For SSH with token (less common)
                        auth_url = repo_url
                    
                    clone_cmd = f"cd {self.workspace_path}/repositories && git clone {auth_url} {repo_name}"
                else:
                    clone_cmd = f"cd {self.workspace_path}/repositories && git clone {repo_url} {repo_name}"
                
                stdin, stdout, stderr = ssh.exec_command(clone_cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    self.repositories[repo_name] = repo_path
                    return f"Repository '{repo_name}' cloned successfully to {repo_path}"
                else:
                    error = stderr.read().decode('utf-8', errors='replace')
                    raise Exception(f"Failed to clone repository: {error}")
                    
        except Exception as e:
            raise Exception(f"Repository cloning failed: {str(e)}")
    
    async def list_repositories(self) -> str:
        """List all repositories in the workspace."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                repos_path = f"{self.workspace_path}/repositories"
                stdin, stdout, stderr = ssh.exec_command(f"ls -la {repos_path}")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    output = stdout.read().decode('utf-8', errors='replace')
                    return f"Repositories in {repos_path}:\n{output}"
                else:
                    return f"No repositories found in {repos_path}"
                    
        except Exception as e:
            raise Exception(f"Failed to list repositories: {str(e)}")
    
    async def switch_repository(self, repo_name: str) -> str:
        """Switch to a specific repository context."""
        try:
            repo_path = f"{self.workspace_path}/repositories/{repo_name}"
            
            with self.ssh_pool.get_connection() as ssh:
                # Check if repository exists
                stdin, stdout, stderr = ssh.exec_command(f"test -d {repo_path} && echo 'exists'")
                if stdout.read().decode().strip() != 'exists':
                    raise Exception(f"Repository '{repo_name}' not found")
                
                # Verify it's a git repository
                stdin, stdout, stderr = ssh.exec_command(f"cd {repo_path} && git status")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    self.current_repo = repo_name
                    self.repositories[repo_name] = repo_path
                    return f"Switched to repository '{repo_name}' at {repo_path}"
                else:
                    raise Exception(f"'{repo_name}' is not a valid git repository")
                    
        except Exception as e:
            raise Exception(f"Failed to switch repository: {str(e)}")
    
    async def get_current_repository(self) -> str:
        """Get the current repository context."""
        if self.current_repo:
            return f"Current repository: {self.current_repo} at {self.repositories[self.current_repo]}"
        else:
            return "No repository currently selected"
    
    async def git_operation(self, operation: str, **params) -> str:
        """Execute git operations in the current repository context."""
        if not self.current_repo:
            raise Exception("No repository selected. Use switch_repository first.")
        
        repo_path = self.repositories[self.current_repo]
        
        try:
            with self.ssh_pool.get_connection() as ssh:
                # Build git command
                git_cmd = f"cd {repo_path} && git {operation}"
                
                # Add parameters
                for key, value in params.items():
                    if value is not None:
                        git_cmd += f" {key} {value}"
                
                stdin, stdout, stderr = ssh.exec_command(git_cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                stdout_text = stdout.read().decode('utf-8', errors='replace')
                stderr_text = stderr.read().decode('utf-8', errors='replace')
                
                result = f"Git {operation} in {self.current_repo} (exit code: {exit_code})\n"
                if stdout_text:
                    result += f"STDOUT:\n{stdout_text}"
                if stderr_text:
                    result += f"STDERR:\n{stderr_text}"
                
                return result
                
        except Exception as e:
            raise Exception(f"Git operation failed: {str(e)}")


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
    """MCP Server for remote server operations via SSH/SFTP with repository management."""
    
    def __init__(self):
        super().__init__(
            name="remote",
            version="3.0.0",
            description="Secure remote server operations with SSH, SFTP, and repository management"
        )
        self.ssh_pool = SSHConnectionPool()
        self.repo_manager = RepositoryManager(self.ssh_pool)
    
    async def initialize(self) -> None:
        """Initialize the remote server and register tools."""
        
        # Initialize workspace
        await self.repo_manager.initialize_workspace()
        
        # Register repository management tools
        init_workspace_tool = MCPTool(
            name="init_workspace",
            description="Initialize the remote workspace for repository management",
            parameters={"type": "object", "properties": {}},
            execute_func=self._init_workspace,
            category="repository",
            timeout=30
        )
        self.register_tool(init_workspace_tool)
        
        clone_repo_tool = MCPTool(
            name="clone_repository",
            description="Clone a repository to the remote workspace. Call as: clone_repository(repo_url='https://github.com/user/repo.git', repo_name='my-repo', auth_token='optional_token')",
            parameters={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "Repository URL (HTTPS or SSH)"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Name for the repository in the workspace"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "Authentication token (optional)",
                        "default": None
                    }
                },
                "required": ["repo_url", "repo_name"]
            },
            execute_func=self._clone_repository,
            category="repository",
            timeout=120
        )
        self.register_tool(clone_repo_tool)
        
        list_repos_tool = MCPTool(
            name="list_repositories",
            description="List all repositories in the remote workspace",
            parameters={"type": "object", "properties": {}},
            execute_func=self._list_repositories,
            category="repository",
            timeout=15
        )
        self.register_tool(list_repos_tool)
        
        switch_repo_tool = MCPTool(
            name="switch_repository",
            description="Switch to a specific repository context. Call as: switch_repository(repo_name='my-repo')",
            parameters={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository to switch to"
                    }
                },
                "required": ["repo_name"]
            },
            execute_func=self._switch_repository,
            category="repository",
            timeout=15
        )
        self.register_tool(switch_repo_tool)
        
        current_repo_tool = MCPTool(
            name="get_current_repository",
            description="Get the current repository context",
            parameters={"type": "object", "properties": {}},
            execute_func=self._get_current_repository,
            category="repository",
            timeout=5
        )
        self.register_tool(current_repo_tool)
        
        # Register git operation tools
        git_status_tool = MCPTool(
            name="git_status",
            description="Get git status of the current repository",
            parameters={"type": "object", "properties": {}},
            execute_func=self._git_status,
            category="git",
            timeout=15
        )
        self.register_tool(git_status_tool)
        
        git_log_tool = MCPTool(
            name="git_log",
            description="Get git log of the current repository. Call as: git_log(n=10) for last 10 commits",
            parameters={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of commits to show",
                        "default": 10
                    }
                }
            },
            execute_func=self._git_log,
            category="git",
            timeout=15
        )
        self.register_tool(git_log_tool)
        
        git_diff_tool = MCPTool(
            name="git_diff",
            description="Get git diff of the current repository. Call as: git_diff() for working directory changes",
            parameters={
                "type": "object",
                "properties": {
                    "commit1": {
                        "type": "string",
                        "description": "First commit hash (optional)",
                        "default": None
                    },
                    "commit2": {
                        "type": "string",
                        "description": "Second commit hash (optional)",
                        "default": None
                    }
                }
            },
            execute_func=self._git_diff,
            category="git",
            timeout=15
        )
        self.register_tool(git_diff_tool)
        
        git_add_tool = MCPTool(
            name="git_add",
            description="Add files to git staging area. Call as: git_add(files='.') for all files or git_add(files='file1.py file2.py') for specific files",
            parameters={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "string",
                        "description": "Files to add (use '.' for all files)",
                        "default": "."
                    }
                },
                "required": ["files"]
            },
            execute_func=self._git_add,
            category="git",
            timeout=30
        )
        self.register_tool(git_add_tool)
        
        git_commit_tool = MCPTool(
            name="git_commit",
            description="Commit changes to git. Call as: git_commit(message='Add new feature')",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    }
                },
                "required": ["message"]
            },
            execute_func=self._git_commit,
            category="git",
            timeout=30
        )
        self.register_tool(git_commit_tool)
        
        git_push_tool = MCPTool(
            name="git_push",
            description="Push changes to remote repository. Call as: git_push(branch='main')",
            parameters={
                "type": "object",
                "properties": {
                    "branch": {
                        "type": "string",
                        "description": "Branch to push",
                        "default": "main"
                    }
                }
            },
            execute_func=self._git_push,
            category="git",
            timeout=60
        )
        self.register_tool(git_push_tool)
        
        git_pull_tool = MCPTool(
            name="git_pull",
            description="Pull changes from remote repository. Call as: git_pull(branch='main')",
            parameters={
                "type": "object",
                "properties": {
                    "branch": {
                        "type": "string",
                        "description": "Branch to pull",
                        "default": "main"
                    }
                }
            },
            execute_func=self._git_pull,
            category="git",
            timeout=60
        )
        self.register_tool(git_pull_tool)
        
        # Register Ollama/Local Model tools
        install_ollama_tool = MCPTool(
            name="install_ollama",
            description="Install Ollama on the remote server for local model support",
            parameters={"type": "object", "properties": {}},
            execute_func=self._install_ollama,
            category="local_models",
            timeout=300
        )
        self.register_tool(install_ollama_tool)
        
        pull_model_tool = MCPTool(
            name="pull_model",
            description="Pull a model to Ollama. Call as: pull_model(model_name='qwen2.5:7b')",
            parameters={
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Model name like 'qwen2.5:7b', 'llama3.1:8b', 'mistral:7b'"
                    }
                },
                "required": ["model_name"]
            },
            execute_func=self._pull_model,
            category="local_models",
            timeout=600
        )
        self.register_tool(pull_model_tool)
        
        list_models_tool = MCPTool(
            name="list_ollama_models",
            description="List all available Ollama models on the remote server",
            parameters={"type": "object", "properties": {}},
            execute_func=self._list_ollama_models,
            category="local_models",
            timeout=15
        )
        self.register_tool(list_models_tool)
        
        test_local_model_tool = MCPTool(
            name="test_local_model",
            description="Test a local model with a prompt. Call as: test_local_model(model_name='qwen2.5:7b', prompt='Hello, how are you?')",
            parameters={
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Model name to test"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Test prompt to send to the model"
                    }
                },
                "required": ["model_name", "prompt"]
            },
            execute_func=self._test_local_model,
            category="local_models",
            timeout=120
        )
        self.register_tool(test_local_model_tool)
        
        # Register existing command execution tool
        execute_command_tool = MCPTool(
            name="execute_command",
            description="Execute commands on remote server. Call as: execute_command(command='ls -la') or execute_command(command='python script.py', input_data='user input')",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command like 'ls', 'cat file.txt', 'python script.py'"
                    },
                    "input_data": {
                        "type": "string",
                        "description": "Input for interactive commands (optional)",
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
            description="Write files to remote server. Call as: write_file(filename='test.txt', content='Hello World')",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename like 'script.py', 'data.txt', 'config.json'"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content as a string"
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
            description="Read files from remote server. Call as: read_file(filename='script.py') or read_file(filename='data.txt')", 
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename to read like 'script.py', 'data.txt'"
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
            description="List directory contents on remote server. Call as: list_directory() for current directory or list_directory(path='/home/user')",
            parameters={
                "type": "object", 
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path like '/home/user' or 'subdir' (optional, defaults to current)",
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
    
    # Repository management methods
    async def _init_workspace(self) -> str:
        """Initialize the remote workspace."""
        return await self.repo_manager.initialize_workspace()
    
    async def _clone_repository(self, repo_url: str, repo_name: str, auth_token: str = None) -> str:
        """Clone a repository to the remote workspace."""
        return await self.repo_manager.clone_repository(repo_url, repo_name, auth_token)
    
    async def _list_repositories(self) -> str:
        """List all repositories in the workspace."""
        return await self.repo_manager.list_repositories()
    
    async def _switch_repository(self, repo_name: str) -> str:
        """Switch to a specific repository context."""
        return await self.repo_manager.switch_repository(repo_name)
    
    async def _get_current_repository(self) -> str:
        """Get the current repository context."""
        return await self.repo_manager.get_current_repository()
    
    # Git operation methods
    async def _git_status(self) -> str:
        """Get git status of the current repository."""
        return await self.repo_manager.git_operation("status")
    
    async def _git_log(self, n: int = 10) -> str:
        """Get git log of the current repository."""
        return await self.repo_manager.git_operation("log", n=str(n))
    
    async def _git_diff(self, commit1: str = None, commit2: str = None) -> str:
        """Get git diff of the current repository."""
        if commit1 and commit2:
            return await self.repo_manager.git_operation("diff", commit1=commit1, commit2=commit2)
        else:
            return await self.repo_manager.git_operation("diff")
    
    async def _git_add(self, files: str) -> str:
        """Add files to git staging area."""
        return await self.repo_manager.git_operation("add", files=files)
    
    async def _git_commit(self, message: str) -> str:
        """Commit changes to git."""
        return await self.repo_manager.git_operation("commit", m=f'"{message}"')
    
    async def _git_push(self, branch: str = "main") -> str:
        """Push changes to remote repository."""
        return await self.repo_manager.git_operation("push", origin=branch)
    
    async def _git_pull(self, branch: str = "main") -> str:
        """Pull changes from remote repository."""
        return await self.repo_manager.git_operation("pull", origin=branch)
    
    # Ollama/Local Model methods
    async def _install_ollama(self) -> str:
        """Install Ollama on the remote server."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                # Check if Ollama is already installed
                stdin, stdout, stderr = ssh.exec_command("which ollama")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    return "Ollama is already installed on the remote server."
                
                # Install Ollama
                install_cmd = """
                sudo apt-get update
                sudo apt-get install -y python3-pip
                pip3 install ollama
                """
                stdin, stdout, stderr = ssh.exec_command(install_cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    return "Ollama installed successfully."
                else:
                    error = stderr.read().decode('utf-8', errors='replace')
                    raise Exception(f"Failed to install Ollama: {error}")
        except Exception as e:
            raise Exception(f"Ollama installation failed: {str(e)}")
    
    async def _pull_model(self, model_name: str) -> str:
        """Pull a model to Ollama."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                # Create a temporary directory for the model
                model_dir = f"/home/ec2-user/ollama/models/{model_name}"
                ssh.exec_command(f"mkdir -p {model_dir}")
                
                # Pull the model
                pull_cmd = f"ollama pull {model_name} --model {model_name}"
                stdin, stdout, stderr = ssh.exec_command(pull_cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    return f"Model '{model_name}' pulled successfully to {model_dir}"
                else:
                    error = stderr.read().decode('utf-8', errors='replace')
                    raise Exception(f"Failed to pull model '{model_name}': {error}")
        except Exception as e:
            raise Exception(f"Model pulling failed: {str(e)}")
    
    async def _list_ollama_models(self) -> str:
        """List all available Ollama models on the remote server."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                stdin, stdout, stderr = ssh.exec_command("ollama models")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code == 0:
                    output = stdout.read().decode('utf-8', errors='replace')
                    return f"Available Ollama models:\n{output}"
                else:
                    error = stderr.read().decode('utf-8', errors='replace')
                    raise Exception(f"Failed to list Ollama models: {error}")
        except Exception as e:
            raise Exception(f"Failed to list Ollama models: {str(e)}")
    
    async def _test_local_model(self, model_name: str, prompt: str) -> str:
        """Test a local model with a prompt."""
        try:
            with self.ssh_pool.get_connection() as ssh:
                # Ensure Ollama is running and accessible
                stdin, stdout, stderr = ssh.exec_command("ollama models")
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code != 0:
                    raise Exception("Ollama is not running or not accessible. Please ensure it's installed and running.")
                
                # Use printf to handle newlines properly for interactive programs
                test_cmd = f"printf '{prompt}\\n' | ollama generate --model {model_name}"
                stdin, stdout, stderr = ssh.exec_command(test_cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                stdout_text = stdout.read().decode('utf-8', errors='replace')
                stderr_text = stderr.read().decode('utf-8', errors='replace')
                
                result = f"Model '{model_name}' test (exit code: {exit_code})\n"
                if stdout_text:
                    result += f"STDOUT:\n{stdout_text}"
                if stderr_text:
                    result += f"STDERR:\n{stderr_text}"
                
                return result
        except Exception as e:
            raise Exception(f"Model testing failed: {str(e)}")
    
    # Existing methods (unchanged)
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