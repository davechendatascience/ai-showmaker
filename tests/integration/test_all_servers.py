#!/usr/bin/env python3
"""
Comprehensive test script for all MCP servers
"""

import requests
import json

def test_all_servers():
    """Test all MCP servers through the bridge."""
    base_url = "http://localhost:8000"
    
    print("🔧 Testing All MCP Servers")
    print("=" * 50)
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        health_data = response.json()
        print(f"   Servers: {health_data.get('servers', 0)}")
        print(f"   Tools: {health_data.get('tools', 0)}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Test servers endpoint
    print("\n2. Testing servers endpoint...")
    try:
        response = requests.get(f"{base_url}/servers", timeout=5)
        print(f"   Status: {response.status_code}")
        servers_data = response.json()
        print(f"   Total servers: {servers_data.get('total_servers', 0)}")
        print(f"   Total tools: {servers_data.get('total_tools', 0)}")
        
        for server_name, server_info in servers_data.get('servers', {}).items():
            print(f"   📦 {server_name}: {server_info.get('tool_count', 0)} tools")
            for tool in server_info.get('tools', []):
                print(f"      - {tool}")
    except Exception as e:
        print(f"   ❌ Servers listing failed: {e}")
        return False
    
    # Test tools endpoint
    print("\n3. Testing tools endpoint...")
    try:
        response = requests.get(f"{base_url}/tools", timeout=5)
        print(f"   Status: {response.status_code}")
        tools = response.json()
        print(f"   Found {len(tools)} tools total:")
        
        # Group tools by server
        tools_by_server = {}
        for tool in tools:
            server = tool.get('server', 'unknown')
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)
        
        for server, server_tools in tools_by_server.items():
            print(f"   📦 {server} server ({len(server_tools)} tools):")
            for tool in server_tools:
                print(f"      - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
    except Exception as e:
        print(f"   ❌ Tools listing failed: {e}")
        return False
    
    # Test tool execution for each server
    print("\n4. Testing tool execution...")
    
    # Define test cases for each server (using actual tool names from the bridge)
    test_cases = {
        "calculation": [
            {"tool_name": "calculate", "params": {"expression": "2 + 3"}},
            {"tool_name": "calculate", "params": {"expression": "10 * 2"}},
        ],
        "development": [
            {"tool_name": "find_files", "params": {"pattern": "*.py"}},
            {"tool_name": "search_in_files", "params": {"pattern": "def", "path": "."}},
        ],
        "monitoring": [
            {"tool_name": "create_todos", "params": {"todos": ["Test task 1", "Test task 2"]}},
            {"tool_name": "get_current_todos", "params": {}},
        ],
        "remote": [
            {"tool_name": "execute_command", "params": {"command": "echo 'Hello from remote'"}},
        ],
        "websearch": [
            {"tool_name": "search_web", "params": {"query": "Python programming", "max_results": 3}},
        ]
    }
    
    success_count = 0
    total_tests = 0
    
    for server_name, tests in test_cases.items():
        print(f"\n   📦 Testing {server_name} server:")
        
        for i, test_case in enumerate(tests, 1):
            total_tests += 1
            print(f"      Test {i}: {test_case['tool_name']} with {test_case['params']}")
            
            try:
                response = requests.post(
                    f"{base_url}/execute",
                    json=test_case,
                    timeout=15,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"      ✅ Success: {result.get('result', 'No result')}")
                        success_count += 1
                    else:
                        print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                else:
                    print(f"      ❌ HTTP Error: {response.text}")
                    
            except Exception as e:
                print(f"      ❌ Exception: {e}")
    
    # Summary
    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    test_all_servers()
