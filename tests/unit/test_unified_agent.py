#!/usr/bin/env python3
"""
Simple test script for the new unified agent.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from core.agent import UnifiedAIShowmakerAgent
from core.config import ConfigManager


async def test_unified_agent():
    """Test the new unified agent."""
    print("🧪 Testing Unified AI-Showmaker Agent")
    print("=" * 50)
    
    try:
        # Initialize configuration
        print("📋 Loading configuration...")
        config = ConfigManager()
        print("✅ Configuration loaded")
        
        # Initialize agent
        print("🤖 Initializing unified agent...")
        agent = UnifiedAIShowmakerAgent(config)
        await agent.initialize()
        print("✅ Agent initialized successfully!")
        
        # Test basic functionality
        print("\n🔧 Testing basic functionality...")
        
        # Get tools info
        tools_info = agent.get_tools_info()
        print(f"📦 Available tools: {len(tools_info)}")
        
        # Get statistics
        stats = agent.get_statistics()
        print(f"📊 Agent statistics: {stats['tool_count']} tools, {stats['server_count']} servers")
        
        # Test simple query
        print("\n💬 Testing simple query...")
        result = await agent.query("What tools are available?")
        print(f"✅ Query result: {result[:100]}...")
        
        # Test complex task detection
        print("\n🎯 Testing complex task detection...")
        complex_result = await agent.query("Deploy a web application")
        print(f"✅ Complex task result: {complex_result[:100]}...")
        
        # Get final statistics
        final_stats = agent.get_statistics()
        print(f"\n📈 Final statistics:")
        print(f"   Total queries: {final_stats['agent_stats']['total_queries']}")
        print(f"   Tool calls: {final_stats['agent_stats']['total_tool_calls']}")
        print(f"   Complex tasks: {final_stats['task_planning_metrics']['complex_tasks_detected']}")
        
        print("\n🎉 All tests passed! Unified agent is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'agent' in locals():
            print("\n🔄 Shutting down agent...")
            await agent.shutdown()
            print("✅ Agent shutdown complete")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_unified_agent())
    sys.exit(0 if success else 1)
