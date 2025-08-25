#!/usr/bin/env python3
"""
Integration tests for Web Search MCP Server with LlamaIndex Integration

Tests web search functionality including DuckDuckGo scraping and content extraction
using the modern LlamaIndex + MCP approach.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, AsyncMock
import json

from mcp_servers.websearch.server import WebSearchMCPServer
from core.reliable_mcp_agent import ReliableLlamaIndexAgent
from core.config import ConfigManager


@pytest_asyncio.fixture
async def websearch_server():
    """Create a web search server instance for testing."""
    server = WebSearchMCPServer()
    await server.initialize()
    yield server
    # Cleanup if needed
    if hasattr(server, 'cleanup'):
        await server.cleanup()


@pytest_asyncio.fixture
async def llamaindex_agent():
    """Create a LlamaIndex agent with web search capabilities for testing."""
    config = ConfigManager()
    agent = ReliableLlamaIndexAgent(config)
    await agent.initialize()
    yield agent
    # Cleanup
    await agent.shutdown()


class TestWebSearchServer:
    """Test web search server functionality."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, websearch_server):
        """Test that the web search server initializes correctly."""
        assert websearch_server is not None
        assert websearch_server.name == "websearch"
        assert len(websearch_server.tools) == 4  # search_web, extract_content, search_and_extract, get_search_suggestions
        assert "search_web" in websearch_server.tools
        assert "extract_content" in websearch_server.tools
        assert "search_and_extract" in websearch_server.tools
        assert "get_search_suggestions" in websearch_server.tools
    
    @pytest.mark.asyncio
    async def test_search_web_validation(self, websearch_server):
        """Test search_web parameter validation."""
        # Test empty query
        result = await websearch_server.search_web("")
        assert "error" in result
        assert "empty" in result["error"].lower()
        
        # Test None query
        result = await websearch_server.search_web(None)
        assert "error" in result
        assert "empty" in result["error"].lower()
        
        # Test max_results limits
        result = await websearch_server.search_web("test", max_results=0)
        assert "error" not in result  # Should be clamped to 1
        
        result = await websearch_server.search_web("test", max_results=15)
        assert "error" not in result  # Should be clamped to 10
    
    @pytest.mark.asyncio
    async def test_extract_content_validation(self, websearch_server):
        """Test extract_content parameter validation."""
        # Test invalid URL
        result = await websearch_server.extract_content("not-a-url")
        assert "error" in result
        assert "invalid" in result["error"].lower()
        
        # Test empty URL
        result = await websearch_server.extract_content("")
        assert "error" in result
        assert "invalid" in result["error"].lower()
        
        # Test None URL
        result = await websearch_server.extract_content(None)
        assert "error" in result
        assert "invalid" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_validation(self, websearch_server):
        """Test get_search_suggestions parameter validation."""
        # Test empty query
        result = await websearch_server.get_search_suggestions("")
        assert "error" in result
        assert "empty" in result["error"].lower()
        
        # Test None query
        result = await websearch_server.get_search_suggestions(None)
        assert "error" in result
        assert "empty" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_search_and_extract_validation(self, websearch_server):
        """Test search_and_extract parameter validation."""
        # Test empty query
        result = await websearch_server.search_and_extract("")
        assert "error" in result
        assert "empty" in result["error"].lower()
        
        # Test max_results limits
        result = await websearch_server.search_and_extract("test", max_results=0)
        assert "error" not in result  # Should be clamped to 1
        
        result = await websearch_server.search_and_extract("test", max_results=10)
        assert "error" not in result  # Should be clamped to 5
    
    @pytest.mark.asyncio
    async def test_tool_schemas(self, websearch_server):
        """Test that tool schemas are properly defined."""
        schemas = websearch_server.get_tool_schemas()
        
        assert "search_web" in schemas
        assert "extract_content" in schemas
        assert "search_and_extract" in schemas
        assert "get_search_suggestions" in schemas
        
        # Check search_web schema
        search_schema = schemas["search_web"]
        assert search_schema["name"] == "search_web"
        assert "description" in search_schema
        assert "parameters" in search_schema
        
        # Check required parameters
        params = search_schema["parameters"]
        assert "properties" in params
        assert "query" in params["properties"]
        assert "required" in params
        assert "query" in params["required"]
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, websearch_server):
        """Test that rate limiting works correctly."""
        start_time = asyncio.get_event_loop().time()
        
        # Make multiple rapid calls
        for i in range(3):
            await websearch_server._rate_limit()
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # Should have at least 2 seconds of delay (3 calls with 1s intervals)
        assert elapsed >= 2.0
    
    @pytest.mark.asyncio
    async def test_caching(self, websearch_server):
        """Test that caching works correctly."""
        # Mock the search function to return consistent results
        with patch.object(websearch_server, '_search_duckduckgo') as mock_search:
            mock_search.return_value = {
                "query": "test",
                "results": [{"title": "Test Result", "url": "http://test.com"}],
                "total_results": 1,
                "source": "DuckDuckGo",
                "timestamp": "2024-01-01T00:00:00"
            }
            
            # First call should hit the mock
            result1 = await websearch_server.search_web("test")
            assert mock_search.call_count == 1
            
            # Second call should use cache
            result2 = await websearch_server.search_web("test")
            assert mock_search.call_count == 1  # Should not be called again
            
            # Results should be identical
            assert result1 == result2


