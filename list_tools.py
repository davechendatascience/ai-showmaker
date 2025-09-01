#!/usr/bin/env python3
"""
List all available MCP tools in the AI-Showmaker project
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from mcp_servers.calculation.server import CalculationMCPServer
from mcp_servers.remote.server import RemoteMCPServer
from mcp_servers.development.server import ReadOnlyDevelopmentMCPServer, DevelopmentMCPServer
from mcp_servers.monitoring.server import MonitoringMCPServer
from mcp_servers.websearch.server import WebSearchMCPServer


async def list_all_tools():
    """List all available MCP tools."""
    
    # Initialize all servers
    servers = {
        "calculation": CalculationMCPServer(),
        "remote": RemoteMCPServer(),
        "development": ReadOnlyDevelopmentMCPServer(),  # Safe read-only version
        "monitoring": MonitoringMCPServer(),
        "websearch": WebSearchMCPServer()
    }
    
    print("🔧 AI-Showmaker MCP Tools Inventory")
    print("=" * 50)
    
    total_tools = 0
    
    for server_name, server in servers.items():
        await server.initialize()
        
        print(f"\n📦 {server_name.upper()} SERVER ({len(server.tools)} tools)")
        print("-" * 40)
        
        for tool_name, tool in server.tools.items():
            total_tools += 1
            print(f"  • {tool_name}")
            print(f"    Description: {tool.description}")
            print(f"    Category: {tool.category}")
            print(f"    Timeout: {tool.timeout}s")
            print()
    
    print(f"\n📊 SUMMARY")
    print("-" * 20)
    print(f"Total Servers: {len(servers)}")
    print(f"Total Tools: {total_tools}")
    
    # Shutdown servers
    for server in servers.values():
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(list_all_tools())
