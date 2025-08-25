#!/usr/bin/env python3
"""
Web Search MCP Server Demo

Demonstrates the web search functionality using DuckDuckGo scraping.
No API keys required - completely self-contained web search.
"""

import asyncio
import sys
import os
from pathlib import Path

# Set console encoding to UTF-8 for emoji support
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from mcp_servers.websearch.server import WebSearchMCPServer


async def demo_web_search():
    """Demonstrate web search functionality."""
    print("🔍 Web Search MCP Server Demo")
    print("=" * 50)
    print("No API keys required - using DuckDuckGo scraping")
    print("=" * 50)
    
    # Initialize web search server
    print("\n🚀 Initializing Web Search Server...")
    server = WebSearchMCPServer()
    await server.initialize()
    print(f"✅ Server initialized with {len(server.tools)} tools")
    
    # Show available tools
    print("\n📋 Available Tools:")
    for tool_name in server.tools.keys():
        print(f"  • {tool_name}")
    
    # Demo 1: Basic web search
    print("\n" + "=" * 50)
    print("🔍 Demo 1: Basic Web Search")
    print("=" * 50)
    
    query = "Python programming tutorial"
    print(f"Searching for: '{query}'")
    
    try:
        results = await server.search_web(query, max_results=3)
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print(f"✅ Found {results['total_results']} results")
            print(f"Source: {results['source']}")
            
            for i, result in enumerate(results['results'], 1):
                print(f"\n{i}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Snippet: {result['snippet'][:100]}...")
                
    except Exception as e:
        print(f"❌ Search failed: {str(e)}")
    
    # Demo 2: Content extraction
    print("\n" + "=" * 50)
    print("📄 Demo 2: Content Extraction")
    print("=" * 50)
    
    test_url = "https://httpbin.org/html"
    print(f"Extracting content from: {test_url}")
    
    try:
        content = await server.extract_content(test_url, max_length=500)
        
        if "error" in content:
            print(f"❌ Error: {content['error']}")
        else:
            print(f"✅ Content extracted successfully")
            print(f"Title: {content['title']}")
            print(f"Content length: {len(content['text_content'])} characters")
            print(f"Content preview: {content['text_content'][:200]}...")
            
    except Exception as e:
        print(f"❌ Content extraction failed: {str(e)}")
    
    # Demo 3: Search and extract
    print("\n" + "=" * 50)
    print("🔍📄 Demo 3: Search and Extract")
    print("=" * 50)
    
    query = "Flask web framework"
    print(f"Searching and extracting content for: '{query}'")
    
    try:
        results = await server.search_and_extract(query, max_results=2, max_content_length=300)
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print(f"✅ Found and extracted content from {results['total_results']} pages")
            
            for i, result in enumerate(results['results'], 1):
                print(f"\n{i}. {result['page_title']}")
                print(f"   URL: {result['url']}")
                print(f"   Content: {result['extracted_content'][:150]}...")
                
    except Exception as e:
        print(f"❌ Search and extract failed: {str(e)}")
    
    # Demo 4: Search suggestions
    print("\n" + "=" * 50)
    print("💡 Demo 4: Search Suggestions")
    print("=" * 50)
    
    query = "Python"
    print(f"Getting suggestions for: '{query}'")
    
    try:
        suggestions = await server.get_search_suggestions(query, max_suggestions=5)
        
        if "error" in suggestions:
            print(f"❌ Error: {suggestions['error']}")
        else:
            print(f"✅ Found {suggestions['total_suggestions']} suggestions")
            print(f"Source: {suggestions['source']}")
            
            for i, suggestion in enumerate(suggestions['suggestions'], 1):
                print(f"  {i}. {suggestion}")
                
    except Exception as e:
        print(f"❌ Suggestions failed: {str(e)}")
    
    # Demo 5: Rate limiting and caching
    print("\n" + "=" * 50)
    print("⚡ Demo 5: Rate Limiting and Caching")
    print("=" * 50)
    
    query = "test query"
    print(f"Testing rate limiting with query: '{query}'")
    
    try:
        import time
        
        # First search (should hit the network)
        start_time = time.time()
        result1 = await server.search_web(query, max_results=1)
        first_search_time = time.time() - start_time
        
        # Second search (should use cache)
        start_time = time.time()
        result2 = await server.search_web(query, max_results=1)
        second_search_time = time.time() - start_time
        
        print(f"First search time: {first_search_time:.2f}s")
        print(f"Second search time: {second_search_time:.2f}s")
        if second_search_time > 0:
            print(f"Cache speedup: {first_search_time/second_search_time:.1f}x faster")
        else:
            print("Cache speedup: Instant (cached)")
        
        if result1 == result2:
            print("✅ Caching working correctly")
        else:
            print("⚠️  Cache results differ")
            
    except Exception as e:
        print(f"❌ Rate limiting test failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Web Search Demo Completed!")
    print("=" * 50)
    print("Features demonstrated:")
    print("✅ DuckDuckGo web search (no API key required)")
    print("✅ Web content extraction")
    print("✅ Combined search and extract")
    print("✅ Search suggestions")
    print("✅ Rate limiting and caching")
    print("✅ Error handling")
    print("=" * 50)


async def interactive_demo():
    """Interactive demo mode."""
    print("\n🎮 Interactive Web Search Demo")
    print("=" * 50)
    print("Commands:")
    print("  search <query> - Search the web")
    print("  extract <url> - Extract content from URL")
    print("  suggest <query> - Get search suggestions")
    print("  quit - Exit demo")
    print("=" * 50)
    
    # Initialize server
    server = WebSearchMCPServer()
    await server.initialize()
    
    while True:
        try:
            command = input("\n🔍 Enter command: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
            
            if command.startswith('search '):
                query = command[7:]  # Remove 'search ' prefix
                print(f"Searching for: '{query}'")
                
                results = await server.search_web(query, max_results=3)
                if "error" not in results:
                    print(f"Found {results['total_results']} results:")
                    for i, result in enumerate(results['results'], 1):
                        print(f"  {i}. {result['title']}")
                        print(f"     {result['url']}")
                else:
                    print(f"Error: {results['error']}")
            
            elif command.startswith('extract '):
                url = command[8:]  # Remove 'extract ' prefix
                print(f"Extracting content from: {url}")
                
                content = await server.extract_content(url, max_length=500)
                if "error" not in content:
                    print(f"Title: {content['title']}")
                    print(f"Content: {content['text_content'][:300]}...")
                else:
                    print(f"Error: {content['error']}")
            
            elif command.startswith('suggest '):
                query = command[8:]  # Remove 'suggest ' prefix
                print(f"Getting suggestions for: '{query}'")
                
                suggestions = await server.get_search_suggestions(query, max_suggestions=5)
                if "error" not in suggestions:
                    print("Suggestions:")
                    for i, suggestion in enumerate(suggestions['suggestions'], 1):
                        print(f"  {i}. {suggestion}")
                else:
                    print(f"Error: {suggestions['error']}")
            
            else:
                print("Unknown command. Use: search, extract, suggest, or quit")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


async def main():
    """Main demo function."""
    try:
        # Run automated demo
        await demo_web_search()
        
        # Ask if user wants interactive demo
        response = input("\n🎮 Would you like to try interactive mode? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            await interactive_demo()
        
        print("\n👋 Thanks for trying the Web Search MCP Server!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
