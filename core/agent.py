#!/usr/bin/env python3
"""
Unified AI-Showmaker Agent

This module provides a unified agent that integrates with MCP servers,
MCP-Zero plugins, and LLM capabilities for intelligent task execution.
"""

import logging
import asyncio
import json
import re
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from llama_index.core.tools import FunctionTool
from llama_index.core.settings import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.tools.types import BaseTool

# Import our custom LLM implementations
from .custom_llm import InferenceNetLLM
from .local_llm import OllamaLLM, LlamaCppLLM

from .config import ConfigManager
from .exceptions import AIShowmakerError
from .mcp_zero import MCPServerDiscovery
from mcp_servers.calculation.server import CalculationMCPServer
from mcp_servers.remote.server import RemoteMCPServer
from mcp_servers.development.server import DevelopmentMCPServer
from mcp_servers.monitoring.server import MonitoringMCPServer
from mcp_servers.websearch.server import WebSearchMCPServer


@dataclass
class TaskPlan:
    """Represents a planned task with multiple steps."""
    task_id: str
    description: str
    steps: List['TaskStep']
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class TaskStep:
    """Represents a single step in a task plan."""
    step_id: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MCPToolMetadata:
    """Enhanced metadata for MCP tools."""
    name: str
    description: str
    server: str
    category: str
    version: str
    parameters: Dict[str, Any]
    examples: List[str] = field(default_factory=list)


class MCPToolWrapper:
    """Wrapper for MCP tools with enhanced metadata."""
    
    def __init__(self, tool: BaseTool, server_name: str, category: str = "utilities"):
        self.tool = tool
        self.metadata = MCPToolMetadata(
            name=getattr(tool, 'name', str(tool)),
            description=getattr(tool, 'description', ""),
            server=server_name,
            category=getattr(tool, 'category', category),
            version=getattr(tool, 'version', "1.0.0"),
            parameters=getattr(tool, 'parameters', {}),
            examples=[]
        )


