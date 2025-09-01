"""
Development MCP Server Implementation

Provides development workflow tools including Git operations,
file management, and package management capabilities.
"""

import os
import json
import subprocess
import tempfile
import platform
import glob
from typing import Dict, Any, List, Optional
from pathlib import Path

from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool
from core.exceptions import ValidationError


class DevelopmentMCPServer(AIShowmakerMCPServer):
    """MCP Server for development workflow operations with authentication."""
    
    def __init__(self, git_repo_path: str = None, auth_token: str = None):
        super().__init__(
            name="development",
            version="2.0.0", 
            description="Development workflow tools including Git, file operations, and package management (AUTHENTICATED)"
        )
        self.git_repo_path = git_repo_path
        self.auth_token = auth_token
        self.is_authenticated = False
        
        if git_repo_path and auth_token:
            self._validate_authentication()
    
    def _validate_authentication(self):
        """Validate authentication and repository access."""
        try:
            # Check if repository path exists and is a git repository
            if not os.path.exists(self.git_repo_path):
                raise ValueError(f"Repository path does not exist: {self.git_repo_path}")
            
            git_dir = os.path.join(self.git_repo_path, '.git')
            if not os.path.exists(git_dir):
                raise ValueError(f"Not a git repository: {self.git_repo_path}")
            
            # Here you could add additional authentication logic
            # For now, we'll just check if the token is provided
            if not self.auth_token:
                raise ValueError("Authentication token required")
            
            self.is_authenticated = True
            self.logger.info(f"✅ Authenticated for repository: {self.git_repo_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Authentication failed: {str(e)}")
            self.is_authenticated = False
            raise
    
    def _check_authentication(self, operation: str) -> str:
        """Check authentication for sensitive operations."""
        if not self.is_authenticated:
            return f"❌ Authentication required for {operation}. Please provide git_repo_path and auth_token."
        return None
    
    def _get_repository_path(self, user_path: str = ".") -> str:
        """Get the repository path, preferring authenticated path."""
        if self.is_authenticated and self.git_repo_path:
            return self.git_repo_path
        return user_path
    
    async def initialize(self) -> None:
        """Initialize the development server and register tools."""
        
        # Git Operations
        git_status_tool = MCPTool(
            name="git_status",
            description="Get git repository status showing modified files, untracked files, and branch info",
            parameters={
                "type": "object",
                "properties": {
                    "repository_path": {
                        "type": "string", 
                        "description": "Path to git repository (default: current directory)",
                        "default": "."
                    }
                }
            },
            execute_func=self._git_status,
            category="git",
            timeout=15
        )
        self.register_tool(git_status_tool)
        
        git_add_tool = MCPTool(
            name="git_add",
            description="Stage files for git commit",
            parameters={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "string",
                        "description": "Files to stage (space-separated, use '.' for all files)"
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository", 
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
            description="Create git commit with message",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    }
                },
                "required": ["message"]
            },
            execute_func=self._git_commit,
            category="git", 
            timeout=30
        )
        self.register_tool(git_commit_tool)
        
        git_log_tool = MCPTool(
            name="git_log",
            description="Show git commit history",
            parameters={
                "type": "object",
                "properties": {
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to show",
                        "default": 10
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
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
            description="Show git differences for files",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string", 
                        "description": "Specific file to diff (optional - shows all changes if not provided)",
                        "default": ""
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes instead of working directory changes",
                        "default": False
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    }
                }
            },
            execute_func=self._git_diff,
            category="git",
            timeout=30
        )
        self.register_tool(git_diff_tool)
        
        # File Operations
        find_files_tool = MCPTool(
            name="find_files",
            description="Search for files by name pattern or content",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File name pattern to search for (supports wildcards)"
                    },
                    "directory": {
                        "type": "string", 
                        "description": "Directory to search in",
                        "default": "."
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File extension filter (e.g., 'py', 'js')",
                        "default": ""
                    }
                },
                "required": ["pattern"]
            },
            execute_func=self._find_files,
            category="files",
            timeout=30
        )
        self.register_tool(find_files_tool)
        
        search_in_files_tool = MCPTool(
            name="search_in_files",
            description="Search for text content within files",
            parameters={
                "type": "object",
                "properties": {
                    "search_text": {
                        "type": "string",
                        "description": "Text to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in",
                        "default": "."
                    },
                    "file_extension": {
                        "type": "string", 
                        "description": "File extension to limit search (e.g., 'py', 'js')",
                        "default": ""
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search",
                        "default": False
                    }
                },
                "required": ["search_text"]
            },
            execute_func=self._search_in_files,
            category="files", 
            timeout=30
        )
        self.register_tool(search_in_files_tool)
        
        # Package Management
        install_package_tool = MCPTool(
            name="install_package",
            description="Install Python packages via pip",
            parameters={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Name of package to install"
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version to install (optional)",
                        "default": ""
                    }
                },
                "required": ["package_name"]
            },
            execute_func=self._install_package,
            category="packages",
            timeout=120
        )
        self.register_tool(install_package_tool)
        
        self.logger.info(f"Development MCP Server initialized with {len(self.tools)} tools")
    
    async def _git_status(self, repository_path: str = ".") -> str:
        """Get git repository status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return f"Git error: {result.stderr}"
            
            # Also get branch info
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repository_path,
                capture_output=True, 
                text=True
            )
            
            status_output = result.stdout.strip()
            branch_name = branch_result.stdout.strip()
            
            if not status_output:
                return f"Repository is clean (branch: {branch_name})"
            
            return f"Branch: {branch_name}\n\nChanges:\n{status_output}"
            
        except subprocess.TimeoutExpired:
            return "Git status command timed out"
        except Exception as e:
            return f"Git status failed: {str(e)}"
    
    async def _git_add(self, files: str, repository_path: str = ".") -> str:
        """Stage files for git commit."""
        # Check authentication for write operations
        auth_error = self._check_authentication("git add")
        if auth_error:
            return auth_error
        
        repo_path = self._get_repository_path(repository_path)
        
        try:
            result = subprocess.run(
                ["git", "add"] + files.split(),
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"Successfully staged: {files}"
            else:
                return f"Git add failed: {result.stderr}"
                
        except Exception as e:
            return f"Git add failed: {str(e)}"
    
    async def _git_commit(self, message: str, repository_path: str = ".") -> str:
        """Create git commit."""
        # Check authentication for write operations
        auth_error = self._check_authentication("git commit")
        if auth_error:
            return auth_error
        
        repo_path = self._get_repository_path(repository_path)
        
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                return f"Commit successful: {message}\n{result.stdout}"
            else:
                return f"Git commit failed: {result.stderr}"
                
        except Exception as e:
            return f"Git commit failed: {str(e)}"
    
    async def _git_log(self, max_commits: int = 10, repository_path: str = ".") -> str:
        """Show git commit history."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--oneline"],
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Git log failed: {result.stderr}"
                
        except Exception as e:
            return f"Git log failed: {str(e)}"
    
    async def _git_diff(self, file_path: str = "", staged: bool = False, repository_path: str = ".") -> str:
        """Show git differences."""
        try:
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            if file_path:
                cmd.append(file_path)
                
            result = subprocess.run(
                cmd,
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                diff_output = result.stdout.strip()
                return diff_output if diff_output else "No differences found"
            else:
                return f"Git diff failed: {result.stderr}"
                
        except Exception as e:
            return f"Git diff failed: {str(e)}"
    
    async def _find_files(self, pattern: str, directory: str = ".", file_type: str = "") -> str:
        """Find files by pattern using cross-platform approach."""
        try:
            if platform.system() == "Windows":
                # Use Python's glob for cross-platform compatibility
                search_pattern = os.path.join(directory, "**", pattern)
                if file_type:
                    search_pattern = os.path.join(directory, "**", f"*.{file_type}")
                
                files = glob.glob(search_pattern, recursive=True)
                
                if files:
                    # Convert to relative paths and sort
                    relative_files = [os.path.relpath(f, directory) for f in files]
                    return "\n".join(sorted(relative_files))
                else:
                    return f"No files found matching pattern: {pattern}"
            else:
                # Use Unix find command on non-Windows systems
                cmd = ["find", directory, "-name", pattern]
                if file_type:
                    cmd.extend(["-name", f"*.{file_type}"])
                    
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.returncode == 0:
                    files = result.stdout.strip()
                    return files if files else f"No files found matching pattern: {pattern}"
                else:
                    return f"Find command failed: {result.stderr}"
                
        except Exception as e:
            return f"File search failed: {str(e)}"
    
    async def _search_in_files(self, search_text: str, directory: str = ".", 
                             file_extension: str = "", case_sensitive: bool = False) -> str:
        """Search for text within files using cross-platform approach."""
        try:
            if platform.system() == "Windows":
                # Use Python-based text search on Windows
                results = []
                search_dir = Path(directory)
                
                # Build file pattern
                if file_extension:
                    pattern = f"**/*.{file_extension}"
                else:
                    pattern = "**/*"
                
                # Search through files
                for file_path in search_dir.glob(pattern):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for line_num, line in enumerate(f, 1):
                                    search_line = line if case_sensitive else line.lower()
                                    search_target = search_text if case_sensitive else search_text.lower()
                                    
                                    if search_target in search_line:
                                        relative_path = os.path.relpath(file_path, directory)
                                        results.append(f"{relative_path}:{line_num}:{line.strip()}")
                        except Exception:
                            continue  # Skip files that can't be read
                
                if results:
                    return "\n".join(results[:50])  # Limit to first 50 matches
                else:
                    return f"Text '{search_text}' not found in any files"
            else:
                # Use grep on Unix-like systems
                cmd = ["grep", "-r"]
                if not case_sensitive:
                    cmd.append("-i")
                cmd.extend(["-n", search_text, directory])
                
                if file_extension:
                    cmd.extend(["--include", f"*.{file_extension}"])
                    
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                elif result.returncode == 1:
                    return f"Text '{search_text}' not found in any files"
                else:
                    return f"Search failed: {result.stderr}"
                
        except Exception as e:
            return f"Text search failed: {str(e)}"
    
    async def _install_package(self, package_name: str, version: str = "") -> str:
        """Install Python package via pip."""
        try:
            package_spec = f"{package_name}=={version}" if version else package_name
            
            result = subprocess.run(
                ["pip", "install", package_spec],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return f"Successfully installed: {package_spec}"
            else:
                return f"Package installation failed: {result.stderr}"
                
        except Exception as e:
            return f"Package installation failed: {str(e)}"
    
    async def shutdown(self) -> None:
        """Shutdown the development server."""
        self.logger.info("Development MCP Server shutting down")


class ReadOnlyDevelopmentMCPServer(AIShowmakerMCPServer):
    """Read-only MCP Server for development operations - SAFE VERSION.
    
    This version only allows read operations and safe queries, preventing
    any modifications to the repository or file system.
    """
    
    def __init__(self):
        super().__init__(
            name="development_readonly",
            version="2.0.0",
            description="Read-only development operations server (SAFE MODE)"
        )
    
    async def initialize(self) -> None:
        """Initialize the read-only development server and register SAFE tools only."""
        from ..base.server import MCPTool
        
        # SAFE: Read-only git operations
        git_status_tool = MCPTool(
            name="git_status",
            description="Get git repository status showing modified files, untracked files, and branch info (READ-ONLY)",
            parameters={
                "type": "object",
                "properties": {
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    }
                }
            },
            execute_func=self._git_status,
            category="git_readonly",
            timeout=15
        )
        self.register_tool(git_status_tool)
        
        git_log_tool = MCPTool(
            name="git_log",
            description="Show git commit history (READ-ONLY)",
            parameters={
                "type": "object",
                "properties": {
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to show",
                        "default": 10
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    }
                }
            },
            execute_func=self._git_log,
            category="git_readonly",
            timeout=15
        )
        self.register_tool(git_log_tool)
        
        git_diff_tool = MCPTool(
            name="git_diff",
            description="Show git differences for files (READ-ONLY)",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string", 
                        "description": "Specific file to diff (optional - shows all changes if not provided)",
                        "default": ""
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes instead of working directory changes",
                        "default": False
                    },
                    "repository_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    }
                }
            },
            execute_func=self._git_diff,
            category="git_readonly",
            timeout=30
        )
        self.register_tool(git_diff_tool)
        
        # SAFE: File search operations (read-only)
        find_files_tool = MCPTool(
            name="find_files",
            description="Search for files by name pattern or content (READ-ONLY)",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File name pattern to search for (supports wildcards)"
                    },
                    "directory": {
                        "type": "string", 
                        "description": "Directory to search in",
                        "default": "."
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File extension filter (e.g., 'py', 'js')",
                        "default": ""
                    }
                },
                "required": ["pattern"]
            },
            execute_func=self._find_files,
            category="files_readonly",
            timeout=30
        )
        self.register_tool(find_files_tool)
        
        search_in_files_tool = MCPTool(
            name="search_in_files",
            description="Search for text content within files (READ-ONLY)",
            parameters={
                "type": "object",
                "properties": {
                    "search_text": {
                        "type": "string",
                        "description": "Text to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in",
                        "default": "."
                    },
                    "file_extension": {
                        "type": "string",
                        "description": "File extension filter (e.g., 'py', 'js')",
                        "default": ""
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search",
                        "default": False
                    }
                },
                "required": ["search_text"]
            },
            execute_func=self._search_in_files,
            category="files_readonly",
            timeout=30
        )
        self.register_tool(search_in_files_tool)
        
        self.logger.info(f"Read-only Development MCP Server initialized with {len(self.tools)} SAFE tools")
        self.logger.warning("⚠️  This is READ-ONLY mode - no git commits or file modifications allowed!")
    
    async def shutdown(self) -> None:
        """Shutdown the read-only development server."""
        self.logger.info("Read-only Development MCP Server shutting down")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'tools_count': len(self.tools),
            'mode': 'readonly_safe'
        }
    
    # Inherit safe methods from parent class
    async def _git_status(self, repository_path: str = ".") -> str:
        """Get git repository status (READ-ONLY)."""
        return await super()._git_status(repository_path)
    
    async def _git_log(self, max_commits: int = 10, repository_path: str = ".") -> str:
        """Show git commit history (READ-ONLY)."""
        return await super()._git_log(max_commits, repository_path)
    
    async def _git_diff(self, file_path: str = "", staged: bool = False, repository_path: str = ".") -> str:
        """Show git differences for files (READ-ONLY)."""
        return await super()._git_diff(file_path, staged, repository_path)
    
    async def _find_files(self, pattern: str, directory: str = ".", file_type: str = "") -> str:
        """Search for files by name pattern or content (READ-ONLY)."""
        return await super()._find_files(pattern, directory, file_type)
    
    async def _search_in_files(self, search_text: str, directory: str = ".", file_extension: str = "", case_sensitive: bool = False) -> str:
        """Search for text content within files (READ-ONLY)."""
        return await super()._search_in_files(search_text, directory, file_extension, case_sensitive)