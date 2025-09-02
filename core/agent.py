#!/usr/bin/env python3
"""
Unified AI Showmaker Agent using llama-index-tools-mcp for MCP tool integration.

This implementation leverages the official llama-index-tools-mcp package for:
- Seamless MCP tool discovery and integration
- Automatic tool schema conversion to FunctionTool objects
- Native LlamaIndex agent workflows
- Better error handling and validation
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path


from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool

from core.config import ConfigManager
from core.custom_llm import InferenceNetLLM
from core.local_llm import OllamaLLM, LlamaCppLLM
from core.mcp_zero.server_discovery import MCPServerDiscovery
from core.utils.task_planner import IntelligentTaskPlanner, TaskPlan


class MCPIntegratedAgent:
    """
    AI Showmaker Agent with native MCP tool integration using llama-index-tools-mcp.
    
    This agent automatically discovers MCP servers, converts their tools to LlamaIndex
    FunctionTool objects, and provides a clean interface for task execution.
    """
    
    # Define SimpleCustomAgent class at class level
    class SimpleCustomAgent:
        def __init__(self, llm, tools, system_prompt):
            self.llm = llm
            self.tools = tools
            self.system_prompt = system_prompt
            self.logger = logging.getLogger(__name__)
        
        async def run(self, query: str):
            # Simple agent that directly uses the LLM
            full_prompt = f"{self.system_prompt}\n\nUser Query: {query}\n\nAvailable Tools: {', '.join([tool.metadata.name for tool in self.tools])}\n\nPlease provide a helpful response using the available tools if needed."
            
            try:
                # Use the LLM's complete method
                if hasattr(self.llm, 'complete'):
                    response = self.llm.complete(full_prompt)
                    return response
                else:
                    return "LLM not properly configured"
            except Exception as e:
                self.logger.error(f"LLM execution failed: {e}")
                return f"Error: {str(e)}"
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MCP server discovery
        self.server_discovery = MCPServerDiscovery()
        
        # LLM instances
        self.inference_llm: Optional[InferenceNetLLM] = None
        self.ollama_llm: Optional[OllamaLLM] = None
        self.llama_cpp_llm: Optional[LlamaCppLLM] = None
        
        # Local MCP servers and tools
        self.local_servers: Dict[str, Any] = {}
        self.mcp_tools: List[BaseTool] = []
        
        # LlamaIndex agent
        self.agent: Optional[FunctionAgent] = None
        
        # Task planner
        self.task_planner = IntelligentTaskPlanner()
        
        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize the agent synchronously
        self._initialize_sync()
        
    async def initialize(self) -> None:
        """Initialize the agent with MCP servers and tools."""
        self.logger.info("Initializing MCP Integrated Agent...")
        
        # Initialize LLMs
        await self._initialize_llms()
        
        # Discover and connect to MCP servers
        await self._discover_mcp_servers()
        
        # Convert MCP tools to LlamaIndex tools
        await self._setup_mcp_tools()
        
        # Create LlamaIndex agent
        await self._create_agent()
        
        self.logger.info(f"Agent initialized with {len(self.mcp_tools)} MCP tools")
    
    def _initialize_sync(self) -> None:
        """Synchronous initialization wrapper."""
        import asyncio
        try:
            asyncio.run(self.initialize())
        except RuntimeError:
            # If there's already an event loop running, we can't use asyncio.run
            # In this case, we'll need to call initialize() manually later
            self.logger.warning("Event loop already running, manual initialization required")
    
    async def _initialize_llms(self) -> None:
        """Initialize available LLM instances."""
        try:
            # Debug: Check config values
            api_key = self.config.get('inference_net_key')
            base_url = self.config.get('inference_net_base_url', 'https://api.inference.net')
            model = self.config.get('inference_net_model', 'mistral-7b-instruct')
            
            self.logger.info(f"Config values - API Key: {'***' if api_key else 'None'}, Base URL: {base_url}, Model: {model}")
            
            # Initialize Inference.net LLM using CustomLLM
            if api_key:
                from llama_index.core.llms import CustomLLM
                
                class InferenceNetCustomLLM(CustomLLM):
                    api_key: str
                    base_url: str
                    model: str
                    
                    def __init__(self, api_key: str, base_url: str, model: str):
                        super().__init__(api_key=api_key, base_url=base_url, model=model)
                        self._inference_llm = InferenceNetLLM(api_key=api_key, base_url=base_url, model=model)
                    
                    @property
                    def metadata(self):
                        from llama_index.core.llms import LLMMetadata
                        return LLMMetadata(
                            model_name=self.model,
                            is_chat_model=True,
                            is_function_calling_model=True
                        )
                    
                    def complete(self, prompt: str, **kwargs):
                        response = self._inference_llm.complete(prompt)
                        return response
                    
                    def stream_complete(self, prompt: str, **kwargs):
                        response = self._inference_llm.complete(prompt)
                        yield response
                    
                    async def achat(self, messages, **kwargs):
                        # Convert messages to a single prompt for the inference LLM
                        prompt = "\n".join([msg.content for msg in messages])
                        response = self._inference_llm.complete(prompt)
                        return response
                    
                    async def astream_chat_with_tools(
                        self,
                        tools: list,
                        chat_history: Optional[list] = None,
                        **kwargs
                    ):
                        # Convert chat history to a single prompt for the inference LLM
                        if chat_history:
                            prompt = "\n".join([msg.content for msg in chat_history])
                        else:
                            prompt = "Please provide a query."
                        
                        response = self._inference_llm.complete(prompt)
                        # Return as an async generator as expected by LlamaIndex
                        yield response
                
                self.inference_llm = InferenceNetCustomLLM(api_key=api_key, base_url=base_url, model=model)
                self.logger.info("Inference.net LLM initialized with CustomLLM wrapper")
            else:
                self.logger.warning("No inference_net_key found in config")
            
            # Initialize Ollama LLM (if available) - skip for now
            self.ollama_llm = None
            
            # Initialize LlamaCpp LLM (if available) - skip for now
            self.llama_cpp_llm = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLMs: {e}")
            raise
    
    async def _discover_mcp_servers(self) -> None:
        """Discover MCP servers and store them for tool conversion."""
        try:
            # Discover MCP servers
            servers = await self.server_discovery.discover_servers()
            self.logger.info(f"Discovered {len(servers)} MCP servers")
            
            # Store the servers for tool conversion
            self.local_servers = servers
            
        except Exception as e:
            self.logger.error(f"Failed to discover MCP servers: {e}")
            raise
    
    async def _setup_mcp_tools(self) -> None:
        """Convert local MCP tools to LlamaIndex FunctionTool objects."""
        try:
            from llama_index.core.tools import FunctionTool
            
            for server_name, server in self.local_servers.items():
                try:
                    # Convert each tool from the local server to a LlamaIndex FunctionTool
                    for tool_name, mcp_tool in server.tools.items():
                        # Create a wrapper function that calls the MCP tool
                        def tool_wrapper(**kwargs):
                            try:
                                # Execute the MCP tool (synchronous for now)
                                result = mcp_tool.execute_func(**kwargs)
                                return str(result)
                            except Exception as e:
                                return f"Tool execution failed: {str(e)}"
                        
                        # Create LlamaIndex FunctionTool
                        llama_tool = FunctionTool.from_defaults(
                            fn=tool_wrapper,
                            name=f"{server_name}_{tool_name}",
                            description=mcp_tool.description
                        )
                        
                        self.mcp_tools.append(llama_tool)
                    
                    self.logger.info(f"Added {len(server.tools)} tools from {server_name}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert tools from {server_name}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to setup MCP tools: {e}")
            raise
    
    async def _create_agent(self) -> None:
        """Create the LlamaIndex FunctionAgent with MCP tools."""
        try:
            # Select the primary LLM (prefer Inference.net, fallback to others)
            primary_llm = self._get_primary_llm()
            if not primary_llm:
                raise Exception("No LLM available")
            
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create a simple custom agent that directly uses LLM and tools
            self.agent = self.SimpleCustomAgent(
                llm=primary_llm,
                tools=self.mcp_tools,
                system_prompt=system_prompt
            )
            
            self.logger.info("Simple Custom Agent created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create agent: {e}")
            raise
    
    def _get_primary_llm(self) -> Optional[LLM]:
        """Get the primary LLM instance."""
        # Prefer Inference.net, then Ollama, then LlamaCpp
        if self.inference_llm:
            return self.inference_llm
        elif self.ollama_llm:
            return self.ollama_llm
        elif self.llama_cpp_llm:
            return self.llama_cpp_llm
        return None
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return f"""You are an AI Showmaker Agent with access to {len(self.mcp_tools)} MCP tools.