class IntelligentTaskPlanner:
    """Intelligent task planning for complex operations."""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_showmaker.task_planner")
        
    def is_complex_task(self, query: str) -> bool:
        """Determine if a task is complex and needs planning."""
        complex_indicators = [
            "deploy", "set up", "configure", "install", "build", "create",
            "process", "analyze", "monitor", "pipeline", "environment"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in complex_indicators)
    
    def _classify_task(self, query: str) -> str:
        """Classify task into different types."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["deploy", "deployment"]):
            return "deployment"
        elif any(word in query_lower for word in ["set up", "development", "environment"]):
            return "development"
        elif any(word in query_lower for word in ["monitor", "monitoring", "tracking"]):
            return "monitoring"
        elif any(word in query_lower for word in ["process", "analyze", "dataset"]):
            return "data_processing"
        elif any(word in query_lower for word in ["install", "system", "software"]):
            return "system_administration"
        else:
            return "general"
    
    def create_task_plan(self, query: str) -> TaskPlan:
        """Create a task plan for complex operations."""
        task_id = f"task_{int(time.time())}"
        task_type = self._classify_task(query)
        
        # Create steps based on task type
        steps = self._create_steps_for_task_type(query, task_type)
        
        return TaskPlan(
            task_id=task_id,
            description=query,
            steps=steps
        )
    
    def _create_steps_for_task_type(self, query: str, task_type: str) -> List[TaskStep]:
        """Create appropriate steps for different task types."""
        steps = []
        
        if task_type == "deployment":
            steps = [
                TaskStep("step_1", "Check system requirements", "system_info", {}),
                TaskStep("step_2", "Validate deployment environment", "remote_execute", {"command": "pwd"}),
                TaskStep("step_3", "Execute deployment", "remote_execute", {"command": "deploy"}),
                TaskStep("step_4", "Verify deployment", "monitoring_status", {})
            ]
        elif task_type == "development":
            steps = [
                TaskStep("step_1", "Check current environment", "system_info", {}),
                TaskStep("step_2", "Set up development tools", "remote_execute", {"command": "setup_dev"}),
                TaskStep("step_3", "Verify setup", "remote_execute", {"command": "verify_dev"})
            ]
        elif task_type == "monitoring":
            steps = [
                TaskStep("step_1", "Check current monitoring status", "monitoring_status", {}),
                TaskStep("step_2", "Configure monitoring", "remote_execute", {"command": "setup_monitoring"}),
                TaskStep("step_3", "Verify monitoring", "monitoring_status", {})
            ]
        else:
            # Generic steps for other task types
            steps = [
                TaskStep("step_1", "Analyze requirements", "system_info", {}),
                TaskStep("step_2", "Execute task", "remote_execute", {"command": query}),
                TaskStep("step_3", "Verify completion", "system_info", {})
            ]
        
        return steps


class UnifiedAIShowmakerAgent:
    """
    Unified AI-Showmaker Agent that handles all functionalities.
    
    This agent consolidates:
    - MCP tool management
    - Task planning
    - Web search integration
    - Statistics tracking
    - MCP-Zero integration
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.agent")
        
        # Core components
        self.mcp_servers: Dict[str, Any] = {}
        self.mcp_tools: Dict[str, MCPToolWrapper] = {}
        self.llama_tools: Dict[str, BaseTool] = {}
        
        # Task planning
        self.task_planner = IntelligentTaskPlanner()
        self.active_task_plans: Dict[str, TaskPlan] = {}
        
        # MCP-Zero integration
        self.mcp_zero_discovery: Optional[MCPServerDiscovery] = None
        
        # Statistics and memory
        self.statistics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_tool_calls': 0,
            'start_time': datetime.now()
        }
        
        self.task_planning_metrics = {
            'complex_tasks_detected': 0,
            'task_plans_created': 0,
            'task_plans_completed': 0,
            'task_plans_failed': 0
        }
        
        # LLM and chat functionality
        self.llm = None
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=4000)
        
        # Tool execution registry (now handled by LlamaIndex tools)
        # self.tool_registry = {}  # name -> function mapping
        
    async def initialize(self) -> None:
        """Initialize the agent with all MCP servers and tools."""
        try:
            self.logger.info("Initializing Unified AI-Showmaker Agent...")
            
            # Initialize MCP servers
            await self._initialize_mcp_servers()
            
            # Initialize MCP-Zero discovery
            await self._initialize_mcp_zero()
            
            # Initialize LLM
            await self._initialize_llm()
            
            # Initialize chat functionality
            await self._initialize_chat_functionality()
            
            self.logger.info("Agent initialized successfully!")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {str(e)}")
            raise AIShowmakerError(f"Agent initialization failed: {str(e)}")
    
    async def _initialize_mcp_servers(self) -> None:
        """Initialize all MCP servers."""
        try:
            # Initialize calculation server
            self.mcp_servers['calculation'] = CalculationMCPServer()
            await self.mcp_servers['calculation'].initialize()
            
            # Initialize remote server
            self.mcp_servers['remote'] = RemoteMCPServer()
            await self.mcp_servers['remote'].initialize()
            
            # Initialize development server
            self.mcp_servers['development'] = DevelopmentMCPServer()
            await self.mcp_servers['development'].initialize()
            
            # Initialize monitoring server
            self.mcp_servers['monitoring'] = MonitoringMCPServer()
            await self.mcp_servers['monitoring'].initialize()
            
            # Initialize web search server
            self.mcp_servers['websearch'] = WebSearchMCPServer()
            await self.mcp_servers['websearch'].initialize()
            
            # Register tools from all servers
            await self._register_mcp_tools()
            
            self.logger.info("All MCP servers initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP servers: {str(e)}")
            raise
    
    async def _initialize_mcp_zero(self) -> None:
        """Initialize MCP-Zero discovery system."""
        try:
            self.mcp_zero_discovery = MCPServerDiscovery()
            await self.mcp_zero_discovery.discover_servers()
            
            # Register discovered tools
            discovered_servers = await self.mcp_zero_discovery.get_all_servers()
            for server_name, server in discovered_servers.items():
                for tool_name, tool in server.tools.items():
                    wrapper = MCPToolWrapper(tool, server_name, getattr(tool, 'category', 'utilities'))
                    self.mcp_tools[f"{server_name}_{tool_name}"] = wrapper
            
            self.logger.info(f"MCP-Zero discovered {len(discovered_servers)} servers")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP-Zero: {str(e)}")
            # Don't fail initialization if MCP-Zero fails
    
    async def _initialize_llm(self) -> None:
        """Initialize the LLM for intelligent responses."""
        try:
            # Try to initialize inference.net LLM first
            inference_net_key = self.config.get('inference_net_key')
            if inference_net_key:
                self.llm = InferenceNetLLM(
                    model=self.config.get('inference_net_model', 'Qwen/Qwen2.5-Coder-32B-Instruct'),
                    api_key=inference_net_key,
                    base_url=self.config.get('inference_net_base_url', 'https://api.inference.net/v1'),
                    temperature=0
                )
                self.logger.info("Initialized InferenceNet LLM")
            else:
                # Try to initialize local Ollama LLM
                try:
                    self.llm = OllamaLLM(
                        model=self.config.get('local_model', 'llama3.2:3b'),
                        base_url=self.config.get('ollama_base_url', 'http://localhost:11434'),
                        temperature=0
                    )
                    self.logger.info("Initialized local Ollama LLM")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize local LLM: {e}")
                    self.llm = None
            
            # Set global settings if LLM is available
            if self.llm:
                Settings.llm = self.llm
                
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {str(e)}")
            self.llm = None
    
    async def _initialize_chat_functionality(self) -> None:
        """Initialize chat functionality with LLM integration using standard LlamaIndex tools."""
        try:
            if self.llm:
                # Convert MCP tools to standard LlamaIndex FunctionTools
                for tool_name, wrapper in self.mcp_tools.items():
                    # Create a proper async function for the tool
                    async def execute_mcp_tool(**kwargs):
                        try:
                            result = await self._execute_mcp_tool(tool_name, **kwargs)
                            return f"Tool {tool_name} executed successfully: {result}"
                        except Exception as e:
                            return f"Tool {tool_name} failed: {str(e)}"
                    
                    # Create the LlamaIndex tool
                    mcp_tool = FunctionTool.from_defaults(
                        fn=execute_mcp_tool,
                        name=tool_name,
                        description=wrapper.metadata.description or f"Execute {tool_name} MCP tool"
                    )
                    
                    self.llama_tools[tool_name] = mcp_tool
                
                self.logger.info(f"Initialized chat functionality with {len(self.llama_tools)} LlamaIndex tools")
            else:
                self.logger.info("No LLM available, using basic tool execution")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize chat functionality: {str(e)}")
            raise
    
    async def _register_mcp_tools(self) -> None:
        """Register tools from all MCP servers."""
        for server_name, server in self.mcp_servers.items():
            for tool_name, tool in server.tools.items():
                wrapper = MCPToolWrapper(tool, server_name, getattr(tool, 'category', 'utilities'))
                self.mcp_tools[f"{server_name}_{tool_name}"] = wrapper
        
        self.logger.info(f"Registered {len(self.mcp_tools)} MCP tools")
    
    async def _execute_mcp_tool(self, tool_name: str, **kwargs) -> str:
        """Execute an MCP tool by name."""
        try:
            if tool_name in self.mcp_tools:
                wrapper = self.mcp_tools[tool_name]
                server_name = wrapper.metadata.server
                tool_name_short = tool_name.replace(f"{server_name}_", "")
                
                # Check if this is a built-in MCP server or MCP-Zero plugin
                if server_name in self.mcp_servers:
                    # Built-in MCP server - execute using the server's execute_tool method
                    server = self.mcp_servers[server_name]
                    # Pass kwargs as a dictionary to match the base server API
                    result = await server.execute_tool(tool_name_short, kwargs)
                else:
                    # MCP-Zero plugin - execute directly from the tool
                    tool = wrapper.tool
                    if hasattr(tool, 'execute_func'):
                        # Use the tool's execute_func directly
                        result = await tool.execute_func(**kwargs)
                    else:
                        # Fallback to calling the tool object directly
                        result = await tool(**kwargs)
                
                self.statistics['total_tool_calls'] += 1
                
                # Convert MCPToolResult to string
                if hasattr(result, 'data'):
                    return str(result.data)
                else:
                    return str(result)
            else:
                return f"Error: Tool '{tool_name}' not found"
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error executing tool: {str(e)}"
    
    async def query(self, query: str) -> str:
        """Process a user query with intelligent task planning."""
        try:
            self.statistics['total_queries'] += 1
            start_time = time.time()
            
            # TEMPORARILY DISABLE OLD TASK PLANNING - use only LLM integration
            # Check if this is a complex task
            # if self.task_planner.is_complex_task(query):
            #     self.task_planning_metrics['complex_tasks_detected'] += 1
            #     return await self._handle_complex_task(query)
            # else:
            # Simple task - execute directly
            return await self._handle_simple_query(query)
                
        except Exception as e:
            self.statistics['failed_queries'] += 1
            self.logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"
        finally:
            self.statistics['successful_queries'] += 1
    
    async def _handle_complex_task(self, query: str) -> str:
        """Handle complex tasks with task planning."""
        try:
            # Create task plan
            task_plan = self.task_planner.create_task_plan(query)
            self.active_task_plans[task_plan.task_id] = task_plan
            self.task_planning_metrics['task_plans_created'] += 1
            
            # Execute task plan
            result = await self._execute_task_plan(task_plan)
            
            return f"Task completed: {result}"
            
        except Exception as e:
            self.logger.error(f"Error handling complex task: {str(e)}")
            return f"Error handling complex task: {str(e)}"
    
    async def _handle_simple_query(self, query: str) -> str:
        """Handle simple queries with LLM integration when available."""
        try:
            if self.llm:
                # Use LLM for intelligent responses
                return await self._handle_query_with_llm(query)
            else:
                # Fallback to basic pattern matching
                return await self._handle_query_basic(query)
                
        except Exception as e:
            self.logger.error(f"Error handling simple query: {str(e)}")
            return f"Error handling simple query: {str(e)}"
    
    async def _handle_query_with_llm(self, query: str) -> str:
        """Handle queries using LLM for intelligent responses with standard tool calling."""
        try:
            if not self.llama_tools:
                # Fallback to basic handling if no tools available
                return await self._handle_query_basic(query)
            
            # Use a simple approach: directly call the LLM with tool information
            # and then manually execute the tools based on the response
            
            # Build a simple prompt asking the LLM to use tools
            tool_prompt = f"""You have access to the following tools. Use them when needed:

Available tools:
{chr(10).join([f"- {name}: {getattr(tool, 'description', 'Execute MCP tool')}" for name, tool in self.llama_tools.items()])}

User query: {query}

Please respond with the tool name and parameters you want to use, or provide a helpful answer if no tools are needed."""
            
            # Get LLM response
            messages = [ChatMessage(role=MessageRole.USER, content=tool_prompt)]
            response = await self.llm.achat(messages)
            response_content = response.message.content or ""
            
            self.logger.info(f"LLM Response: {response_content}")
            
            # Smart tool detection - look for the most specific tool mentioned
            executed_tools = []
            
            # First, try to find exact tool names mentioned in the response
            mentioned_tools = []
            for tool_name in self.llama_tools.keys():
                # Look for tool names that are specifically mentioned (not just partial matches)
                if f"`{tool_name}`" in response_content or f"'{tool_name}'" in response_content or f'"{tool_name}"' in response_content:
                    mentioned_tools.append(tool_name)
                elif f"Tool name: {tool_name}" in response_content:
                    mentioned_tools.append(tool_name)
                elif f"Tool Name: {tool_name}" in response_content:
                    mentioned_tools.append(tool_name)
            
            self.logger.info(f"Found mentioned tools: {mentioned_tools}")
            
            # If no specific tools mentioned, fall back to pattern matching but be more selective
            if not mentioned_tools:
                for tool_name, tool in self.llama_tools.items():
                    # Only match if the tool name appears in a meaningful context
                    if (tool_name.lower() in response_content.lower() and 
                        not any(other_tool in tool_name.lower() for other_tool in self.llama_tools.keys() if other_tool != tool_name)):
                        mentioned_tools.append(tool_name)
            
            # Execute the mentioned tools
            for tool_name in mentioned_tools:
                if tool_name in self.llama_tools:
                    tool = self.llama_tools[tool_name]
                    self.logger.info(f"Executing tool: {tool_name} with tool object: {type(tool)}")
                    try:
                        # Extract parameters from the LLM response
                        params = self._extract_tool_params(response_content, tool_name)
                        self.logger.info(f"Extracted params for {tool_name}: {params}")
                        
                        # Execute the tool with extracted parameters
                        if params:
                            result = await tool.acall(**params)
                            executed_tools.append(f"Tool {tool_name}: {result}")
                        else:
                            # Try with default parameters
                            result = await tool.acall()
                            executed_tools.append(f"Tool {tool_name}: {result}")
                            
                    except Exception as e:
                        self.logger.error(f"Tool execution failed: {e}")
                        continue
            
            # If tools were executed, return the results
            if executed_tools:
                return "\n".join(executed_tools)
            
            # If no tools were executed, return the LLM response
            return response_content
            
        except Exception as e:
            self.logger.error(f"Error in LLM query handling: {str(e)}")
            # Fallback to basic handling
            return await self._handle_query_basic(query)
    
    def _extract_tool_params(self, response_content: str, tool_name: str) -> Dict[str, Any]:
        """Extract tool parameters from LLM response."""
        params = {}
        
        # Look for JSON-like parameter structures
        import re
        import json
        
        # Try to find JSON parameters
        json_pattern = r'Parameters:\s*\{([^}]+)\}'
        json_matches = re.findall(json_pattern, response_content, re.IGNORECASE)
        
        for match in json_matches:
            try:
                # Clean up the JSON string
                clean_json = match.replace('\n', '').replace('"', '"').replace('"', '"')
                # Try to parse as JSON
                parsed = json.loads(f"{{{clean_json}}}")
                params.update(parsed)
            except Exception:
                # If JSON parsing fails, try to extract key-value pairs
                key_value_pattern = r'(\w+):\s*([^,\n]+)'
                kv_matches = re.findall(key_value_pattern, match)
                for key, value in kv_matches:
                    # Clean up the value
                    clean_value = value.strip().strip('"').strip("'")
                    if clean_value.isdigit():
                        params[key] = int(clean_value)
                    elif clean_value.lower() in ['true', 'false']:
                        params[key] = clean_value.lower() == 'true'
                    else:
                        params[key] = clean_value
        
        # For calculation tools, also look for expression patterns
        if "calculation" in tool_name.lower():
            expr_pattern = r'expression["\']?\s*:\s*["\']([^"\']+)["\']'
            expr_match = re.search(expr_pattern, response_content, re.IGNORECASE)
            if expr_match:
                params['expression'] = expr_match.group(1)
        
        return params
    
    async def _handle_query_basic(self, query: str) -> str:
        """Handle queries with basic pattern matching."""
        query_lower = query.lower()
        
        # Check for calculation queries
        if any(word in query_lower for word in ["calculate", "math", "compute", "+", "-", "*", "/"]):
            if "calculate" in query_lower:
                expression = query_lower.split("calculate")[-1].strip()
                if expression:
                    result = await self._execute_mcp_tool("calculation_calculate", expression=expression)
                    return f"Calculation result: {result}"
        
        # Check for system info queries
        if "system" in query_lower and "info" in query_lower:
            result = await self._execute_mcp_tool("remote_system_info")
            return f"System information: {result}"
        
        # Check for tool info queries
        if "tools" in query_lower and "available" in query_lower:
            tools_info = self.get_tools_info()
            return f"Available tools: {len(tools_info)} tools from various MCP servers"
        
        # Default response
        return f"I can help you with various tasks. Available tools: {len(self.mcp_tools)} MCP tools. Try asking about calculations, system information, or available tools."
    
    def _build_system_prompt(self) -> str:
        """Build a comprehensive system prompt for basic queries (tools handled by LlamaIndex)."""
        prompt = """You are an expert AI development assistant powered by specialized tool servers.

You have access to various MCP tools for:
- Mathematical calculations and advanced math operations
- Remote server operations and development tasks
- Monitoring and progress tracking
- Web search and content extraction

When users ask for specific operations, you can use the available tools through the standard tool calling interface.

For general questions, provide helpful information based on your knowledge."""
        
        return prompt
    
    # Note: Function calling is now handled by LlamaIndex's ReActAgent
    # No need for manual regex parsing
    
    # Note: Parameter parsing is now handled by LlamaIndex's ReActAgent
    # No need for manual parameter parsing
    
    # Note: Tool execution is now handled by LlamaIndex's ReActAgent
    # No need for manual tool execution
    
    # Note: Function mapping is now handled by LlamaIndex's ReActAgent
    # No need for manual function mapping
    
    async def _execute_task_plan(self, task_plan: TaskPlan) -> str:
        """Execute a task plan step by step."""
        try:
            task_plan.status = "in_progress"
            task_plan.started_at = datetime.now()
            
            results = []
            
            for step in task_plan.steps:
                step.status = "in_progress"
                
                try:
                    # Execute the step
                    result = await self._execute_mcp_tool(step.tool_name, **step.parameters)
                    step.result = result
                    step.status = "completed"
                    results.append(f"Step {step.step_id}: {result}")
                    
                except Exception as e:
                    step.error = str(e)
                    step.status = "failed"
                    results.append(f"Step {step.step_id}: Failed - {str(e)}")
            
            # Update task plan status
            if all(step.status == "completed" for step in task_plan.steps):
                task_plan.status = "completed"
                self.task_planning_metrics['task_plans_completed'] += 1
            else:
                task_plan.status = "failed"
                self.task_planning_metrics['task_plans_failed'] += 1
            
            task_plan.completed_at = datetime.now()
            
            return "\n".join(results)
            
        except Exception as e:
            task_plan.status = "failed"
            task_plan.error = str(e)
            task_plan.completed_at = datetime.now()
            self.task_planning_metrics['task_plans_failed'] += 1
            raise
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all available tools."""
        tools_info = []
        
        # Add MCP tools
        for tool_name, wrapper in self.mcp_tools.items():
            tools_info.append({
                'name': tool_name,
                'description': wrapper.metadata.description,
                'server': wrapper.metadata.server,
                'category': wrapper.metadata.category,
                'version': wrapper.metadata.version,
                'parameters': wrapper.metadata.parameters
            })
        
        # Add LlamaIndex tools
        for tool_name, tool in self.llama_tools.items():
            tools_info.append({
                'name': tool_name,
                'description': getattr(tool.metadata, 'description', ''),
                'server': 'llamaindex',
                'category': 'llamaindex',
                'version': '1.0.0',
                'parameters': {}
            })
        
        return tools_info
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics."""
        uptime = (datetime.now() - self.statistics['start_time']).total_seconds()
        
        return {
            'agent_stats': self.statistics.copy(),
            'task_planning_metrics': self.task_planning_metrics.copy(),
            'tool_count': len(self.mcp_tools),
            'server_count': len(self.mcp_servers),
            'uptime_seconds': uptime
        }
    
    async def _get_server_stats(self) -> Dict[str, Any]:
        """Get statistics for all MCP servers."""
        server_stats = {}
        
        for server_name, server in self.mcp_servers.items():
            try:
                server_stats[server_name] = {
                    'tool_count': len(server.tools),
                    'statistics': getattr(server, 'get_statistics', lambda: {})()
                }
            except Exception as e:
                server_stats[server_name] = {
                    'error': str(e),
                    'tool_count': 0,
                    'statistics': {}
                }
        
        return server_stats
    
    def get_active_task_plans(self) -> Dict[str, TaskPlan]:
        """Get all active task plans."""
        return self.active_task_plans.copy()
    
    def get_llm_info(self) -> Dict[str, Any]:
        """Get information about the current LLM."""
        if not self.llm:
            return {"status": "no_llm_available"}
        
        try:
            return {
                "status": "available",
                "model_name": getattr(self.llm, 'model', 'unknown'),
                "type": type(self.llm).__name__,
                "temperature": getattr(self.llm, 'temperature', 'unknown'),
                "base_url": getattr(self.llm, 'base_url', 'unknown') if hasattr(self.llm, 'base_url') else 'local'
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def shutdown(self) -> None:
        """Shutdown the agent and all servers."""
        try:
            self.logger.info("Shutting down agent...")
            
            # Shutdown MCP servers
            for server_name, server in self.mcp_servers.items():
                try:
                    if hasattr(server, 'shutdown'):
                        await server.shutdown()
                    self.logger.info(f"Shutdown server: {server_name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down {server_name}: {e}")
            
            # Shutdown MCP-Zero
            if self.mcp_zero_discovery:
                await self.mcp_zero_discovery.shutdown_all()
            
            self.logger.info("Agent shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")


# Alias for backward compatibility
AIShowmakerAgent = UnifiedAIShowmakerAgent