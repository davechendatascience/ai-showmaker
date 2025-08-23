"""
Integration tests specifically for agent todo list functionality.
Tests whether the agent actually uses todos during complex task execution.
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

from core.agent import AIShowmakerAgent
from core.config import ConfigManager
from core.exceptions import AIShowmakerError


class AgentTodoTester:
    """Test agent's actual usage of todo lists during task execution."""
    
    def __init__(self):
        self.agent = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the agent."""
        if self._initialized:
            return
            
        try:
            config = ConfigManager()
            self.agent = AIShowmakerAgent(config)
            await self.agent.initialize()
            self._initialized = True
            print("✅ Agent initialized for todo testing")
        except AIShowmakerError as e:
            print(f"❌ Failed to initialize agent: {str(e)}")
            raise e
    
    async def shutdown(self):
        """Shutdown the agent."""
        if self.agent and self._initialized:
            await self.agent.shutdown()
    
    def test_todo_creation_in_complex_task(self):
        """Test if agent creates todos for complex multi-step tasks."""
        print("\n🧪 Testing todo creation during complex task...")
        
        # Complex task that should trigger todo creation
        complex_task = """
        I need to build and deploy a simple calculator web application. This involves:
        1. Creating the calculator logic
        2. Writing a web interface  
        3. Deploying it to the remote server
        4. Testing that it works
        Please create a todo list and track your progress through each step.
        """
        
        try:
            # Get monitoring server to track tool calls
            monitoring_server = self.agent.server_manager.servers.get('monitoring')
            
            if not monitoring_server:
                print("❌ No monitoring server found")
                return False
            
            # Track initial state
            initial_contexts = len(monitoring_server.contexts)
            
            # Execute the complex task
            result = self.agent.run(complex_task)
            print(f"✅ Complex task executed")
            
            # Check if todos were actually created by examining server state
            final_contexts = len(monitoring_server.contexts)
            todos_created = False
            
            if final_contexts > initial_contexts:
                # Check if any context has todos
                for context in monitoring_server.contexts.values():
                    if len(context.todo_items) > 0:
                        print(f"✅ Found {len(context.todo_items)} todos in session {context.session_id}")
                        todos_created = True
                        break
            
            # Also check tool execution metrics
            tool_calls = monitoring_server.get_server_info().get('tool_executions', {})
            create_todos_calls = tool_calls.get('create_todos', 0)
            
            if create_todos_calls > 0:
                print(f"✅ Agent called create_todos {create_todos_calls} times")
                todos_created = True
            
            if todos_created:
                print("✅ Agent successfully used todo functionality")
                return True
            else:
                print("❌ Agent did not use todo functionality")
                return False
                
        except Exception as e:
            print(f"❌ Complex task failed: {str(e)}")
            return False
    
    def test_explicit_todo_usage(self):
        """Test explicit todo list usage by the agent."""
        print("\n📋 Testing explicit todo list usage...")
        
        explicit_todo_task = "Create a todo list for setting up a development environment with these steps: install dependencies, configure git, set up database, run tests"
        
        try:
            result = self.agent.run(explicit_todo_task)
            print(f"✅ Explicit todo task executed")
            
            # Get monitoring server to track tool calls
            monitoring_server = self.agent.server_manager.servers.get('monitoring')
            
            if not monitoring_server:
                print("❌ No monitoring server found")
                return False
            
            # Check if todos were actually created by examining server state
            todos_found = 0
            for context in monitoring_server.contexts.values():
                todos_found += len(context.todo_items)
            
            # Also check tool execution metrics
            tool_calls = monitoring_server.get_server_info().get('tool_executions', {})
            create_todos_calls = tool_calls.get('create_todos', 0)
            
            if todos_found >= 4:  # Should have at least 4 todos (install, configure, setup, run)
                print(f"✅ Agent created {todos_found} todos as expected")
                return True
            elif create_todos_calls > 0:
                print(f"✅ Agent called create_todos {create_todos_calls} times")
                return True
            else:
                print(f"❌ Expected todos created, but found {todos_found} todos and {create_todos_calls} create_todos calls")
                return False
                
        except Exception as e:
            print(f"❌ Explicit todo task failed: {str(e)}")
            return False
    
    def test_todo_progress_tracking(self):
        """Test if agent can track progress using todos."""
        print("\n📈 Testing todo progress tracking...")
        
        # First create a todo list
        create_task = "Create a todo list for building a simple Python script: 1) Plan the script, 2) Write the code, 3) Test it, 4) Document it"
        
        try:
            result1 = self.agent.run(create_task)
            print("✅ Todo list created")
            
            # Then ask for progress
            progress_task = "Show me the current progress of my todo list"
            result2 = self.agent.run(progress_task)
            print("✅ Progress check completed")
            
            # Get monitoring server to check actual progress tracking
            monitoring_server = self.agent.server_manager.servers.get('monitoring')
            
            if not monitoring_server:
                print("❌ No monitoring server found")
                return False
            
            # Check if get_current_todos or get_progress_summary was called
            tool_calls = monitoring_server.get_server_info().get('tool_executions', {})
            get_todos_calls = tool_calls.get('get_current_todos', 0)
            get_progress_calls = tool_calls.get('get_progress_summary', 0)
            
            if get_todos_calls > 0 or get_progress_calls > 0:
                print(f"✅ Agent tracked progress (get_todos: {get_todos_calls}, get_progress: {get_progress_calls})")
                return True
            else:
                print("❌ Agent did not use progress tracking tools")
                return False
                
        except Exception as e:
            print(f"❌ Progress tracking test failed: {str(e)}")
            return False
    
    async def run_all_todo_tests(self):
        """Run all todo-related tests."""
        print("🧪 Testing Agent Todo List Functionality")
        print("=" * 50)
        
        try:
            await self.initialize()
            
            # Run tests
            test1 = self.test_explicit_todo_usage()
            test2 = self.test_todo_progress_tracking() 
            test3 = self.test_todo_creation_in_complex_task()
            
            # Summary
            passed = sum([test1, test2, test3])
            total = 3
            
            print(f"\n{'='*50}")
            print(f"📊 Todo Functionality Test Results:")
            print(f"✅ Passed: {passed}/{total}")
            print(f"❌ Failed: {total-passed}/{total}")
            
            if passed == total:
                print("🎉 All todo functionality tests passed!")
                return True
            else:
                print("⚠️ Some todo functionality tests failed")
                return False
                
        except Exception as e:
            print(f"❌ Todo testing failed: {str(e)}")
            return False
        finally:
            await self.shutdown()


async def main():
    """Main test function."""
    tester = AgentTodoTester()
    success = await tester.run_all_todo_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)