Your capabilities include:
- Web search and information gathering
- Remote server operations and development
- Mathematical calculations and advanced math
- File operations and monitoring
- Development workflows and automation

IMPORTANT RULES:
1. Always use the exact tool names as provided - never add asterisks (*) or other formatting
2. For complex tasks, break them down into logical steps
3. Use web search when you need to gather information
4. For development tasks, execute actual remote operations, don't just provide instructions
5. Validate results and provide clear feedback

Available tools: {', '.join([tool.metadata.name for tool in self.mcp_tools])}

When given a task, analyze it carefully and use the appropriate tools to complete it step by step."""
    
    async def query(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Execute a query using the agent.
        
        Args:
            query: The user's query or task description
            session_id: Optional session ID for tracking
            
        Returns:
            The agent's response
        """
        if not self.agent:
            raise Exception("Agent not initialized")
        
        try:
            # Create session if needed
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Store session info
            self.active_sessions[session_id] = {
                'query': query,
                'start_time': time.time(),
                'status': 'running'
            }
            
            self.logger.info(f"Executing query: {query[:100]}...")
            
            # Execute query using our simple custom agent
            try:
                # Use our simple agent's run method
                response = await self.agent.run(query)
                self.logger.info("Simple agent run succeeded")
                
                # Extract the response content
                response_text = str(response)
                
                # Update session status
                self.active_sessions[session_id]['status'] = 'completed'
                self.active_sessions[session_id]['response'] = response_text
                
                return response_text
                
            except Exception as e:
                self.logger.error(f"Agent execution failed: {e}")
                raise
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            
            # Update session status
            if session_id and session_id in self.active_sessions:
                self.active_sessions[session_id]['status'] = 'failed'
                self.active_sessions[session_id]['error'] = str(e)
            
            raise
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific session."""
        return self.active_sessions.get(session_id)
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions."""
        return list(self.active_sessions.values())
    
    async def shutdown(self) -> None:
        """Shutdown the agent and clean up resources."""
        self.logger.info("Shutting down MCP Integrated Agent...")
        
        # Clean up local servers if needed
        if hasattr(self, 'local_servers'):
            for server_name, server in self.local_servers.items():
                try:
                    if hasattr(server, 'shutdown'):
                        await server.shutdown()
                except Exception as e:
                    self.logger.warning(f"Failed to shutdown server {server_name}: {e}")
        
        self.logger.info("Agent shutdown complete")
    
    @property
    def available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [tool.metadata.name for tool in self.mcp_tools]
    
    @property
    def tool_count(self) -> int:
        """Get the total number of available tools."""
        return len(self.mcp_tools)
