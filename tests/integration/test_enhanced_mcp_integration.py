#!/usr/bin/env python3
"""
Integration tests for Enhanced MCP Integration

Tests the enhanced integration between LlamaIndex and MCP servers.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.enhanced_mcp_agent import EnhancedAIShowmakerAgent, MCPToolWrapper, MCPToolMetadata
from core.config import ConfigManager


class TestEnhancedMCPIntegration:
    """Test suite for enhanced MCP integration."""
    
    @pytest.fixture
    async def agent(self):
        """Create an enhanced agent for testing."""
        config = ConfigManager()
        agent = EnhancedAIShowmakerAgent(config)
        await agent.initialize()
        yield agent
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the enhanced agent initializes correctly."""
        assert agent is not None
        assert agent.agent is not None
        assert len(agent.agent.mcp_tools) > 0
        assert len(agent.agent.llama_tools) > 0
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, agent):
        """Test that MCP tools are properly registered."""
        tools_info = agent.get_tools_info()
        assert len(tools_info) > 0
        
        # Check that tools have enhanced metadata
        for tool in tools_info:
            assert 'name' in tool
            assert 'description' in tool
            assert 'server' in tool
            assert 'category' in tool
            assert 'version' in tool
            assert 'parameters' in tool
    
    @pytest.mark.asyncio
    async def test_calculation_tool(self, agent):
        """Test mathematical calculation tool."""
        result = await agent.query("Calculate 5 + 3")
        assert result is not None
        assert "8" in result or "5 + 3 = 8" in result
    
    @pytest.mark.asyncio
    async def test_todo_creation(self, agent):
        """Test todo creation tool."""
        result = await agent.query("Create todos for: test feature, deploy app")
        assert result is not None
        assert "todo" in result.lower() or "created" in result.lower()
    
    @pytest.mark.asyncio
    async def test_system_info(self, agent):
        """Test system information tool."""
        result = await agent.query("Get system information")
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_statistics(self, agent):
        """Test that statistics are properly tracked."""
        # Make a few queries
        await agent.query("Calculate 2 + 2")
        await agent.query("Create a todo for testing")
        
        stats = agent.get_statistics()
        assert stats['agent_stats']['total_queries'] >= 2
        assert stats['agent_stats']['total_tool_calls'] >= 2
        assert stats['tool_count'] > 0
        assert stats['server_count'] > 0
    
    @pytest.mark.asyncio
    async def test_server_statistics(self, agent):
        """Test server statistics."""
        server_stats = await agent._get_server_stats()
        assert len(server_stats) > 0
        
        for server_name, stats in server_stats.items():
            if 'error' not in stats:
                assert 'tool_count' in stats
                assert 'statistics' in stats
                assert stats['tool_count'] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling for invalid queries."""
        result = await agent.query("Execute invalid tool with bad parameters")
        assert result is not None
        # Should handle error gracefully
        assert "error" in result.lower() or "failed" in result.lower()
    
    @pytest.mark.asyncio
    async def test_mcp_tool_wrapper(self, agent):
        """Test MCPToolWrapper functionality."""
        # Get a tool wrapper
        tool_name = list(agent.agent.mcp_tools.keys())[0]
        wrapper = agent.agent.mcp_tools[tool_name]
        
        assert isinstance(wrapper, MCPToolWrapper)
        assert isinstance(wrapper.metadata, MCPToolMetadata)
        assert wrapper.metadata.name is not None
        assert wrapper.metadata.description is not None
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, agent):
        """Test parameter validation."""
        # This should fail due to missing required parameters
        result = await agent.query("Calculate")  # Missing expression
        assert result is not None
        # Should handle missing parameters gracefully
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, agent):
        """Test that conversation memory persists."""
        # First query
        result1 = await agent.query("Calculate 5 + 3")
        
        # Second query that references the first
        result2 = await agent.query("What was the result of the previous calculation?")
        
        assert result1 is not None
        assert result2 is not None
        # The agent should be able to reference previous calculations
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self, agent):
        """Test handling of concurrent queries."""
        queries = [
            "Calculate 1 + 1",
            "Calculate 2 + 2", 
            "Calculate 3 + 3"
        ]
        
        # Execute queries concurrently
        tasks = [agent.query(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result) > 0


class TestMCPToolWrapper:
    """Test suite for MCPToolWrapper class."""
    
    def test_metadata_creation(self):
        """Test MCPToolMetadata creation."""
        metadata = MCPToolMetadata(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            server_name="test_server",
            category="test",
            version="1.0.0",
            timeout=30,
            requires_auth=False
        )
        
        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.server_name == "test_server"
        assert metadata.category == "test"
        assert metadata.version == "1.0.0"
        assert metadata.timeout == 30
        assert metadata.requires_auth is False


class TestEnhancedAgentFeatures:
    """Test suite for enhanced agent features."""
    
    @pytest.fixture
    async def agent(self):
        """Create an enhanced agent for testing."""
        config = ConfigManager()
        agent = EnhancedAIShowmakerAgent(config)
        await agent.initialize()
        yield agent
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_enhanced_system_prompt(self, agent):
        """Test that enhanced system prompts include detailed tool information."""
        # The system prompt should include detailed tool information
        # This is tested indirectly through tool execution
        result = await agent.query("What tools are available?")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_function_call_parsing(self, agent):
        """Test enhanced function call parsing."""
        # Test with a simple calculation that should trigger function calling
        result = await agent.query("Calculate the factorial of 5")
        assert result is not None
        
        # Check that tool calls were made
        stats = agent.get_statistics()
        assert stats['agent_stats']['total_tool_calls'] > 0
    
    @pytest.mark.asyncio
    async def test_tool_result_formatting(self, agent):
        """Test tool result formatting."""
        result = await agent.query("Calculate 10 * 10")
        assert result is not None
        assert "100" in result
    
    @pytest.mark.asyncio
    async def test_async_execution(self, agent):
        """Test async execution capabilities."""
        # Test that async execution works properly
        result = await agent.query("Calculate 2^10")
        assert result is not None
        assert "1024" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
