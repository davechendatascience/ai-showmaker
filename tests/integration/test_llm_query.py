#!/usr/bin/env python3
"""
Test script to specifically test LLM query handling
"""

import asyncio
from core.config import ConfigManager
from core.agent import UnifiedAIShowmakerAgent

async def test_llm_query():
    print("🧪 Testing LLM Query Handling")
    print("=" * 50)
    
    # Load configuration and initialize agent
    config = ConfigManager()
    agent = UnifiedAIShowmakerAgent(config)
    
    print("🔄 Initializing agent...")
    await agent.initialize()
    
    # Verify LLM is available
    llm_info = agent.get_llm_info()
    print(f"LLM Status: {llm_info}")
    
    if not agent.llm:
        print("❌ No LLM available, cannot test")
        await agent.shutdown()
        return
    
    print("✅ LLM is available!")
    
    # Test different types of queries
    test_queries = [
        "What can you help me with?",
        "Tell me about the available tools",
        "How many tools do you have access to?",
        "What is the purpose of this system?",
        "Can you explain what MCP servers are?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test Query {i}: {query}")
        print("-" * 40)
        
        try:
            result = await agent.query(query)
            print(f"✅ Response: {result[:300]}...")
            
            # Check if this looks like an LLM response vs basic pattern matching
            if any(phrase in result.lower() for phrase in [
                "i can help you with various tasks",
                "available tools:",
                "mcp tools",
                "try asking about"
            ]):
                print("⚠️  This looks like basic pattern matching, not LLM")
            else:
                print("🎯 This looks like an LLM-generated response!")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n🔄 Shutting down agent...")
    await agent.shutdown()
    print("✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_llm_query())
