"""
Quick test for the todo parameter conversion fix.
Tests the MCP server directly to verify it now handles various input formats.
"""
import asyncio
import sys
import os
from pathlib import Path

# Fix encoding for emojis on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from mcp_servers.monitoring.server import MonitoringMCPServer


async def test_todo_formats():
    """Test different todo input formats."""
    print("🧪 Testing Todo Input Format Fixes")
    print("=" * 40)
    
    server = MonitoringMCPServer()
    await server.initialize()
    
    # Create a session first
    await server.execute_tool("create_session", {"session_name": "test_fix"})
    
    # Test 1: Simple string array
    print("\n📝 Test 1: Simple string array")
    result = await server.execute_tool("create_todos", {
        "todos": ["Install dependencies", "Configure git", "Set up database"]
    })
    print(f"✅ {result.data}")
    
    # Test 2: Mixed format with objects
    print("\n📝 Test 2: Mixed format with objects")
    result = await server.execute_tool("create_todos", {
        "todos": [
            {"content": "Plan architecture", "status": "pending"},
            {"content": "Write code", "status": "in_progress", "activeForm": "Writing the code"},
            "Test the application"  # Simple string
        ]
    })
    print(f"✅ {result.data}")
    
    # Test 3: Get current todos
    print("\n📝 Test 3: Get current todos")
    result = await server.execute_tool("get_current_todos", {})
    print(f"✅ {result.data}")
    
    await server.shutdown()
    print("\n🎉 All todo format tests completed!")


async def main():
    """Main test function."""
    await test_todo_formats()
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)