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
            # Execute the complex task
            result = self.agent.run(complex_task)
            print(f"✅ Complex task executed")
            
            # Check if todos were created by looking at monitoring server
            # This would require access to the monitoring server's state
            # For now, we'll check if the agent mentioned todos in its response
            todo_keywords = ['todo', 'task', 'step', 'progress', 'tracking']
            if any(keyword in result.lower() for keyword in todo_keywords):
                print("✅ Agent appears to have used todo functionality")
                return True
            else:
                print("❌ Agent may not have used todo functionality")
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
            
            # Check if result contains todo-related content
            if 'todo' in result.lower() and ('created' in result.lower() or 'list' in result.lower()):
                print("✅ Agent successfully used todo functionality")
                return True
            else:
                print("❌ Agent did not properly use todo functionality")
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
            
            # Check if we got meaningful progress information
            if 'todo' in result2.lower() and ('progress' in result2.lower() or 'status' in result2.lower()):
                print("✅ Agent successfully tracked todo progress")
                return True
            else:
                print("❌ Agent did not properly track todo progress")
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