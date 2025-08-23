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
    """MCP Server for development workflow operations."""
    
    def __init__(self):
        super().__init__(
            name="development",
            version="2.0.0", 
            description="Development workflow tools including Git, file operations, and package management"
        )
    
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
        try:
            result = subprocess.run(
                ["git", "add"] + files.split(),
                cwd=repository_path,
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
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repository_path,
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