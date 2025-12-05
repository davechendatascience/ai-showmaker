"""
Base MCP Server Implementation for AI-Showmaker

This module provides the base classes that all AI-Showmaker MCP servers inherit from.
It implements the Model Context Protocol standard with AI-Showmaker specific enhancements.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from core.exceptions import ToolError, ValidationError, ConnectionError, SecurityError, AIShowmakerError


class MCPToolResultType(Enum):
    """Types of tool execution results."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class MCPErrorCode(Enum):
    """Standardized error codes for tool failures."""
    TOOL_NOT_FOUND = "tool_not_found"
    VALIDATION_ERROR = "validation_error"
    SECURITY_ERROR = "security_error"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class MCPToolResult:
    """Result of an MCP tool execution."""
    result_type: MCPToolResultType
    data: Any
    message: str = ""
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class MCPTool:
    """Represents an MCP tool with its metadata and execution function."""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute_func: callable
    category: str = "general"
    version: str = "1.0.0"
    timeout: int = 30
    requires_auth: bool = False
    # Error handling / retry policy (optional)
    max_retries: int = 0
    retry_backoff: float = 0.5  # seconds for first retry
    retry_backoff_factor: float = 2.0  # exponential backoff factor
    retriable_error_codes: Optional[List[str]] = None  # e.g., ["connection_error"]