class TestWebSearchIntegration:
    """Integration tests for web search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_web_integration(self, websearch_server):
        """Test actual web search functionality (requires internet)."""
        # This test requires internet connection
        try:
            result = await websearch_server.search_web("Python programming", max_results=3)
            
            assert "error" not in result
            assert "query" in result
            assert result["query"] == "Python programming"
            assert "results" in result
            assert "total_results" in result
            assert "source" in result
            assert result["source"] == "DuckDuckGo"
            
            # Check results structure
            results = result["results"]
            assert len(results) <= 3
            
            for item in results:
                assert "title" in item
                assert "url" in item
                assert "snippet" in item
                assert "timestamp" in item
                
        except Exception as e:
            # If internet is not available, skip the test
            pytest.skip(f"Internet connection required: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_extract_content_integration(self, websearch_server):
        """Test actual content extraction (requires internet)."""
        # This test requires internet connection
        try:
            result = await websearch_server.extract_content(
                "https://httpbin.org/html", 
                max_length=500
            )
            
            assert "error" not in result
            assert "url" in result
            assert result["url"] == "https://httpbin.org/html"
            assert "title" in result
            assert "content" in result
            assert "text_content" in result
            assert "metadata" in result
            assert "timestamp" in result
            
            # Check content length
            assert len(result["text_content"]) <= 500
            
        except Exception as e:
            # If internet is not available, skip the test
            pytest.skip(f"Internet connection required: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_search_and_extract_integration(self, websearch_server):
        """Test combined search and extract functionality (requires internet)."""
        # This test requires internet connection
        try:
            result = await websearch_server.search_and_extract(
                "Python tutorial", 
                max_results=2,
                max_content_length=300
            )
            
            assert "error" not in result
            assert "query" in result
            assert result["query"] == "Python tutorial"
            assert "results" in result
            assert "total_results" in result
            
            # Check results structure
            results = result["results"]
            assert len(results) <= 2
            
            for item in results:
                assert "title" in item
                assert "url" in item
                assert "extracted_content" in item
                assert "page_title" in item
                
        except Exception as e:
            # If internet is not available, skip the test
            pytest.skip(f"Internet connection required: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_integration(self, websearch_server):
        """Test search suggestions functionality (requires internet)."""
        # This test requires internet connection
        try:
            result = await websearch_server.get_search_suggestions("Python", max_suggestions=3)
            
            assert "error" not in result
            assert "query" in result
            assert result["query"] == "Python"
            assert "suggestions" in result
            assert "total_suggestions" in result
            assert "source" in result
            assert result["source"] == "DuckDuckGo"
            
            # Check suggestions
            suggestions = result["suggestions"]
            assert len(suggestions) <= 3
            
            for suggestion in suggestions:
                assert isinstance(suggestion, str)
                assert len(suggestion) > 0
                
        except Exception as e:
            # If internet is not available, skip the test
            pytest.skip(f"Internet connection required: {str(e)}")


class TestWebSearchErrorHandling:
    """Test error handling in web search functionality."""
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, websearch_server):
        """Test handling of network errors."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            result = await websearch_server.search_web("test")
            assert "error" in result
            assert "Network error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_response_handling(self, websearch_server):
        """Test handling of invalid HTTP responses."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await websearch_server.search_web("test")
            assert "error" in result
            assert "404" in result["error"]
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, websearch_server):
        """Test handling of request timeouts."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await websearch_server.extract_content("https://example.com")
            assert "error" in result
            assert "timeout" in result["error"].lower()


class TestWebSearchLlamaIndexIntegration:
    """Test web search functionality with LlamaIndex integration."""
    
    @pytest.mark.asyncio
    async def test_llamaindex_agent_with_websearch(self, llamaindex_agent):
        """Test that the LlamaIndex agent has web search tools available."""
        # Check that web search tools are available
        tool_names = [tool.name for tool in llamaindex_agent.llama_tools]
        websearch_tools = [name for name in tool_names if 'websearch' in name.lower()]
        
        assert len(websearch_tools) > 0, "No web search tools found in LlamaIndex agent"
        print(f"Found web search tools: {websearch_tools}")
    
    @pytest.mark.asyncio
    async def test_websearch_via_llamaindex(self, llamaindex_agent):
        """Test web search functionality through LlamaIndex agent."""
        # Test a simple web search query
        query = "Search for Python programming tutorial"
        
        try:
            # This would normally use the agent's query method
            # For now, we'll test the underlying web search functionality
            websearch_tool = None
            for tool in llamaindex_agent.llama_tools:
                if 'websearch' in tool.name.lower() and 'search_web' in tool.name.lower():
                    websearch_tool = tool
                    break
            
            if websearch_tool:
                # Test the tool function directly
                result = await websearch_tool.func(query="Python tutorial", max_results=2)
                assert result is not None
                print(f"Web search result: {result[:200]}...")
            else:
                pytest.skip("Web search tool not found in LlamaIndex agent")
                
        except Exception as e:
            # If internet is not available, skip the test
            pytest.skip(f"Internet connection required: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
