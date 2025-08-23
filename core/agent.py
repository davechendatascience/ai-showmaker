"""
Enhanced AI-Showmaker Agent with MCP Server Integration

This module provides the main agent class that orchestrates multiple
MCP servers and provides a unified interface for tool execution.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import initialize_agent, AgentType

from mcp_servers.calculation.server import CalculationMCPServer
from mcp_servers.remote.server import RemoteMCPServer  
from mcp_servers.development.server import DevelopmentMCPServer
from mcp_servers.monitoring.server import MonitoringMCPServer
from .config import ConfigManager
from .exceptions import AIShowmakerError


class MCPServerManager:
    """Manages multiple MCP servers and provides unified tool access."""
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.tools: Dict[str, Tool] = {}
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the server manager."""
        logger = logging.getLogger("ai_showmaker.core")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    async def initialize_servers(self) -> None:
        """Initialize all MCP servers."""
        try:
            # Initialize calculation server
            self.servers['calculation'] = CalculationMCPServer()
            await self.servers['calculation'].initialize()
            
            # Initialize remote server  
            self.servers['remote'] = RemoteMCPServer()
            await self.servers['remote'].initialize()
            
            # Initialize development server
            self.servers['development'] = DevelopmentMCPServer()
            await self.servers['development'].initialize()
            
            # Initialize monitoring server
            self.servers['monitoring'] = MonitoringMCPServer()
            await self.servers['monitoring'].initialize()
            
            self.logger.info("All MCP servers initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP servers: {str(e)}")
            raise AIShowmakerError(f"Server initialization failed: {str(e)}")
    
    def _normalize_todos_parameter(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize todos parameter to expected format."""
        try:
            import json
            
            todos = arguments.get("todos")
            if not todos:
                return arguments
            
            # Handle different input formats
            if isinstance(todos, str):
                # Try to parse as JSON
                try:
                    todos = json.loads(todos)
                except json.JSONDecodeError:
                    # If not JSON, split by common delimiters and create simple todos
                    if "," in todos:
                        todo_items = [item.strip() for item in todos.split(",")]
                    elif "\n" in todos:
                        todo_items = [item.strip() for item in todos.split("\n")]
                    else:
                        todo_items = [todos.strip()]
                    
                    todos = []
                    for item in todo_items:
                        if item:
                            todos.append({
                                "content": item,
                                "status": "pending",
                                "activeForm": f"Working on {item.lower()}"
                            })
            
            # Handle list of strings (convert to proper format)
            if isinstance(todos, list) and todos:
                normalized_todos = []
                for item in todos:
                    if isinstance(item, str):
                        normalized_todos.append({
                            "content": item,
                            "status": "pending", 
                            "activeForm": f"Working on {item.lower()}"
                        })
                    elif isinstance(item, dict):
                        # Ensure required fields exist
                        if "content" not in item:
                            continue
                        normalized_item = {
                            "content": item.get("content", ""),
                            "status": item.get("status", "pending"),
                            "activeForm": item.get("activeForm", f"Working on {item.get('content', '').lower()}")
                        }
                        normalized_todos.append(normalized_item)
                
                arguments["todos"] = normalized_todos
            
            return arguments
            
        except Exception as e:
            self.logger.error(f"Error normalizing todos parameter: {str(e)}")
            return arguments
    
    def _convert_mcp_tool_to_langchain(self, server_name: str, mcp_tool) -> Tool:
        """Convert an MCP tool to a LangChain tool."""
        
        def execute_tool(*args, **kwargs) -> str:
            """Execute the MCP tool synchronously for LangChain."""
            try:
                # Convert args to proper format for MCP server
                if args and len(args) == 1:
                    # Handle single string argument (common in LangChain)
                    if isinstance(args[0], str):
                        try:
                            import json
                            # Try to parse as JSON first
                            arguments = json.loads(args[0])
                            
                            # Special handling for monitoring server todos
                            if mcp_tool.name == "create_todos" and "todos" in arguments:
                                arguments = self._normalize_todos_parameter(arguments)
                                
                        except json.JSONDecodeError:
                            # If not JSON, treat as single parameter
                            param_names = list(mcp_tool.parameters.get('properties', {}).keys())
                            if param_names:
                                param_name = param_names[0]
                                arguments = {param_name: args[0]}
                            else:
                                arguments = {"input": args[0]}
                    else:
                        arguments = args[0]
                        if mcp_tool.name == "create_todos" and "todos" in arguments:
                            arguments = self._normalize_todos_parameter(arguments)
                else:
                    arguments = kwargs
                    if mcp_tool.name == "create_todos" and "todos" in arguments:
                        arguments = self._normalize_todos_parameter(arguments)
                
                # Run the async MCP tool - handle existing event loop
                try:
                    # Try to get the current event loop
                    current_loop = asyncio.get_event_loop()
                    if current_loop.is_running():
                        # Use asyncio.run_coroutine_threadsafe if we're in a running loop
                        import concurrent.futures
                        import threading
                        
                        def run_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(
                                    self.servers[server_name].execute_tool(mcp_tool.name, arguments)
                                )
                            finally:
                                new_loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_in_thread)
                            result = future.result(timeout=30)
                    else:
                        # No running loop, safe to use run_until_complete
                        result = current_loop.run_until_complete(
                            self.servers[server_name].execute_tool(mcp_tool.name, arguments)
                        )
                except RuntimeError:
                    # No event loop in current thread, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self.servers[server_name].execute_tool(mcp_tool.name, arguments)
                        )
                    finally:
                        loop.close()
                
                if result.result_type.value == "success":
                    return str(result.data)
                else:
                    return f"Error: {result.message}"
                    
            except Exception as e:
                self.logger.error(f"Tool execution failed: {mcp_tool.name} - {str(e)}")
                return f"Tool execution failed: {str(e)}"
        
        # Create LangChain tool
        return Tool(
            name=f"{server_name}_{mcp_tool.name}",
            func=execute_tool,
            description=mcp_tool.description
        )
    
    def get_langchain_tools(self) -> List[Tool]:
        """Get all tools as LangChain tools."""
        tools = []
        
        for server_name, server in self.servers.items():
            for tool_name, mcp_tool in server.tools.items():
                langchain_tool = self._convert_mcp_tool_to_langchain(server_name, mcp_tool)
                tools.append(langchain_tool)
        
        return tools
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get information about all servers."""
        info = {}
        for server_name, server in self.servers.items():
            info[server_name] = server.get_server_info()
        return info
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers."""
        for server_name, server in self.servers.items():
            try:
                await server.shutdown()
                self.logger.info(f"Shutdown {server_name} server")
            except Exception as e:
                self.logger.error(f"Error shutting down {server_name}: {str(e)}")


class AIShowmakerAgent:
    """
    Enhanced AI-Showmaker agent with MCP server integration.
    
    Provides a unified interface for interacting with multiple specialized
    MCP servers through a LangChain-based conversational agent.
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.server_manager = MCPServerManager()
        self.agent = None
        self.logger = logging.getLogger("ai_showmaker.agent")
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'start_time': datetime.now()
        }
    
    async def initialize(self) -> None:
        """Initialize the agent and all MCP servers."""
        try:
            # Initialize MCP servers
            await self.server_manager.initialize_servers()
            
            # Get tools from all servers
            tools = self.server_manager.get_langchain_tools()
            
            # Set up the LangChain agent
            system_message = """You are an expert AI development assistant powered by specialized tool servers.

You have access to four main categories of tools:
1. Calculation tools - Advanced mathematical operations, variables, scientific functions
2. Remote tools - SSH/SFTP operations on remote servers with security validation  
3. Development tools - Git operations, file search, package management
4. Monitoring tools - Todo list management, progress tracking, session management

CRITICAL TODO USAGE RULES:
- ALWAYS create a todo list for ANY task with 2+ steps using monitoring_create_todos
- ALWAYS update todo status with monitoring_update_todo_status as you complete each step
- ALWAYS use monitoring_get_current_todos to check progress when asked about status
- Examples of multi-step tasks: building applications, deploying services, setting up environments, creating scripts with testing
- Even simple tasks like "create and test a script" require todos: 1) create script, 2) test script

WORKFLOW: Start every multi-step task by creating todos, then execute steps while updating status.

Always use the appropriate tools to complete tasks. Be methodical and explain your actions.
For interactive programs, use the remote server's execute_command tool with input_data parameter.
"""
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", "{input}")
            ])
            
            # Initialize the language model
            chat = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                temperature=0,
                google_api_key=self.config.get('google_api_key')
            )
            
            # Create the agent
            self.agent = initialize_agent(
                tools,
                chat,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True
            )
            
            self.logger.info(f"AI-Showmaker Agent initialized with {len(tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Agent initialization failed: {str(e)}")
            raise AIShowmakerError(f"Agent initialization failed: {str(e)}")
    
    def _enhance_query_for_todos(self, query: str) -> str:
        """Enhance query to trigger todo usage for multi-step tasks."""
        # Keywords that indicate multi-step tasks
        multi_step_keywords = [
            'build', 'create', 'develop', 'implement', 'deploy', 'setup', 'install',
            'configure', 'test', 'write', 'make', 'design', 'plan', 'execute'
        ]
        
        # Check if query contains multi-step indicators
        query_lower = query.lower()
        has_multi_step = any(keyword in query_lower for keyword in multi_step_keywords)
        
        # Check for explicit step indicators
        has_steps = any(indicator in query_lower for indicator in ['step', 'then', 'and', 'after', '1)', '2)', '3)'])
        
        # If likely multi-step, add explicit todo instruction
        if has_multi_step or has_steps:
            return f"{query}\n\nIMPORTANT: Since this is a multi-step task, start by creating a todo list to track your progress."
        
        return query
    
    def run(self, query: str) -> str:
        """Execute a query using the agent."""
        if not self.agent:
            raise AIShowmakerError("Agent not initialized. Call initialize() first.")
        
        try:
            self.stats['total_queries'] += 1
            
            # Enhance query to encourage todo usage
            enhanced_query = self._enhance_query_for_todos(query)
            
            result = self.agent.run(enhanced_query)
            
            self.stats['successful_queries'] += 1
            self.logger.info(f"Query executed successfully: {query[:50]}...")
            
            return result
            
        except Exception as e:
            self.stats['failed_queries'] += 1
            self.logger.error(f"Query execution failed: {str(e)}")
            return f"Query execution failed: {str(e)}"
    
    def human_in_the_loop(self, task_description: str, max_retries: int = 3) -> Optional[str]:
        """Execute task with human-in-the-loop confirmation."""
        current_task = task_description
        
        for attempt in range(max_retries):
            try:
                response = self.run(current_task)
                print(f"\n--- Agent Response ---")
                print(response)
                print(f"--- End Response ---\n")
                
                confirm = input("Is the task completed successfully? (y/n/q for quit): ").strip().lower()
                if confirm == "q":
                    print("Task aborted by user.")
                    return None
                elif confirm == "y":
                    print("✅ Task confirmed!")
                    return response
                else:
                    feedback = input("What should be improved for the next attempt? ")
                    current_task = (
                        f"Previous task: {task_description}\n"
                        f"Previous attempt: {response}\n"
                        f"User feedback: {feedback}\n"
                        f"Please try again with improvements."
                    )
            
            except KeyboardInterrupt:
                print("\nTask interrupted by user.")
                return None
            except Exception as e:
                print(f"Error during attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return f"Max retries reached. Last error: {str(e)}"
        
        return "Max retries reached."
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent usage statistics."""
        uptime = datetime.now() - self.stats['start_time']
        server_info = asyncio.run(self._get_server_stats())
        
        return {
            'agent_stats': self.stats.copy(),
            'uptime_seconds': uptime.total_seconds(),
            'server_info': server_info
        }
    
    async def _get_server_stats(self) -> Dict[str, Any]:
        """Get statistics from all servers."""
        return self.server_manager.get_server_info()
    
    async def shutdown(self) -> None:
        """Shutdown the agent and all servers."""
        await self.server_manager.shutdown()
        self.logger.info("AI-Showmaker Agent shutdown complete")