class AIShowmakerMCPServer(ABC):
    """
    Base class for all AI-Showmaker MCP servers.
    
    Provides standardized tool registration, execution, and monitoring
    capabilities following the Model Context Protocol specification.
    """
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.tools: Dict[str, MCPTool] = {}
        self.logger = self._setup_logging()
        self.execution_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'avg_execution_time': 0.0
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the MCP server."""
        logger = logging.getLogger(f"mcp.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the MCP server."""
        if tool.name in self.tools:
            self.logger.warning(f"Tool '{tool.name}' already registered. Overwriting.")
        
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
        
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a registered tool by name."""
        return self.tools.get(name)
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with their metadata."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "category": tool.category,
                "version": tool.version,
                "timeout": tool.timeout,
                "requires_auth": tool.requires_auth
            }
            for tool in self.tools.values()
        ]
        
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            MCPToolResult with execution results
        """
        start_time = time.time()
        self.execution_stats['total_calls'] += 1
        
        try:
            # Get the tool
            tool = self.get_tool(tool_name)
            if not tool:
                raise ToolError(tool_name, f"Tool '{tool_name}' not found")

            # Validate arguments
            self._validate_arguments(tool, arguments)

            # Log execution
            self.logger.info(f"Executing tool: {tool_name} with args: {arguments}")

            # Execute with timeout + retry policy
            attempts = 0
            max_attempts = max(1, int(getattr(tool, 'max_retries', 0)) + 1)
            backoff = float(getattr(tool, 'retry_backoff', 0.5))
            factor = float(getattr(tool, 'retry_backoff_factor', 2.0))
            last_error: Optional[Exception] = None
            while attempts < max_attempts:
                attempts += 1
                try:
                    result = await asyncio.wait_for(
                        self._execute_with_error_handling(tool, arguments),
                        timeout=tool.timeout
                    )

                    execution_time = time.time() - start_time

                    # Update stats
                    self.execution_stats['successful_calls'] += 1
                    self._update_avg_execution_time(execution_time)

                    return MCPToolResult(
                        result_type=MCPToolResultType.SUCCESS,
                        data=result,
                        message=f"Tool '{tool_name}' executed successfully",
                        execution_time=execution_time,
                        metadata={
                            'tool_name': tool_name,
                            'server_name': self.name,
                            'attempts': attempts,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                except asyncio.TimeoutError as e:
                    last_error = e
                    error_code, retriable = MCPErrorCode.TIMEOUT.value, True
                except Exception as e:
                    last_error = e
                    error_code, retriable = self._classify_exception(e)

                # If we got here, an error occurred
                if attempts < max_attempts and self._should_retry(tool, error_code, retriable):
                    self.logger.warning(
                        f"Tool '{tool_name}' failed on attempt {attempts}/{max_attempts} with {error_code}; retrying in {backoff:.2f}s"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= factor
                    continue
                else:
                    # Break to produce error result
                    break

            # If we exit loop without return, report error
            raise last_error if last_error else ToolError(tool_name, "Unknown error")

        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_stats['failed_calls'] += 1
            
            error_message = str(e)
            error_code, retriable = self._classify_exception(e)
            self.logger.error(f"Tool execution failed: {tool_name} - {error_code} - {error_message}")
            
            return MCPToolResult(
                result_type=MCPToolResultType.ERROR,
                data=None,
                message=error_message,
                execution_time=execution_time,
                metadata={
                    'tool_name': tool_name,
                    'server_name': self.name,
                    'error_type': type(e).__name__,
                    'error_code': error_code,
                    'retriable': retriable,
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    async def _execute_with_error_handling(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with comprehensive error handling."""
        try:
            # Check if the function is async
            if asyncio.iscoroutinefunction(tool.execute_func):
                return await tool.execute_func(**arguments)
            else:
                # Run sync function in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: tool.execute_func(**arguments))

        except (ValidationError, SecurityError, ConnectionError, ToolError) as e:
            # Preserve known error types for classification upstream
            raise e
        except asyncio.CancelledError:
            raise ToolError(tool.name, "Tool execution cancelled")
        except Exception as e:
            # Wrap unknown exceptions
            raise ToolError(tool.name, f"Tool execution failed: {str(e)}")
    
    def _validate_arguments(self, tool: MCPTool, arguments: Dict[str, Any]) -> None:
        """Validate arguments against tool parameters schema."""
        # Basic validation - can be enhanced with JSON schema validation
        required_params = tool.parameters.get('required', [])
        
        for param in required_params:
            if param not in arguments:
                raise ValidationError(f"Required parameter '{param}' missing for tool '{tool.name}'")

    def _classify_exception(self, e: Exception) -> (str, bool):
        """Map exceptions to standardized error codes and whether they are retriable."""
        # Don't rely only on type(e).__name__ strings; use known classes
        if isinstance(e, ValidationError):
            return MCPErrorCode.VALIDATION_ERROR.value, False
        if isinstance(e, SecurityError):
            return MCPErrorCode.SECURITY_ERROR.value, False
        if isinstance(e, ConnectionError):
            return MCPErrorCode.CONNECTION_ERROR.value, True
        if isinstance(e, asyncio.TimeoutError):
            return MCPErrorCode.TIMEOUT.value, True
        if isinstance(e, ToolError):
            # Generic tool error; assume retriable unless message indicates not found
            msg = str(e).lower()
            if "not found" in msg:
                return MCPErrorCode.TOOL_NOT_FOUND.value, False
            return MCPErrorCode.UNKNOWN_ERROR.value, True
        return MCPErrorCode.UNKNOWN_ERROR.value, True

    def _should_retry(self, tool: MCPTool, error_code: str, retriable_by_default: bool) -> bool:
        """Decide whether to retry based on tool policy and error code."""
        allowed = getattr(tool, 'retriable_error_codes', None)
        if isinstance(allowed, list) and len(allowed) > 0:
            return error_code in allowed
        return retriable_by_default and getattr(tool, 'max_retries', 0) > 0
                
    def _update_avg_execution_time(self, execution_time: float) -> None:
        """Update average execution time statistics."""
        total_successful = self.execution_stats['successful_calls']
        current_avg = self.execution_stats['avg_execution_time']
        
        new_avg = ((current_avg * (total_successful - 1)) + execution_time) / total_successful
        self.execution_stats['avg_execution_time'] = new_avg
        
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and statistics."""
        return {
            'name': self.name,
            'version': self.version, 
            'description': self.description,
            'tool_count': len(self.tools),
            'statistics': self.execution_stats.copy(),
            'tools': [tool.name for tool in self.tools.values()]
        }
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the MCP server and register tools."""
        pass
        
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of the MCP server."""
        pass
