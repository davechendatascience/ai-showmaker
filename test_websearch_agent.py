#!/usr/bin/env python3
"""
Simple Web Search Agent Test

This script tests if web search is working with the intelligent agent.
"""

import asyncio
import logging
from core.intelligent_reliable_agent import IntelligentReliableAIShowmakerAgent
from core.config import ConfigManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websearch_agent():
    """Test web search functionality with the intelligent agent."""
    print("🔍 Testing Web Search with Intelligent Agent")
    print("=" * 50)
    
    try:
        # Initialize agent
        print("🚀 Initializing agent...")
        config = ConfigManager()
        agent = IntelligentReliableAIShowmakerAgent(config)
        await agent.initialize()
        
        print("✅ Agent initialized successfully")
        
        # Check available tools
        tools_info = agent.get_tools_info()
        websearch_tools = [tool for tool in tools_info if 'websearch' in tool.get('name', '').lower()]
        
        print(f"📊 Total tools available: {len(tools_info)}")
        print(f"🔍 Web search tools found: {len(websearch_tools)}")
        
        if websearch_tools:
            print("✅ Web search tools are available!")
            for tool in websearch_tools:
                print(f"  • {tool.get('name', 'Unknown')}")
        else:
            print("❌ No web search tools found")
            return False
        
        # Test 1: Simple web search
        print(f"\n🔍 Test 1: Simple web search")
        print("Searching for: 'Python programming language'")
        
        result1 = await agent.query("Search the web for information about Python programming language")
        
        if result1 and "Error:" not in result1:
            print("✅ Web search successful!")
            print(f"Result preview: {result1[:200]}...")
        else:
            print("❌ Web search failed")
            print(f"Error: {result1}")
            return False
        
        # Test 2: Technology comparison
        print(f"\n🔍 Test 2: Technology comparison")
        print("Comparing React vs Vue.js")
        
        result2 = await agent.query("Search the web to compare React and Vue.js frameworks")
        
        if result2 and "Error:" not in result2:
            print("✅ Technology comparison successful!")
            print(f"Result preview: {result2[:200]}...")
        else:
            print("❌ Technology comparison failed")
            print(f"Error: {result2}")
            return False
        
        # Test 3: Current events
        print(f"\n🔍 Test 3: Current events")
        print("Searching for latest AI developments")
        
        result3 = await agent.query("Search the web for the latest developments in artificial intelligence in 2024")
        
        if result3 and "Error:" not in result3:
            print("✅ Current events search successful!")
            print(f"Result preview: {result3[:200]}...")
        else:
            print("❌ Current events search failed")
            print(f"Error: {result3}")
            return False
        
        # Show statistics
        print(f"\n📊 Agent Statistics:")
        stats = agent.get_statistics()
        print(f"Total queries: {stats.get('total_queries', 0)}")
        print(f"Successful queries: {stats.get('successful_queries', 0)}")
        print(f"Failed queries: {stats.get('failed_queries', 0)}")
        print(f"Tool calls: {stats.get('total_tool_calls', 0)}")
        
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            print(f"Complex tasks detected: {planning_stats.get('complex_tasks_detected', 0)}")
            print(f"Task plans created: {planning_stats.get('task_plans_created', 0)}")
        
        print(f"\n🎉 All web search tests passed!")
        print("✅ Web search is working with the intelligent agent")
        print("✅ Results are being processed correctly")
        print("✅ Agent can perform research tasks")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        if 'agent' in locals():
            await agent.shutdown()


async def main():
    """Main test function."""
    success = await test_websearch_agent()
    
    if success:
        print(f"\n🎯 Web Search Integration Status: ✅ WORKING")
        print("The web search functionality is properly integrated with the intelligent agent.")
        print("You can now use web search in complex tasks and research scenarios.")
    else:
        print(f"\n🎯 Web Search Integration Status: ❌ NOT WORKING")
        print("There are issues with the web search integration that need to be resolved.")


if __name__ == "__main__":
    asyncio.run(main())
