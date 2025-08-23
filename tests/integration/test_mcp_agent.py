"""
Integration tests for MCP-based AI-Showmaker agent.
Tests the complete system with all MCP servers working together.
"""
import os
import asyncio
import time
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.agent import AIShowmakerAgent
from core.config import ConfigManager
from core.exceptions import AIShowmakerError
from tests.scenarios.test_queries import TEST_QUERIES, get_all_basic_tests, get_comprehensive_test_suite


class TestResult:
    """Store results of a single test."""
    def __init__(self, query: str, success: bool = False, response: str = "", error: str = "", duration: float = 0.0):
        self.query = query
        self.success = success
        self.response = response
        self.error = error
        self.duration = duration
        self.timestamp = datetime.now()


class MCPAgentTester:
    """Integration tester for MCP-based AI-Showmaker agent."""
    
    def __init__(self, interactive: bool = True, timeout: int = 60):
        self.interactive = interactive
        self.timeout = timeout
        self.results = []
        self.agent = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the MCP-based agent asynchronously."""
        if self._initialized:
            return
            
        try:
            config = ConfigManager()
            self.agent = AIShowmakerAgent(config)
            await self.agent.initialize()
            self._initialized = True
            print("✅ MCP-based AI-Showmaker Agent initialized successfully!")
        except AIShowmakerError as e:
            print(f"❌ Failed to initialize agent: {str(e)}")
            raise e
    
    async def shutdown(self):
        """Shutdown the agent and all MCP servers."""
        if self.agent and self._initialized:
            await self.agent.shutdown()
    
    def run_single_test(self, query: str) -> TestResult:
        """Run a single test query."""
        print(f"\n{'='*50}")
        print(f"TESTING: {query}")
        print(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            if not self._initialized:
                raise RuntimeError("Agent not initialized. Call initialize() first.")
            
            if self.interactive:
                response = self.agent.human_in_the_loop(query)
            else:
                response = self.agent.run(query)
            
            duration = time.time() - start_time
            
            if response:
                result = TestResult(query, True, str(response), "", duration)
                print(f"✅ SUCCESS ({duration:.2f}s)")
            else:
                result = TestResult(query, False, "", "No response or user rejected", duration)
                print(f"❌ FAILED ({duration:.2f}s): No response")
        
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(query, False, "", str(e), duration)
            print(f"❌ ERROR ({duration:.2f}s): {str(e)}")
        
        self.results.append(result)
        return result
    
    def run_test_suite(self, test_list: list, suite_name: str = "Test Suite"):
        """Run a list of tests."""
        print(f"\n🚀 STARTING {suite_name.upper()}")
        print(f"📋 Running {len(test_list)} tests...\n")
        
        for i, query in enumerate(test_list, 1):
            print(f"\n[{i}/{len(test_list)}] ", end="")
            result = self.run_single_test(query)
            
            # Brief pause between tests
            if i < len(test_list):
                time.sleep(1)
        
        self.print_summary(suite_name)
    
    def print_summary(self, suite_name: str = ""):
        """Print test results summary."""
        total = len(self.results)
        passed = len([r for r in self.results if r.success])
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"📊 {suite_name} SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result.success:
                    print(f"   • {result.query}")
                    print(f"     Error: {result.error}")
        
        avg_duration = sum(r.duration for r in self.results) / total if total > 0 else 0
        print(f"\n⏱️ Average Duration: {avg_duration:.2f}s")
        print(f"{'='*60}")


async def main():
    """Main test execution function."""
    print("🤖 AI-Showmaker MCP Integration Tests")
    print("=" * 40)
    
    # Initialize tester
    tester = MCPAgentTester(interactive=False)  # Non-interactive for CI/CD
    
    try:
        await tester.initialize()
        
        # Run basic functionality tests
        print("\n🔧 Running Basic Functionality Tests...")
        basic_tests = get_all_basic_tests()
        tester.run_test_suite(basic_tests, "Basic Functionality")
        
        # Clear results for next suite
        tester.results.clear()
        
        # Run comprehensive feature tests
        print("\n🚀 Running Comprehensive Feature Tests...")
        comprehensive_tests = get_comprehensive_test_suite()
        tester.run_test_suite(comprehensive_tests, "Comprehensive Features")
        
    except AIShowmakerError as e:
        print(f"❌ AI-Showmaker Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return 1
    finally:
        await tester.shutdown()
        print("✅ Integration tests completed")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)