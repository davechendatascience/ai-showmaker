"""
MCP Server Discovery System

This module provides dynamic discovery and loading of MCP servers from local directories.
It integrates seamlessly with the existing AI-Showmaker MCP infrastructure.
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mcp_servers.base.server import AIShowmakerMCPServer
from .plugin_validator import PluginValidator
from .capability_discovery import CapabilityDiscoveryEngine, CapabilityExtractor, ToolCategory


class PluginDiscoveryEvent(FileSystemEventHandler):
    """File system event handler for plugin discovery."""
    
    def __init__(self, discovery_manager: 'MCPServerDiscovery'):
        self.discovery_manager = discovery_manager
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            asyncio.create_task(self.discovery_manager.discover_servers())
            
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            asyncio.create_task(self.discovery_manager.discover_servers())
            
    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            asyncio.create_task(self.discovery_manager.discover_servers())


class MCPServerDiscovery:
    """
    Discovers and loads MCP servers dynamically from local directories.
    
    This class integrates with the existing AI-Showmaker MCP infrastructure
    to provide seamless plugin discovery and loading.
    """
    
    def __init__(self, discovery_paths: List[str] = None):
        self.discovery_paths = discovery_paths or ['examples/plugins', 'plugins']
        self.logger = logging.getLogger("mcp_zero.discovery")
        self.discovered_servers: Dict[str, AIShowmakerMCPServer] = {}
        self.server_classes: Dict[str, Type[AIShowmakerMCPServer]] = {}
        self.observer = None
        self.watching = False
        self.validator = PluginValidator()
        
        # Capability-based discovery engine
        self.capability_engine = CapabilityDiscoveryEngine()
        
    async def start_watching(self) -> None:
        """Start watching discovery paths for changes."""
        if self.watching:
            return
            
        try:
            self.observer = Observer()
            event_handler = PluginDiscoveryEvent(self)
            
            for path in self.discovery_paths:
                if os.path.exists(path):
                    self.observer.schedule(event_handler, path, recursive=True)
                    self.logger.info(f"Watching for plugins in: {path}")
                else:
                    # Create directory if it doesn't exist
                    os.makedirs(path, exist_ok=True)
                    self.logger.info(f"Created plugin directory: {path}")
            
            self.observer.start()
            self.watching = True
            self.logger.info("Plugin discovery watching started")
            
        except Exception as e:
            self.logger.error(f"Failed to start plugin watching: {e}")
            
    async def stop_watching(self) -> None:
        """Stop watching for plugin changes."""
        if self.observer and self.watching:
            self.observer.stop()
            self.observer.join()
            self.watching = False
            self.logger.info("Plugin discovery watching stopped")
            
    async def discover_servers(self) -> Dict[str, AIShowmakerMCPServer]:
        """
        Discover and load MCP servers from discovery paths.
        
        Returns:
            Dict of server names to server instances
        """
        self.logger.info("Starting MCP server discovery...")
        
        for discovery_path in self.discovery_paths:
            if not os.path.exists(discovery_path):
                continue
                
            await self._scan_directory(discovery_path)
            
        self.logger.info(f"Discovery complete. Found {len(self.discovered_servers)} servers")
        return self.discovered_servers
        
    async def _scan_directory(self, directory_path: str) -> None:
        """Scan a directory for MCP server plugins."""
        try:
            for file_path in Path(directory_path).glob("*.py"):
                if file_path.name.startswith('__'):
                    continue
                    
                await self._load_server_from_file(file_path)
                
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory_path}: {e}")
            
    async def _load_server_from_file(self, file_path: Path) -> None:
        """Load an MCP server from a Python file."""
        try:
            # 1. SECURITY: Validate plugin before loading
            is_valid, validation_errors = await self.validator.validate_plugin(file_path)
            
            if not is_valid:
                self.logger.warning(f"Plugin {file_path.name} failed validation: {validation_errors}")
                return
                
            self.logger.info(f"Plugin {file_path.name} passed security validation")
            
            # 2. Load the module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{file_path.stem}", 
                file_path
            )
            
            if not spec or not spec.loader:
                self.logger.warning(f"Could not load spec for {file_path}")
                return
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 3. Look for MCP server classes
            server_classes = self._find_server_classes(module)
            
            for server_class in server_classes:
                await self._instantiate_server(server_class, file_path)
                
        except Exception as e:
            self.logger.error(f"Error loading server from {file_path}: {e}")
            
    def _find_server_classes(self, module) -> List[Type[AIShowmakerMCPServer]]:
        """Find MCP server classes in a module."""
        server_classes = []
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a class that inherits from AIShowmakerMCPServer
            if (isinstance(attr, type) and 
                issubclass(attr, AIShowmakerMCPServer) and 
                attr != AIShowmakerMCPServer):
                server_classes.append(attr)
                
        return server_classes
        
    async def _instantiate_server(self, server_class: Type[AIShowmakerMCPServer], 
                                 file_path: Path) -> None:
        """Instantiate and register an MCP server."""
        try:
            # Create server instance
            server = server_class()
            
            # Initialize the server
            if hasattr(server, 'initialize'):
                await server.initialize()
                
            # Register the server
            server_name = server.name
            self.discovered_servers[server_name] = server
            self.server_classes[server_name] = server_class
            
            self.logger.info(f"Loaded MCP server: {server_name} from {file_path}")
            self.logger.info(f"Server {server_name} has {len(server.tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Error instantiating server {server_class.__name__}: {e}")
            
    async def get_server(self, server_name: str) -> Optional[AIShowmakerMCPServer]:
        """Get a discovered server by name."""
        return self.discovered_servers.get(server_name)
        
    async def get_all_servers(self) -> Dict[str, AIShowmakerMCPServer]:
        """Get all discovered servers."""
        return self.discovered_servers.copy()
        
    async def reload_server(self, server_name: str) -> bool:
        """Reload a specific server."""
        if server_name not in self.server_classes:
            return False
            
        try:
            # Remove old instance
            if server_name in self.discovered_servers:
                old_server = self.discovered_servers[server_name]
                if hasattr(old_server, 'shutdown'):
                    await old_server.shutdown()
                del self.discovered_servers[server_name]
                
            # Reload the server class
            server_class = self.server_classes[server_name]
            await self._instantiate_server(server_class, Path(""))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading server {server_name}: {e}")
            return False
            
    async def shutdown_all(self) -> None:
        """Shutdown all discovered servers."""
        for server_name, server in self.discovered_servers.items():
            try:
                if hasattr(server, 'shutdown'):
                    await server.shutdown()
                self.logger.info(f"Shutdown plugin server: {server_name}")
            except Exception as e:
                self.logger.error(f"Error shutting down {server_name}: {e}")
                
        self.discovered_servers.clear()
        self.server_classes.clear()
        
    def get_discovery_info(self) -> Dict[str, Any]:
        """Get information about the discovery system."""
        return {
            'discovery_paths': self.discovery_paths,
            'watching': self.watching,
            'discovered_servers': list(self.discovered_servers.keys()),
            'total_tools': sum(len(s.tools) for s in self.discovered_servers.values()),
            'validation_info': self.validator.get_validation_info()
        }
    
    # ===== CAPABILITY-BASED DISCOVERY METHODS =====
    
    async def discover_tools_by_capability(self, query: str) -> List[tuple]:
        """
        Find tools by capability using natural language query.
        
        Args:
            query: Natural language description of what the agent needs
            
        Returns:
            List of (tool_name, relevance_score) tuples
        """
        return self.capability_engine.discover_by_capability(query)
    
    async def discover_tools_by_category(self, category: str) -> List[str]:
        """
        Find tools by category.
        
        Args:
            category: Category name (e.g., "mathematics", "statistics")
            
        Returns:
            List of tool names in that category
        """
        try:
            tool_category = ToolCategory(category)
            return self.capability_engine.discover_by_category(tool_category)
        except ValueError:
            self.logger.warning(f"Unknown category: {category}")
            return []
    
    async def discover_tools_by_tags(self, tags: List[str]) -> List[str]:
        """
        Find tools that have any of the specified tags.
        
        Args:
            tags: List of tags to search for
            
        Returns:
            List of tool names matching the tags
        """
        return self.capability_engine.discover_by_tags(tags)
    
    async def get_tool_suggestions(self, context: str) -> List[str]:
        """
        Get intelligent tool suggestions based on context.
        
        Args:
            context: Description of what the agent is trying to accomplish
            
        Returns:
            List of suggested tool names
        """
        return self.capability_engine.get_tool_suggestions(context)
    
    async def get_capability_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all available tool capabilities.
        
        Returns:
            Dictionary with capability statistics
        """
        return self.capability_engine.get_capability_summary()
    
    def _register_tool_capabilities(self, server: AIShowmakerMCPServer) -> None:
        """
        Register all tools from a server with the capability engine.
        
        Args:
            server: MCP server instance
        """
        for tool_name, tool in server.tools.items():
            try:
                # Extract tool metadata
                tool_data = {
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "category": getattr(tool, 'category', 'utilities')
                }
                
                # Create capability object
                capability = CapabilityExtractor.extract_from_tool(tool_name, tool_data)
                
                # Register with capability engine
                self.capability_engine.register_tool_capability(tool_name, capability)
                
                self.logger.debug(f"Registered capabilities for tool: {tool_name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to register capabilities for tool {tool_name}: {e}")
    
    async def _instantiate_server(self, server_class: Type[AIShowmakerMCPServer], 
                                 file_path: Path) -> None:
        """Instantiate and register an MCP server."""
        try:
            # Create server instance
            server = server_class()
            
            # Initialize the server
            if hasattr(server, 'initialize'):
                await server.initialize()
                
            # Register the server
            server_name = server.name
            self.discovered_servers[server_name] = server
            self.server_classes[server_name] = server_class
            
            # Register tool capabilities for discovery
            self._register_tool_capabilities(server)
            
            self.logger.info(f"Loaded MCP server: {server_name} from {file_path}")
            self.logger.info(f"Server {server_name} has {len(server.tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Error instantiating server {server_class.__name__}: {e}")
