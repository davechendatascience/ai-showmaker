#!/usr/bin/env python3
"""
Simple test script for the running MCP bridge
"""

import requests
import json

def test_bridge():
    """Test the running bridge."""
    base_url = "http://localhost:8000"
    
    print("🔧 Testing MCP Bridge")
    print("=" * 30)
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Test tools endpoint
    print("\n2. Testing tools endpoint...")
    try:
        response = requests.get(f"{base_url}/tools", timeout=5)
        print(f"   Status: {response.status_code}")
        tools = response.json()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"     - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
    except Exception as e:
        print(f"   ❌ Tools listing failed: {e}")
        return False
    
    # Test tool execution
    print("\n3. Testing tool execution...")
    test_cases = [
        {"tool_name": "calculate", "params": {"expression": "2 + 3"}},
        {"tool_name": "calculate", "params": {"expression": "10 * 2"}}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Test {i}: {test_case['tool_name']} with {test_case['params']}")
        try:
            response = requests.post(
                f"{base_url}/execute",
                json=test_case,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Result: {result}")
            
            if response.status_code == 200 and result.get('success'):
                print("   ✅ Success!")
            else:
                print("   ❌ Failed!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n🎉 Bridge testing completed!")
    return True

if __name__ == "__main__":
    test_bridge()
