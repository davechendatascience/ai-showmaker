"""
Unit tests for individual MCP servers.
Tests each server in isolation to validate tool functionality.
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

from mcp_servers.calculation.server import CalculationMCPServer
from mcp_servers.remote.server import RemoteMCPServer
from mcp_servers.development.server import DevelopmentMCPServer
from mcp_servers.monitoring.server import MonitoringMCPServer


class MCPServerTester:
    """Test individual MCP servers."""
    
    async def test_calculation_server(self):
        """Test the calculation MCP server."""
        print("\n🧮 Testing Calculation MCP Server...")
        
        server = CalculationMCPServer()
        await server.initialize()
        
        # Test basic calculation
        result = await server.execute_tool("calculate", {"expression": "2 + 3 * 4"})
        assert result.result_type.value == "success"
        assert result.data == "14"
        print("✅ Basic calculation: 2 + 3 * 4 = 14")
        
        # Test advanced calculation
        result = await server.execute_tool("calculate", {"expression": "sqrt(144) + factorial(5)"})
        assert result.result_type.value == "success"
        assert result.data == "132"
        print("✅ Advanced calculation: sqrt(144) + factorial(5) = 132")
        
        # Test variable operations
        result = await server.execute_tool("set_variable", {"name": "x", "value": 10})
        assert result.result_type.value == "success"
        print("✅ Variable setting: x = 10")
        
        result = await server.execute_tool("calculate", {"expression": "x * 2 + 5"})
        assert result.result_type.value == "success"
        assert result.data == "25"
        print("✅ Variable calculation: x * 2 + 5 = 25")
        
        await server.shutdown()
        print("✅ Calculation server tests passed!")
    
    async def test_development_server(self):
        """Test the development MCP server."""
        print("\n🔧 Testing Development MCP Server...")
        
        server = DevelopmentMCPServer()
        await server.initialize()
        
        # Test git status
        result = await server.execute_tool("git_status", {})
        assert result.result_type.value == "success"
        print(f"✅ Git status: {result.data[:50]}...")
        
        # Test file finding
        result = await server.execute_tool("find_files", {"pattern": "*.py", "directory": "."})
        assert result.result_type.value == "success"
        print(f"✅ Find Python files: Found {len(result.data.split())} files")
        
        await server.shutdown()
        print("✅ Development server tests passed!")
    
    async def test_monitoring_server(self):
        """Test the monitoring MCP server."""
        print("\n📋 Testing Monitoring MCP Server...")
        
        server = MonitoringMCPServer()
        await server.initialize()
        
        # Create a session
        result = await server.execute_tool("create_session", {"session_name": "test"})
        assert result.result_type.value == "success"
        print("✅ Session creation")
        
        # Create todos
        todos_data = [
            {"content": "Test task 1", "status": "pending", "activeForm": "Testing task 1"},
            {"content": "Test task 2", "status": "in_progress", "activeForm": "Testing task 2"}
        ]
        result = await server.execute_tool("create_todos", {"todos": todos_data})
        assert result.result_type.value == "success"
        print("✅ Todo creation: 2 items")
        
        # Get current todos
        result = await server.execute_tool("get_current_todos", {})
        assert result.result_type.value == "success"
        print("✅ Todo retrieval")
        
        # Update todo status
        result = await server.execute_tool("update_todo_status", {
            "todo_id": "todo_1", 
            "status": "completed",
            "notes": "Test completed"
        })
        assert result.result_type.value == "success"
        print("✅ Todo status update")
        
        await server.shutdown()
        print("✅ Monitoring server tests passed!")
    
    async def test_remote_server_basic(self):
        """Test basic remote server functionality (non-SSH dependent tests)."""
        print("\n🌐 Testing Remote MCP Server (basic)...")
        
        server = RemoteMCPServer()
        await server.initialize()
        
        # Test server info
        info = server.get_server_info()
        assert info['name'] == 'remote'
        assert info['tool_count'] == 4
        print("✅ Server info retrieval")
        
        # Note: Skip SSH-dependent tests in unit testing
        # Those should be tested in integration tests
        
        await server.shutdown()
        print("✅ Remote server basic tests passed!")
    
    async def run_all_tests(self):
        """Run all MCP server tests."""
        print("🧪 Running MCP Server Unit Tests")
        print("=" * 40)
        
        try:
            await self.test_calculation_server()
            await self.test_development_server()
            await self.test_monitoring_server()
            await self.test_remote_server_basic()
            
            print(f"\n{'='*40}")
            print("🎉 All MCP server tests passed!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            return False


async def main():
    """Main test function."""
    tester = MCPServerTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)