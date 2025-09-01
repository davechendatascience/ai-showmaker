#!/usr/bin/env python3
"""
Reliable MCP Integration for LlamaIndex Agent

This module provides a highly reliable integration between LlamaIndex and MCP servers,
with robust parameter validation, retry logic, and comprehensive error handling.
"""

import logging
import asyncio
import json
import re
import ast
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from llama_index.core.tools import FunctionTool
    from .custom_llm import InferenceNetLLM
    from llama_index.core.settings import Settings
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.llms import ChatMessage, MessageRole
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

from .config import ConfigManager
from .output_validator import OutputValidator, ValidationResult


class ParameterType(Enum):
    """Parameter types for validation."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ReliableMCPToolMetadata:
    """Enhanced metadata for MCP tools with strict validation."""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    category: str
    version: str
    timeout: int
    requires_auth: bool
    examples: List[Dict[str, Any]] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []
    
    def get_parameter_info(self, param_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed parameter information."""
        properties = self.parameters.get('properties', {})
        return properties.get(param_name)
    
    def get_required_parameters(self) -> List[str]:
        """Get list of required parameters."""
        return self.parameters.get('required', [])
    
    def validate_parameter_type(self, param_name: str, value: Any) -> Tuple[bool, Any, str]:
        """Validate and convert parameter to correct type."""
        param_info = self.get_parameter_info(param_name)
        if not param_info:
            return True, value, ""  # Unknown parameter, allow it
        
        param_type = param_info.get('type', 'string')
        try:
            if param_type == ParameterType.STRING.value:
                return True, str(value), ""
            elif param_type == ParameterType.INTEGER.value:
                return True, int(value), ""
            elif param_type == ParameterType.NUMBER.value:
                return True, float(value), ""
            elif param_type == ParameterType.BOOLEAN.value:
                if isinstance(value, str):
                    bool_val = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    bool_val = bool(value)
                return True, bool_val, ""
            elif param_type == ParameterType.ARRAY.value:
                if isinstance(value, str):
                    # Try to parse as JSON array
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return True, parsed, ""
                    except json.JSONDecodeError:
                        pass
                    # Fallback: split by comma
                    return True, [item.strip() for item in value.split(',') if item.strip()], ""
                elif isinstance(value, list):
                    return True, value, ""
                else:
                    return False, None, f"Expected array, got {type(value).__name__}"
            else:
                return True, value, ""
        except (ValueError, TypeError) as e:
            return False, None, f"Type conversion failed: {str(e)}"


@dataclass
class ReliableMCPToolResult:
    """Enhanced MCP tool result with reliability metrics."""
    success: bool
    data: Any
    message: str
    execution_time: float
    tool_name: str
    server_name: str
    timestamp: datetime
    retry_count: int = 0
    validation_errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.metadata is None:
            self.metadata = {}


