#!/usr/bin/env python3
"""
LEGACY Test Runner - Basic MCP Server Tests Only

This is a legacy test runner that only tests basic MCP server functionality.
For comprehensive testing of the intelligent task planning system, use:
    python run_comprehensive_tests.py

This legacy runner tests:
- Basic MCP servers (calculation, development, monitoring, remote)
- Todo functionality fixes

It does NOT test:
- Intelligent task planning system
- LlamaIndex integration
- Output validation
- Enhanced MCP integration
- Improved agent capabilities
"""
import os
import sys
from pathlib import Path

# Set encoding first, before any imports
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Run all tests with proper encoding setup."""
    print("🧪 Running AI-Showmaker MCP Tests")
    print("=" * 40)
    
    # Test 1: MCP Servers
    print("\n🔧 Testing MCP Servers...")
    try:
        from tests.mcp.test_servers import main as test_servers
        import asyncio
        result1 = asyncio.run(test_servers())
        if result1 == 0:
            print("✅ MCP Server tests passed")
        else:
            print("❌ MCP Server tests failed")
    except Exception as e:
        print(f"❌ MCP Server tests error: {e}")
        result1 = 1
    
    # Test 2: Todo Fix
    print("\n📋 Testing Todo Functionality...")
    try:
        from tests.mcp.test_todo_fix import main as test_todo_fix
        result2 = asyncio.run(test_todo_fix())
        if result2 == 0:
            print("✅ Todo fix tests passed")
        else:
            print("❌ Todo fix tests failed")
    except Exception as e:
        print(f"❌ Todo fix tests error: {e}")
        result2 = 1
    
    # Summary
    print(f"\n{'='*40}")
    if result1 == 0 and result2 == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)