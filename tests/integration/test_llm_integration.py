#!/usr/bin/env python3
"""
Test script to check LLM integration with the unified agent
"""

import asyncio
import os
from core.config import ConfigManager
from core.agent import UnifiedAIShowmakerAgent

async def test_llm_integration():
    print("🧪 Testing LLM Integration")
    print("=" * 50)
    
    # Check environment variables
    print("🔍 Environment Variables:")
    inference_key = os.getenv('INFERENCE_NET_KEY')
    if inference_key:
        print(f"✅ INFERENCE_NET_KEY: {inference_key[:10]}...")
    else:
        print("❌ INFERENCE_NET_KEY: Not found")
    
    inference_model = os.getenv('INFERENCE_NET_MODEL')
    if inference_model:
        print(f"✅ INFERENCE_NET_MODEL: {inference_model}")
    else:
        print("❌ INFERENCE_NET_MODEL: Not found")
    
    inference_url = os.getenv('INFERENCE_NET_BASE_URL')
    if inference_url:
        print(f"✅ INFERENCE_NET_BASE_URL: {inference_url}")
    else:
        print("❌ INFERENCE_NET_BASE_URL: Not found")
    
    print()
    
    # Load configuration
    print("📋 Loading configuration...")
    config = ConfigManager()
    print(f"✅ Configuration loaded: {type(config)}")
    
    # Check config values
    print("\n🔍 Configuration Values:")
    inference_net_key = config.get('inference_net_key')
    if inference_net_key:
        print(f"✅ inference_net_key: {inference_net_key[:10]}...")
    else:
        print("❌ inference_net_key: Not found")
    
    inference_net_model = config.get('inference_net_model')
    if inference_net_model:
        print(f"✅ inference_net_model: {inference_net_model}")
    else:
        print("❌ inference_net_model: Not found")
    
    inference_net_url = config.get('inference_net_base_url')
    if inference_net_url:
        print(f"✅ inference_net_base_url: {inference_net_url}")
    else:
        print("❌ inference_net_base_url: Not found")
    
    print()
    
    # Initialize agent
    print("🤖 Initializing agent...")
    agent = UnifiedAIShowmakerAgent(config)
    
    # Check LLM info before initialization
    print("\n🔍 LLM Info (before init):")
    llm_info = agent.get_llm_info()
    print(f"LLM Status: {llm_info}")
    
    print("\n🔄 Initializing agent...")
    await agent.initialize()
    
    # Check LLM info after initialization
    print("\n🔍 LLM Info (after init):")
    llm_info = agent.get_llm_info()
    print(f"LLM Status: {llm_info}")
    
    if agent.llm:
        print("✅ LLM initialized successfully!")
        print(f"LLM Type: {type(agent.llm)}")
        print(f"Model: {getattr(agent.llm, 'model', 'unknown')}")
        print(f"Base URL: {getattr(agent.llm, 'base_url', 'unknown')}")
    else:
        print("❌ No LLM available")
    
    # Test a simple query
    print("\n💬 Testing simple query...")
    result = await agent.query("What tools are available?")
    print(f"Query Result: {result[:200]}...")
    
    print("\n🔄 Shutting down agent...")
    await agent.shutdown()
    print("✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_llm_integration())