class ReliableMCPToolWrapper:
    """Reliable wrapper for MCP tools with comprehensive validation and retry logic."""
    
    def __init__(self, mcp_tool, server_name: str, server_instance):
        self.mcp_tool = mcp_tool
        self.server_name = server_name
        self.server_instance = server_instance
        self.metadata = self._create_metadata()
        self.logger = logging.getLogger(f"ai_showmaker.reliable_tool.{server_name}.{mcp_tool.name}")
        
    def _create_metadata(self) -> ReliableMCPToolMetadata:
        """Create enhanced metadata for the MCP tool."""
        return ReliableMCPToolMetadata(
            name=self.mcp_tool.name,
            description=self.mcp_tool.description,
            parameters=self.mcp_tool.parameters,
            server_name=self.server_name,
            category=getattr(self.mcp_tool, 'category', 'general'),
            version=getattr(self.mcp_tool, 'version', '1.0.0'),
            timeout=getattr(self.mcp_tool, 'timeout', 30),
            requires_auth=getattr(self.mcp_tool, 'requires_auth', False),
            examples=getattr(self.mcp_tool, 'examples', []),
            max_retries=getattr(self.mcp_tool, 'max_retries', 3),
            retry_delay=getattr(self.mcp_tool, 'retry_delay', 1.0)
        )
    
    def validate_parameters(self, kwargs: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Comprehensive parameter validation and type conversion."""
        validation_errors = []
        validated_params = {}
        
        # Check required parameters
        required_params = self.metadata.get_required_parameters()
        for param in required_params:
            if param not in kwargs:
                validation_errors.append(f"Missing required parameter: {param}")
        
        # Validate and convert all provided parameters
        for key, value in kwargs.items():
            if value is None or value == "" or str(value).lower() == "none":
                continue
            
            # Clean string parameters
            if isinstance(value, str):
                value = self._clean_string_parameter(value)
            
            # Validate and convert type
            is_valid, converted_value, error_msg = self.metadata.validate_parameter_type(key, value)
            if is_valid:
                validated_params[key] = converted_value
            else:
                validation_errors.append(f"Parameter '{key}': {error_msg}")
        
        return len(validation_errors) == 0, validated_params, validation_errors
    
    def _clean_string_parameter(self, value: str) -> str:
        """Clean string parameters from common parsing issues."""
        # Remove extra quotes
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        
        # Handle escaped quotes
        value = value.replace('\\"', '"').replace("\\'", "'")
        
        return value
    
    async def execute_with_retry(self, **kwargs) -> ReliableMCPToolResult:
        """Execute the MCP tool with retry logic and comprehensive error handling."""
        start_time = datetime.now()
        retry_count = 0
        last_error = None
        
        # Validate parameters first
        is_valid, validated_params, validation_errors = self.validate_parameters(kwargs)
        
        if not is_valid:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ReliableMCPToolResult(
                success=False,
                data=None,
                message=f"Parameter validation failed: {'; '.join(validation_errors)}",
                execution_time=execution_time,
                tool_name=self.mcp_tool.name,
                server_name=self.server_name,
                timestamp=start_time,
                retry_count=retry_count,
                validation_errors=validation_errors
            )
        
        # Retry loop
        while retry_count <= self.metadata.max_retries:
            try:
                self.logger.info(f"Executing {self.mcp_tool.name} (attempt {retry_count + 1}) with params: {validated_params}")
                
                # Execute the tool through the MCP server
                result = await self.server_instance.execute_tool(self.mcp_tool.name, validated_params)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ReliableMCPToolResult(
                    success=result.result_type.value == 'success',
                    data=result.data,
                    message=result.message,
                    execution_time=execution_time,
                    tool_name=self.mcp_tool.name,
                    server_name=self.server_name,
                    timestamp=start_time,
                    retry_count=retry_count,
                    metadata=result.metadata
                )
                
            except Exception as e:
                last_error = e
                retry_count += 1
                self.logger.warning(f"Attempt {retry_count} failed for {self.mcp_tool.name}: {str(e)}")
                
                if retry_count <= self.metadata.max_retries:
                    await asyncio.sleep(self.metadata.retry_delay * retry_count)  # Exponential backoff
        
        # All retries failed
        execution_time = (datetime.now() - start_time).total_seconds()
        return ReliableMCPToolResult(
            success=False,
            data=None,
            message=f"Tool execution failed after {retry_count} attempts: {str(last_error)}",
            execution_time=execution_time,
            tool_name=self.mcp_tool.name,
            server_name=self.server_name,
            timestamp=start_time,
            retry_count=retry_count,
            metadata={'error_type': type(last_error).__name__}
        )


class ReliableLlamaIndexAgent:
    """
    Highly reliable LlamaIndex-based AI Agent with robust MCP integration.
    
    This implementation provides bulletproof integration between LlamaIndex and MCP
    servers, with comprehensive parameter validation, retry logic, and error recovery.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize the reliable LlamaIndex agent."""
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.reliable_llamaindex_agent")
        
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex packages not installed. Run: pip install llama-index llama-index-llms-openai")
        
        # Initialize LLM using custom InferenceNetLLM for inference.net compatibility
        self.llm = InferenceNetLLM(
            model=config.get('inference_net_model', 'mistralai/mistral-nemo-12b-instruct/fp-8'),
            api_key=config.get('inference_net_key'),
            base_url=config.get('inference_net_base_url', 'https://api.inference.net/v1'),
            temperature=0  # Low temperature for more consistent tool usage
        )
        
        # Set global settings
        Settings.llm = self.llm
        
        # Enhanced tool management
        self.mcp_servers = {}
        self.mcp_tools = {}  # name -> ReliableMCPToolWrapper
        self.llama_tools = []  # LlamaIndex FunctionTools
        self.tool_registry = {}  # name -> function mapping
        self.memory = ChatMemoryBuffer.from_defaults()
        
        # Execution statistics with reliability metrics
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_tool_calls': 0,
            'successful_tool_calls': 0,
            'failed_tool_calls': 0,
            'validation_errors': 0,
            'retry_attempts': 0,
            'avg_response_time': 0.0,
            'parameter_errors': 0,
            'output_validation_errors': 0,
            'output_validation_warnings': 0
        }
        
        # Initialize output validator for intelligent error detection
        self.output_validator = OutputValidator()
    
    def set_mcp_servers(self, servers: Dict[str, Any]):
        """Set the MCP servers and register tools with reliable metadata."""
        self.mcp_servers = servers
        self._register_mcp_tools_reliable()
    
    def _register_mcp_tools_reliable(self):
        """Register MCP tools with reliable metadata and validation."""
        self.mcp_tools.clear()
        self.llama_tools.clear()
        self.tool_registry.clear()
        
        for server_name, server in self.mcp_servers.items():
            for tool_name, mcp_tool in server.tools.items():
                # Create reliable MCP tool wrapper
                mcp_wrapper = ReliableMCPToolWrapper(mcp_tool, server_name, server)
                self.mcp_tools[f"{server_name}_{tool_name}"] = mcp_wrapper
                
                # Create LlamaIndex FunctionTool with reliable metadata
                llama_tool = self._create_reliable_llama_tool(mcp_wrapper)
                self.llama_tools.append(llama_tool)
                
                # Register in tool registry with multiple naming schemes
                self.tool_registry[llama_tool.metadata.name] = mcp_wrapper.execute_with_retry
                self.tool_registry[tool_name] = mcp_wrapper.execute_with_retry  # Base name
                self.tool_registry[f"{server_name}_{tool_name}"] = mcp_wrapper.execute_with_retry  # Full name
                
                self.logger.info(f"Registered reliable tool: {server_name}_{tool_name}")
        
        self.logger.info(f"Reliable LlamaIndex agent initialized with {len(self.llama_tools)} tools")
    
    def _create_reliable_llama_tool(self, mcp_wrapper: ReliableMCPToolWrapper) -> FunctionTool:
        """Create a LlamaIndex FunctionTool with reliable metadata from MCP tool."""
        
        # Capture the agent instance to ensure proper statistics updates
        agent_instance = self
        
        def tool_function(**kwargs) -> str:
            """Execute MCP tool with comprehensive error handling and validation."""
            try:
                # Execute the tool with retry logic
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new event loop in thread for async execution
                    import concurrent.futures
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(mcp_wrapper.execute_with_retry(**kwargs))
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        result = future.result(timeout=mcp_wrapper.metadata.timeout)
                else:
                    result = loop.run_until_complete(mcp_wrapper.execute_with_retry(**kwargs))
                
                # Update statistics using the captured agent instance
                agent_instance.stats['total_tool_calls'] += 1
                agent_instance.stats['retry_attempts'] += result.retry_count
                
                if result.success:
                    agent_instance.stats['successful_tool_calls'] += 1
                else:
                    agent_instance.stats['failed_tool_calls'] += 1
                    if result.validation_errors:
                        agent_instance.stats['validation_errors'] += 1
                        agent_instance.stats['parameter_errors'] += 1
                
                # Format result for LlamaIndex
                if result.success:
                    formatted_result = agent_instance._format_reliable_tool_result(result)
                    
                    # Validate output for expected behavior
                    validation_result = agent_instance._validate_tool_output(
                        formatted_result, mcp_wrapper.metadata.name, kwargs
                    )
                    
                    if validation_result[0] == ValidationResult.ERROR:
                        agent_instance.stats['output_validation_errors'] += 1
                        return f"❌ OUTPUT VALIDATION ERROR: {validation_result[1]}\n\nOriginal output:\n{formatted_result}"
                    elif validation_result[0] == ValidationResult.WARNING:
                        agent_instance.stats['output_validation_warnings'] += 1
                        return f"⚠️ OUTPUT WARNING: {validation_result[1]}\n\nOutput:\n{formatted_result}"
                    
                    return formatted_result
                else:
                    error_msg = f"Tool execution failed: {result.message}"
                    if result.validation_errors:
                        error_msg += f" (Validation errors: {'; '.join(result.validation_errors)})"
                    return error_msg
                
            except Exception as e:
                # Update statistics for exceptions too
                agent_instance.stats['total_tool_calls'] += 1
                agent_instance.stats['failed_tool_calls'] += 1
                error_msg = f"Tool execution failed: {str(e)}"
                agent_instance.logger.error(f"Error in {mcp_wrapper.metadata.name}: {error_msg}")
                return error_msg
        
        # Set function metadata
        tool_function.__name__ = mcp_wrapper.metadata.name
        tool_function.__doc__ = mcp_wrapper.metadata.description
        
        # Create FunctionTool with reliable metadata
        return FunctionTool.from_defaults(
            fn=tool_function,
            name=mcp_wrapper.metadata.name,
            description=mcp_wrapper.metadata.description
        )
    
    def _format_reliable_tool_result(self, result: ReliableMCPToolResult) -> str:
        """Format reliable MCP tool result for LlamaIndex consumption."""
        if result.data is None:
            return result.message
        
        # Format based on data type
        if isinstance(result.data, (dict, list)):
            return json.dumps(result.data, indent=2, default=str)
        elif isinstance(result.data, str):
            return result.data
        else:
            return str(result.data)
    
    def _build_reliable_system_prompt(self) -> str:
        """Build highly reliable system prompt with detailed tool information and strict guidelines."""
        tool_descriptions = []
        
        for tool_name, mcp_wrapper in self.mcp_tools.items():
            metadata = mcp_wrapper.metadata
            desc = f"- {tool_name}: {metadata.description}"
            
            # Add detailed parameter information
            if metadata.parameters.get('properties'):
                params = []
                for param_name, param_info in metadata.parameters['properties'].items():
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', '')
                    required = param_name in metadata.parameters.get('required', [])
                    req_marker = " (REQUIRED)" if required else " (optional)"
                    
                    # Add type-specific guidance
                    type_guidance = ""
                    if param_type == 'array':
                        type_guidance = " - Use format: [\"item1\", \"item2\"]"
                    elif param_type == 'boolean':
                        type_guidance = " - Use: true/false"
                    elif param_type == 'integer':
                        type_guidance = " - Use numeric value only"
                    
                    params.append(f"    {param_name} ({param_type}){req_marker}: {param_desc}{type_guidance}")
                
                if params:
                    desc += f"\n  Parameters:\n" + "\n".join(params)
            
            # Add examples if available
            if metadata.examples:
                desc += f"\n  Examples: {metadata.examples}"
            
            tool_descriptions.append(desc)
        
        tools_text = "\n".join(tool_descriptions)
        
        return f"""You are a highly reliable AI assistant that MUST use the available tools to answer questions. 
CRITICAL: You must be extremely precise with tool usage and parameter formatting.

Available tools:
{tools_text}

CRITICAL RULES FOR RELIABLE TOOL USAGE:
1. ALWAYS use tools instead of giving instructions or educational responses
2. Use EXACT tool names as specified above (case-sensitive)
3. Format parameters EXACTLY as shown in the examples
4. For string parameters: use quotes: parameter="value"
5. For array parameters: use format: parameter=["item1", "item2"]
6. For boolean parameters: use true/false (no quotes)
7. For numeric parameters: use numbers only (no quotes)
8. NEVER skip required parameters
9. If unsure about a parameter, use a reasonable default or ask for clarification

To use a tool, respond with a function call in this EXACT format:
FUNCTION_CALL: tool_name(parameter1="value1", parameter2="value2")

EXACT EXAMPLES:
FUNCTION_CALL: calculate(expression="5 + 3")
FUNCTION_CALL: create_todos(todos=["Deploy web app", "Test deployment", "Monitor performance"])
FUNCTION_CALL: execute_command(command="uname -a")
FUNCTION_CALL: list_directory(path="/home/user")

You can make multiple function calls by using multiple FUNCTION_CALL lines.
After executing tools, I will provide you with the results, and you should give a final comprehensive answer based on the actual tool results.

IMPORTANT: If a tool fails, check the error message and try again with corrected parameters."""

    def _extract_function_calls_reliable(self, text: str) -> List[Dict[str, Any]]:
        """Extract function calls with highly reliable parsing."""
        function_calls = []
        
        # Multiple pattern matching strategies for maximum reliability
        patterns = [
            r'FUNCTION_CALL:\s*(\w+)\((.*?)\)(?=\s*(?:FUNCTION_CALL:|$))',
            r'\[FUNCTION_CALL:\s*(\w+)\((.*?)\)\]',
            r'function_call:\s*(\w+)\((.*?)\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
            for func_name, params_str in matches:
                try:
                    params = self._parse_parameters_reliable(func_name, params_str)
                    if params is not None:
                        function_calls.append({
                            'name': func_name,
                            'parameters': params
                        })
                        self.logger.info(f"Reliably parsed function call: {func_name} with params: {params}")
                except Exception as e:
                    self.logger.error(f"Failed to parse function call {func_name}: {e}")
                    continue
        
        return function_calls
    
    def _parse_parameters_reliable(self, func_name: str, params_str: str) -> Optional[Dict[str, Any]]:
        """Highly reliable parameter parsing with multiple fallback strategies."""
        if not params_str.strip():
            return {}
        
        params = {}
        
        # Strategy 1: AST parsing (most reliable)
        try:
            func_call = f"dummy({params_str})"
            parsed = ast.parse(func_call, mode='eval')
            if isinstance(parsed.body, ast.Call):
                for arg in parsed.body.keywords:
                    param_name = arg.arg
                    try:
                        value = ast.literal_eval(arg.value)
                        params[param_name] = value
                    except (ValueError, SyntaxError):
                        # Fallback: treat as string
                        params[param_name] = ast.unparse(arg.value).strip('"\'')
                return params
        except (ValueError, SyntaxError) as e:
            self.logger.debug(f"AST parsing failed for {func_name}: {e}")
        
        # Strategy 2: Enhanced regex parsing
        try:
            self._parse_params_with_enhanced_regex(params_str, params)
            if params:
                return params
        except Exception as e:
            self.logger.debug(f"Enhanced regex parsing failed for {func_name}: {e}")
        
        # Strategy 3: Simple key-value parsing
        try:
            self._parse_params_simple(params_str, params)
            if params:
                return params
        except Exception as e:
            self.logger.debug(f"Simple parsing failed for {func_name}: {e}")
        
        self.logger.warning(f"All parsing strategies failed for {func_name}: {params_str}")
        return None
    
    def _parse_params_with_enhanced_regex(self, params_str: str, params: Dict[str, Any]):
        """Enhanced regex-based parameter parsing."""
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
        
        # Handle boolean parameters: param=true/false
        bool_pattern = r'(\w+)=(true|false)'
        bool_matches = re.findall(bool_pattern, params_str, re.IGNORECASE)
        
        for param_name, bool_value in bool_matches:
            if param_name not in params:
                params[param_name] = bool_value.lower() == 'true'
        
        # Handle numeric parameters: param=123
        num_pattern = r'(\w+)=(\d+(?:\.\d+)?)'
        num_matches = re.findall(num_pattern, params_str)
        
        for param_name, num_value in num_matches:
            if param_name not in params:
                try:
                    if '.' in num_value:
                        params[param_name] = float(num_value)
                    else:
                        params[param_name] = int(num_value)
                except ValueError:
                    pass
    
    def _parse_params_simple(self, params_str: str, params: Dict[str, Any]):
        """Simple key-value parsing as last resort."""
        # Split by comma and handle each parameter
        param_parts = params_str.split(',')
        for part in param_parts:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                params[key] = value
    
    async def _execute_function_call_reliable(self, call: Dict[str, Any]) -> str:
        """Execute a function call with comprehensive error handling."""
        func_name = call['name']
        params = call['parameters']
        
        # Find the function in our registry (try multiple naming schemes)
        func = None
        for name_variant in [func_name, f"{func_name}", f"calculate_{func_name}", f"remote_{func_name}"]:
            if name_variant in self.tool_registry:
                func = self.tool_registry[name_variant]
                break
        
        if func is None:
            available_tools = list(self.tool_registry.keys())
            raise Exception(f"Function '{func_name}' not found. Available: {available_tools}")
        
        # Update tool call statistics
        self.stats['total_tool_calls'] += 1
        
        try:
            result = await func(**params)
            self.stats['successful_tool_calls'] += 1
            return str(result)
        except Exception as e:
            self.stats['failed_tool_calls'] += 1
            raise Exception(f"Function execution failed: {str(e)}")
    
    async def query(self, message: str) -> str:
        """Query the agent with highly reliable MCP integration."""
        if not self.llama_tools:
            return "Error: No tools available. Please set MCP servers first."
        
        start_time = datetime.now()
        self.stats['total_queries'] += 1
        
        try:
            # Add user message to memory
            user_msg = ChatMessage(role=MessageRole.USER, content=message)
            self.memory.put(user_msg)
            
            # Build reliable system prompt
            system_prompt = self._build_reliable_system_prompt()
            messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]
            messages.extend(self.memory.get())
            
            # Get response with function calling instructions
            response = await self.llm.achat(messages)
            response_content = response.message.content or ""
            
            self.logger.info(f"LLM Response: {response_content}")
            
            # Extract and execute function calls with reliable parsing
            function_calls = self._extract_function_calls_reliable(response_content)
            self.logger.info(f"Extracted {len(function_calls)} function calls from response")
            
            if function_calls:
                # Execute function calls with comprehensive error handling
                tool_results = []
                for call in function_calls:
                    try:
                        result = await self._execute_function_call_reliable(call)
                        tool_results.append(f"Tool {call['name']}: {result}")
                        self.logger.info(f"Successfully executed {call['name']}")
                    except Exception as e:
                        tool_results.append(f"Tool {call['name']} failed: {str(e)}")
                        self.logger.error(f"Failed to execute {call['name']}: {str(e)}")
                
                # Get final response with tool results
                tool_context = "\n".join(tool_results)
                final_prompt = f"Based on the following tool results, provide a concise and accurate answer:\n\n{tool_context}"
                
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
        """Get reliable information about available tools."""
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
                "examples": metadata.examples,
                "max_retries": metadata.max_retries,
                "timeout": metadata.timeout
            })
        return tools_info
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics with reliability metrics."""
        return {
            'agent_stats': self.stats.copy(),
            'tool_count': len(self.mcp_tools),
            'server_count': len(self.mcp_servers),
            'memory_size': len(self.memory.get()) if self.memory else 0,
            'reliability_metrics': {
                'success_rate': self.stats['successful_queries'] / max(self.stats['total_queries'], 1),
                'tool_success_rate': self.stats['successful_tool_calls'] / max(self.stats['total_tool_calls'], 1),
                'validation_error_rate': self.stats['validation_errors'] / max(self.stats['total_tool_calls'], 1),
                'avg_retries_per_call': self.stats['retry_attempts'] / max(self.stats['total_tool_calls'], 1)
            }
        }
    
    def _validate_tool_output(self, output: str, tool_name: str, parameters: Dict[str, Any]) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """
        Validate tool output for expected behavior.
        
        Args:
            output: The tool output to validate
            tool_name: Name of the tool that produced the output
            parameters: Parameters used in the tool call
        
        Returns:
            Tuple of (ValidationResult, message, details)
        """
        # Determine command type based on tool name and parameters
        command_type = self._determine_command_type(tool_name, parameters)
        
        # Create context for validation
        context = self._create_validation_context(tool_name, parameters)
        
        # Validate output
        return self.output_validator.validate_output(output, command_type, context)
    
    def _determine_command_type(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Determine the type of command for validation."""
        tool_name_lower = tool_name.lower()
        
        if "mkdir" in tool_name_lower or "directory" in tool_name_lower:
            return "directory_creation"
        elif "list" in tool_name_lower and "directory" in tool_name_lower:
            return "directory_listing"
        elif "touch" in tool_name_lower or ("write" in tool_name_lower and "file" in tool_name_lower):
            return "file_creation"
        elif "read" in tool_name_lower and "file" in tool_name_lower:
            return "file_reading"
        elif "execute" in tool_name_lower and "command" in tool_name_lower:
            # Analyze the command to determine type
            command = parameters.get('command', '').lower()
            if 'mkdir' in command:
                return "directory_creation"
            elif 'ls' in command or 'dir' in command:
                return "directory_listing"
            elif 'touch' in command or 'echo' in command:
                return "file_creation"
            elif 'cat' in command or 'head' in command or 'tail' in command:
                return "file_reading"
            else:
                return "command_execution"
        else:
            return "command_execution"
    
    def _create_validation_context(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create validation context based on tool parameters."""
        context = {}
        
        # Extract expected names from parameters
        if 'command' in parameters:
            command = parameters['command']
            # Extract directory/file names from common commands
            if command.startswith('mkdir '):
                context['expected_name'] = command[6:].strip()
            elif command.startswith('touch '):
                context['expected_name'] = command[6:].strip()
            elif '>' in command and 'echo' in command:
                # Extract filename from echo command
                parts = command.split('>')
                if len(parts) > 1:
                    context['expected_name'] = parts[1].strip()
        
        # Extract from other parameter types
        if 'path' in parameters:
            context['expected_name'] = parameters['path']
        if 'file_path' in parameters:
            context['expected_name'] = parameters['file_path']
        if 'directory' in parameters:
            context['expected_name'] = parameters['directory']
        
        return context


# Compatibility wrapper for existing code
class ReliableAIShowmakerAgent:
    """
    Reliable compatibility wrapper to maintain existing API while using bulletproof LlamaIndex internally.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize with reliable LlamaIndex backend."""
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.reliable_agent")
        self.manager = None  # Will be set during initialization
        self.agent = None
        self.start_time = datetime.now()
        
    async def initialize(self) -> None:
        """Initialize the agent and MCP servers."""
        from core.enhanced_mcp_agent import EnhancedMCPServerManager
        
        self.manager = EnhancedMCPServerManager()
        await self.manager.initialize_servers()
        self.agent = ReliableLlamaIndexAgent(self.config)
        self.agent.set_mcp_servers(self.manager.servers)
        self.logger.info("ReliableAIShowmakerAgent initialized with bulletproof LlamaIndex backend")
    
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
        if not self.manager:
            return {}
        return self.manager.get_server_stats()
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        if self.manager:
            await self.manager.shutdown()
