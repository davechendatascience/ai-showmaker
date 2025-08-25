#!/usr/bin/env python3
"""
Enhanced MCP Integration for LlamaIndex Agent

This module provides improved integration between LlamaIndex and MCP servers,
with native protocol support, better tool registration, and enhanced communication.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime

try:
    from llama_index.core.tools import FunctionTool
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.core.settings import Settings
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.llms import ChatMessage, MessageRole
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

from .config import ConfigManager


@dataclass
class MCPToolMetadata:
    """Enhanced metadata for MCP tools."""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    category: str
    version: str
    timeout: int
    requires_auth: bool
    examples: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class MCPToolResult:
    """Enhanced MCP tool result with better metadata."""
    success: bool
    data: Any
    message: str
    execution_time: float
    tool_name: str
    server_name: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MCPToolWrapper:
    """Enhanced wrapper for MCP tools with better LlamaIndex integration."""
    
    def __init__(self, mcp_tool, server_name: str, server_instance):
        self.mcp_tool = mcp_tool
        self.server_name = server_name
        self.server_instance = server_instance
        self.metadata = self._create_metadata()
        
    def _create_metadata(self) -> MCPToolMetadata:
        """Create enhanced metadata for the MCP tool."""
        return MCPToolMetadata(
            name=self.mcp_tool.name,
            description=self.mcp_tool.description,
            parameters=self.mcp_tool.parameters,
            server_name=self.server_name,
            category=getattr(self.mcp_tool, 'category', 'general'),
            version=getattr(self.mcp_tool, 'version', '1.0.0'),
            timeout=getattr(self.mcp_tool, 'timeout', 30),
            requires_auth=getattr(self.mcp_tool, 'requires_auth', False),
            examples=getattr(self.mcp_tool, 'examples', [])
        )
    
    async def execute(self, **kwargs) -> MCPToolResult:
        """Execute the MCP tool with proper error handling and timing."""
        start_time = datetime.now()
        
        try:
            # Execute the tool through the MCP server
            result = await self.server_instance.execute_tool(self.mcp_tool.name, kwargs)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return MCPToolResult(
                success=result.result_type.value == 'success',
                data=result.data,
                message=result.message,
                execution_time=execution_time,
                tool_name=self.mcp_tool.name,
                server_name=self.server_name,
                timestamp=start_time,
                metadata=result.metadata
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return MCPToolResult(
                success=False,
                data=None,
                message=str(e),
                execution_time=execution_time,
                tool_name=self.mcp_tool.name,
                server_name=self.server_name,
                timestamp=start_time,
                metadata={'error_type': type(e).__name__}
            )


class EnhancedLlamaIndexAgent:
    """
    Enhanced LlamaIndex-based AI Agent with native MCP integration.
    
    This implementation provides better integration between LlamaIndex and MCP
    servers, with improved tool calling, error handling, and communication.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize the enhanced LlamaIndex agent."""
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.enhanced_llamaindex_agent")
        
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex packages not installed. Run: pip install llama-index llama-index-llms-openai")
        
        # Initialize LLM using OpenAILike for custom API compatibility
        self.llm = OpenAILike(
            model=config.get('inference_net_model', 'mistralai/mistral-nemo-12b-instruct/fp-8'),
            api_key=config.get('inference_net_key'),
            api_base=config.get('inference_net_base_url', 'https://api.inference.net/v1'),
            temperature=0,
            is_chat_model=True,
            is_function_calling_model=False,
            context_window=128000
        )
        
        # Set global settings
        Settings.llm = self.llm
        
        # Enhanced tool management
        self.mcp_servers = {}
        self.mcp_tools = {}  # name -> MCPToolWrapper
        self.llama_tools = []  # LlamaIndex FunctionTools
        self.tool_registry = {}  # name -> function mapping
        self.memory = ChatMemoryBuffer.from_defaults()
        
        # Execution statistics
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_tool_calls': 0,
            'successful_tool_calls': 0,
            'failed_tool_calls': 0,
            'avg_response_time': 0.0
        }
    
    def set_mcp_servers(self, servers: Dict[str, Any]):
        """Set the MCP servers and register tools with enhanced metadata."""
        self.mcp_servers = servers
        self._register_mcp_tools_enhanced()
    
    def _register_mcp_tools_enhanced(self):
        """Register MCP tools with enhanced metadata and better LlamaIndex integration."""
        self.mcp_tools.clear()
        self.llama_tools.clear()
        self.tool_registry.clear()
        
        for server_name, server in self.mcp_servers.items():
            for tool_name, mcp_tool in server.tools.items():
                # Create enhanced MCP tool wrapper
                mcp_wrapper = MCPToolWrapper(mcp_tool, server_name, server)
                self.mcp_tools[f"{server_name}_{tool_name}"] = mcp_wrapper
                
                # Create LlamaIndex FunctionTool with enhanced metadata
                llama_tool = self._create_llama_tool(mcp_wrapper)
                self.llama_tools.append(llama_tool)
                
                # Register in tool registry
                self.tool_registry[llama_tool.metadata.name] = mcp_wrapper.execute
                self.tool_registry[tool_name] = mcp_wrapper.execute  # Also register base name
                
                self.logger.info(f"Registered enhanced tool: {server_name}_{tool_name}")
        
        self.logger.info(f"Enhanced LlamaIndex agent initialized with {len(self.llama_tools)} tools")
    
    def _create_llama_tool(self, mcp_wrapper: MCPToolWrapper) -> FunctionTool:
        """Create a LlamaIndex FunctionTool with enhanced metadata from MCP tool."""
        
        def tool_function(**kwargs) -> str:
            """Execute MCP tool with enhanced error handling and result formatting."""
            try:
                # Clean and validate parameters
                cleaned_kwargs = self._clean_and_validate_parameters(mcp_wrapper.metadata, kwargs)
                
                # Execute the tool
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new event loop in thread for async execution
                    import concurrent.futures
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(mcp_wrapper.execute(**cleaned_kwargs))
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        result = future.result(timeout=mcp_wrapper.metadata.timeout)
                else:
                    result = loop.run_until_complete(mcp_wrapper.execute(**cleaned_kwargs))
                
                # Update statistics
                self.stats['total_tool_calls'] += 1
                if result.success:
                    self.stats['successful_tool_calls'] += 1
                else:
                    self.stats['failed_tool_calls'] += 1
                
                # Format result for LlamaIndex
                if result.success:
                    return self._format_tool_result(result)
                else:
                    return f"Tool execution failed: {result.message}"
                
            except Exception as e:
                self.stats['total_tool_calls'] += 1
                self.stats['failed_tool_calls'] += 1
                error_msg = f"Tool execution failed: {str(e)}"
                self.logger.error(f"Error in {mcp_wrapper.metadata.name}: {error_msg}")
                return error_msg
        
        # Set function metadata
        tool_function.__name__ = mcp_wrapper.metadata.name
        tool_function.__doc__ = mcp_wrapper.metadata.description
        
        # Create FunctionTool with enhanced metadata
        return FunctionTool.from_defaults(
            fn=tool_function,
            name=mcp_wrapper.metadata.name,
            description=mcp_wrapper.metadata.description
        )
    
    def _format_tool_result(self, result: MCPToolResult) -> str:
        """Format MCP tool result for LlamaIndex consumption."""
        if result.data is None:
            return result.message
        
        # Format based on data type
        if isinstance(result.data, (dict, list)):
            return json.dumps(result.data, indent=2, default=str)
        elif isinstance(result.data, str):
            return result.data
        else:
            return str(result.data)
    
    def _clean_and_validate_parameters(self, metadata: MCPToolMetadata, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate parameters with enhanced error handling."""
        cleaned_kwargs = {}
        required_params = metadata.parameters.get('required', [])
        
        for key, value in kwargs.items():
            # Skip None values and empty strings
            if value is None or value == "" or str(value).lower() == "none":
                continue
                
            # Handle string parameter wrapping issues
            if isinstance(value, str):
                # Check for double-wrapped parameters
                if '=' in value and value.count("'") >= 2:
                    import re
                    match = re.match(r'^[^=]+=[\'"]?([^\'"]*)[\'"]?$', value)
                    if match:
                        value = match.group(1)
                        self.logger.warning(f"Unwrapped parameter {key}: {kwargs[key]} -> {value}")
            
            cleaned_kwargs[key] = value
        
        # Validate required parameters
        missing_params = [param for param in required_params if param not in cleaned_kwargs]
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        return cleaned_kwargs
    
    def _build_enhanced_system_prompt(self) -> str:
        """Build enhanced system prompt with detailed tool information."""
        tool_descriptions = []
        
        for tool_name, mcp_wrapper in self.mcp_tools.items():
            metadata = mcp_wrapper.metadata
            desc = f"- {tool_name}: {metadata.description}"
            
            # Add parameter information
            if metadata.parameters.get('properties'):
                params = []
                for param_name, param_info in metadata.parameters['properties'].items():
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', '')
                    required = param_name in metadata.parameters.get('required', [])
                    req_marker = " (required)" if required else ""
                    params.append(f"    {param_name} ({param_type}){req_marker}: {param_desc}")
                
                if params:
                    desc += f"\n  Parameters:\n" + "\n".join(params)
            
            # Add examples if available
            if metadata.examples:
                desc += f"\n  Examples: {metadata.examples}"
            
            tool_descriptions.append(desc)
        
        tools_text = "\n".join(tool_descriptions)
        
        return f"""You are an AI assistant that MUST use the available tools to answer questions. DO NOT give instructions or educational responses - ALWAYS use tools to perform the requested actions.

Available tools:
{tools_text}

IMPORTANT RULES:
1. When asked to create todos, USE the create_todos tool
2. When asked to check system info, USE the execute_command tool
3. When asked to calculate something, USE the calculate tool
4. When asked about files/directories, USE the remote tools
5. ALWAYS use tools instead of giving instructions
6. Use the exact tool names as specified above

To use a tool, respond with a function call in this exact format:
FUNCTION_CALL: tool_name(parameter1="value1", parameter2="value2")

Examples:
FUNCTION_CALL: calculate(expression="5 + 3")
FUNCTION_CALL: create_todos(todos=["Deploy web app", "Test deployment", "Monitor performance"])
FUNCTION_CALL: execute_command(command="uname -a")
FUNCTION_CALL: list_directory(path="/home/user")

You can make multiple function calls by using multiple FUNCTION_CALL lines.
After executing tools, I will provide you with the results, and you should give a final comprehensive answer based on the actual tool results."""

    def _extract_function_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract function calls from LLM response with enhanced parsing."""
        function_calls = []
        
        # Enhanced pattern matching for function calls
        import re
        pattern = r'(?:\[)?FUNCTION_CALL:\s*(\w+)\((.*?)\)(?:\])?(?=\s*(?:FUNCTION_CALL:|$|\[FUNCTION_CALL:))'
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        
        for func_name, params_str in matches:
            try:
                params = {}
                if params_str.strip():
                    # Enhanced parameter parsing
                    try:
                        # Try to parse as Python AST first
                        import ast
                        func_call = f"dummy({params_str})"
                        parsed = ast.parse(func_call, mode='eval')
                        if isinstance(parsed.body, ast.Call):
                            for arg in parsed.body.keywords:
                                param_name = arg.arg
                                value = ast.literal_eval(arg.value)
                                params[param_name] = value
                    except (ValueError, SyntaxError):
                        # Fallback to regex parsing
                        self._parse_params_with_regex(params_str, params)
                
                if params or not params_str.strip():  # Allow tools with no parameters
                    function_calls.append({
                        'name': func_name,
                        'parameters': params
                    })
                    self.logger.info(f"Parsed function call: {func_name} with params: {params}")
                
            except Exception as e:
                self.logger.error(f"Failed to parse function call {func_name}: {e}")
                continue
        
        return function_calls

    def _parse_params_with_regex(self, params_str: str, params: Dict[str, Any]):
        """Enhanced regex-based parameter parsing."""
        import re
        # Handle arrays: param=["item1", "item2"] or param=['item1', 'item2']
        array_pattern = r'(\w+)=\[([^\]]+)\]'
        array_matches = re.findall(array_pattern, params_str)
        
        for param_name, array_content in array_matches:
            # Extract items from array content
            items = re.findall(r'["\']([^"\']+)["\']', array_content)
            params[param_name] = items
        
        # Handle simple string parameters: param="value"
        string_pattern = r'(\w+)=(["\'])([^"\']*)\2'
        string_matches = re.findall(string_pattern, params_str)
        
        for param_name, quote, param_value in string_matches:
            if param_name not in params:  # Don't override array params
                params[param_name] = param_value
    
    async def _execute_function_call(self, call: Dict[str, Any]) -> str:
        """Execute a function call with enhanced error handling."""
        func_name = call['name']
        params = call['parameters']
        
        # Find the function in our registry
        if func_name in self.tool_registry:
            func = self.tool_registry[func_name]
            try:
                result = func(**params)
                return str(result)
            except Exception as e:
                raise Exception(f"Function execution failed: {str(e)}")
        else:
            available_tools = list(self.tool_registry.keys())
            raise Exception(f"Function '{func_name}' not found. Available: {available_tools}")
    
    async def query(self, message: str) -> str:
        """Query the agent with enhanced MCP integration."""
        if not self.llama_tools:
            return "Error: No tools available. Please set MCP servers first."
        
        start_time = datetime.now()
        self.stats['total_queries'] += 1
        
        try:
            # Add user message to memory
            user_msg = ChatMessage(role=MessageRole.USER, content=message)
            self.memory.put(user_msg)
            
            # Build enhanced system prompt
            system_prompt = self._build_enhanced_system_prompt()
            messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]
            messages.extend(self.memory.get())
            
            # Get response with function calling instructions
            response = await self.llm.achat(messages)
            response_content = response.message.content or ""
            
            self.logger.info(f"LLM Response: {response_content}")
            
            # Extract and execute function calls
            function_calls = self._extract_function_calls(response_content)
            self.logger.info(f"Extracted {len(function_calls)} function calls from response")
            
            if function_calls:
                # Execute function calls
                tool_results = []
                for call in function_calls:
                    try:
                        result = await self._execute_function_call(call)
                        tool_results.append(f"Tool {call['name']}: {result}")
                        self.logger.info(f"Successfully executed {call['name']}")
                    except Exception as e:
                        tool_results.append(f"Tool {call['name']} failed: {str(e)}")
                        self.logger.error(f"Failed to execute {call['name']}: {str(e)}")
                
                # Get final response with tool results
                tool_context = "\n".join(tool_results)
                final_prompt = f"Based on the following tool results, provide a concise answer:\n\n{tool_context}"
                
                final_message = ChatMessage(role=MessageRole.USER, content=final_prompt)
                final_response = await self.llm.achat([final_message])
                
                result = final_response.message.content or "No response generated"
                
                # Add to memory
                assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=result)
                self.memory.put(assistant_msg)
                
                self.stats['successful_queries'] += 1
                return result
            else:
                # No function calls detected
                if "FUNCTION_CALL:" in response_content:
                    self.logger.warning(f"Response contains FUNCTION_CALL but parsing failed: {response_content}")
                
                # No function calls needed, return direct response
                assistant_msg = ChatMessage(role=MessageRole.ASSISTANT, content=response_content)
                self.memory.put(assistant_msg)
                
                self.stats['successful_queries'] += 1
                return response_content
            
        except Exception as e:
            self.stats['failed_queries'] += 1
            self.logger.error(f"Agent query failed: {str(e)}")
            return f"Error: {str(e)}"
        finally:
            # Update average response time
            response_time = (datetime.now() - start_time).total_seconds()
            total_queries = self.stats['successful_queries'] + self.stats['failed_queries']
            if total_queries > 0:
                self.stats['avg_response_time'] = (
                    (self.stats['avg_response_time'] * (total_queries - 1)) + response_time
                ) / total_queries
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get enhanced information about available tools."""
        tools_info = []
        for tool_name, mcp_wrapper in self.mcp_tools.items():
            metadata = mcp_wrapper.metadata
            tools_info.append({
                "name": tool_name,
                "description": metadata.description,
                "server": metadata.server_name,
                "category": metadata.category,
                "version": metadata.version,
                "parameters": metadata.parameters,
                "examples": metadata.examples
            })
        return tools_info
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics."""
        return {
            'agent_stats': self.stats.copy(),
            'tool_count': len(self.mcp_tools),
            'server_count': len(self.mcp_servers),
            'memory_size': len(self.memory.get()) if self.memory else 0
        }


class EnhancedMCPServerManager:
    """
    Enhanced MCP Server Manager for LlamaIndex integration.
    
    This provides better server management and tool registration with
    enhanced error handling and monitoring capabilities.
    """
    
    def __init__(self):
        """Initialize the enhanced server manager."""
        self.logger = logging.getLogger("ai_showmaker.enhanced_mcp_manager")
        self.servers = {}
        self.agent = None
        
    async def initialize_servers(self) -> None:
        """Initialize all MCP servers with enhanced error handling."""
        from mcp_servers.calculation.server import CalculationMCPServer
        from mcp_servers.remote.server import RemoteMCPServer
        from mcp_servers.development.server import DevelopmentMCPServer
        from mcp_servers.monitoring.server import MonitoringMCPServer
        from mcp_servers.websearch.server import WebSearchMCPServer
        
        # Initialize servers with enhanced error handling
        servers_to_init = [
            ("calculation", CalculationMCPServer()),
            ("remote", RemoteMCPServer()),
            ("development", DevelopmentMCPServer()),
            ("monitoring", MonitoringMCPServer()),
            ("websearch", WebSearchMCPServer())
        ]
        
        for name, server in servers_to_init:
            try:
                await server.initialize()
                self.servers[name] = server
                self.logger.info(f"Initialized {name} MCP server with {len(server.tools)} tools")
            except Exception as e:
                self.logger.error(f"Failed to initialize {name} server: {str(e)}")
                # Continue with other servers even if one fails
        
        self.logger.info(f"Initialized {len(self.servers)} MCP servers successfully")
    
    def create_agent(self, config: ConfigManager) -> EnhancedLlamaIndexAgent:
        """Create and configure an enhanced LlamaIndex agent."""
        agent = EnhancedLlamaIndexAgent(config)
        agent.set_mcp_servers(self.servers)
        self.agent = agent
        return agent
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers with enhanced error handling."""
        for name, server in self.servers.items():
            try:
                await server.shutdown()
                self.logger.info(f"Shutdown {name} server")
            except Exception as e:
                self.logger.error(f"Error shutting down {name} server: {str(e)}")
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics."""
        stats = {}
        for name, server in self.servers.items():
            try:
                stats[name] = server.get_server_info()
            except Exception as e:
                self.logger.error(f"Error getting stats for {name} server: {str(e)}")
                stats[name] = {'error': str(e)}
        return stats


# Enhanced compatibility wrapper for existing code
class EnhancedAIShowmakerAgent:
    """
    Enhanced compatibility wrapper to maintain existing API while using improved LlamaIndex internally.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize with enhanced LlamaIndex backend."""
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.enhanced_agent")
        self.manager = EnhancedMCPServerManager()
        self.agent = None
        self.start_time = datetime.now()
        
    async def initialize(self) -> None:
        """Initialize the agent and MCP servers."""
        await self.manager.initialize_servers()
        self.agent = self.manager.create_agent(self.config)
        self.logger.info("EnhancedAIShowmakerAgent initialized with enhanced LlamaIndex backend")
    
    async def query(self, message: str) -> str:
        """Query the agent."""
        if not self.agent:
            await self.initialize()
        return await self.agent.query(message)
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get available tools information."""
        if not self.agent:
            return []
        return self.agent.get_tools_info()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics."""
        if not self.agent:
            return {'error': 'Agent not initialized'}
        
        stats = self.agent.get_statistics()
        stats['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        return stats
    
    async def _get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return self.manager.get_server_stats()
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        if self.manager:
            await self.manager.shutdown()
