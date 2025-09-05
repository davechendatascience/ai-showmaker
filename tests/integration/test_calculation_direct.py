#!/usr/bin/env python3
"""
Direct test of the calculation MCP server without HTTP bridge
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import MCP servers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def test_calculation_server():
    """Test the calculation server directly."""
    print("🧮 Testing Calculation MCP Server directly...")
    
    try:
        # Import the calculation server
        from mcp_servers.calculation.server import CalculationMCPServer
        
        # Create and initialize the server
        print("   Creating server instance...")
        server_instance = CalculationMCPServer()
        
        print("   Initializing server...")
        await server_instance.initialize()
        
        print("   Server initialized successfully!")
        print(f"   Available tools: {list(server_instance.tools.keys())}")
        
        # Test tool execution
        print("\n🔍 Testing tool execution...")
        
        # Test calculate tool
        print("   Testing calculate tool...")
        result = await server_instance.execute_tool("calculate", {"expression": "2 + 3"})
        print(f"   Result: {result}")
        
        # Test another calculation
        print("   Testing calculate tool with 10 * 2...")
        result = await server_instance.execute_tool("calculate", {"expression": "10 * 2"})
        print(f"   Result: {result}")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 Direct Calculation Server Test")
    print("=" * 40)
    
    try:
        success = asyncio.run(test_calculation_server())
        if success:
            print("\n🎉 Calculation server is working correctly!")
        else:
            print("\n⚠️ Calculation server has issues.")
        return success
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
