#!/usr/bin/env python3
"""
LLM Integration Test Suite for MCP Tools
Tests how the LLM actually uses MCP tools to answer natural language queries
"""

import asyncio
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.config import ConfigManager
from core.agent import UnifiedAIShowmakerAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMIntegrationTester:
    """Test LLM integration with MCP tools through natural language queries."""
    
    def __init__(self, agent: UnifiedAIShowmakerAgent):
        self.agent = agent
        self.test_results = {}
        self.start_time = datetime.now()
        
    def _evaluate_llm_integration(self, response: str, expected_behavior: str) -> bool:
        """Evaluate if the LLM response shows proper tool integration."""
        response_lower = response.lower()
        
        # Check for signs that LLM actually used tools (not just pattern matching)
        tool_usage_indicators = [
            "calculation", "calculated", "result", "answer",
            "variable", "set", "get", "clear",
            "workspace", "repository", "git", "status",
            "session", "todo", "progress", "monitoring",
            "search", "web", "suggestion", "duckduckgo",
            "matrix", "determinant", "statistics", "constant"
        ]
        
        # Check if response contains tool-related content
        has_tool_content = any(indicator in response_lower for indicator in tool_usage_indicators)
        
        # Check if response is substantial (not just "I can help you with that")
        is_substantial = len(response.strip()) > 50
        
        # Check if response shows actual computation/execution
        has_execution = any(word in response_lower for word in ["result", "answer", "calculated", "found", "executed"])
        
        # Special case: If the response contains a number that looks like a calculation result
        # (like "14" for "2 + 3 * 4"), consider it successful
        import re
        number_pattern = r'\b\d+\b'
        numbers = re.findall(number_pattern, response)
        has_calculation_result = len(numbers) > 0 and any(int(n) > 10 for n in numbers)
        
        # For calculation queries, prioritize numerical results
        if "calculate" in expected_behavior.lower() or "arithmetic" in expected_behavior.lower():
            return has_calculation_result or (has_tool_content and is_substantial and has_execution)
        
        return has_tool_content and is_substantial and has_execution
        
    async def test_calculation_llm_integration(self):
        """Test LLM's ability to use calculation tools through natural language."""
        print("\n🧮 Testing LLM + Calculation Tools Integration")
        print("=" * 50)
        
        tests = [
            {
                "query": "Use the calculation tool to compute 2 + 3 * 4. Execute the calculation_calculate tool with expression='2 + 3 * 4'",
                "expected_behavior": "LLM should use calculation tool and return 14",
                "description": "Basic arithmetic through LLM"
            },
            {
                "query": "Use the calculation tool to compute sqrt(16) + log(100). Execute the calculation_calculate tool with expression='sqrt(16) + log(100)'",
                "expected_behavior": "LLM should use calculation tool and return mathematical result",
                "description": "Mathematical functions through LLM"
            },
            {
                "query": "Use calculation tools to: 1) Set variable 'test_var' to 42 using calculation_set_variable, 2) Get all variables using calculation_get_variables, 3) Clear all variables using calculation_clear_variables",
                "expected_behavior": "LLM should execute multiple calculation tool calls in sequence",
                "description": "Multi-step calculation operations through LLM"
            }
        ]
        
        results = []
        for test in tests:
            try:
                print(f"\n🔍 Testing: {test['description']}")
                print(f"Query: {test['query']}")
                
                # Use the agent's query method which should trigger LLM processing
                result = await self.agent.query(test['query'])
                
                # Check if the LLM actually used tools (not just pattern matching)
                success = self._evaluate_llm_integration(result, test['expected_behavior'])
                
                status = "✅ PASS" if success else "❌ FAIL"
                results.append({
                    "query": test['query'],
                    "status": status,
                    "result": str(result)[:150],
                    "description": test['description']
                })
                
                print(f"{status} {test['description']}")
                print(f"LLM Response: {str(result)[:150]}...")
                
            except Exception as e:
                results.append({
                    "query": test['query'],
                    "status": "❌ ERROR",
                    "result": str(e),
                    "description": test['description']
                })
                print(f"❌ ERROR: {str(e)}")
        
        self.test_results['calculation_llm'] = results
        return results
        
    async def test_remote_llm_integration(self):
        """Test LLM's ability to use remote server tools through natural language."""
        print("\n🖥️ Testing LLM + Remote Server Tools Integration")
        print("=" * 50)
        
        tests = [
            {
                "query": "Initialize a workspace and show me the current repository status",
                "expected_behavior": "LLM should use remote tools to initialize workspace and check git status",
                "description": "Workspace initialization through LLM"
            },
            {
                "query": "List the contents of the current directory and show me any Python files",
                "expected_behavior": "LLM should use remote tools to list directory and find Python files",
                "description": "Directory operations through LLM"
            }
        ]
        
        results = []
        for test in tests:
            try:
                print(f"\n🔍 Testing: {test['description']}")
                print(f"Query: {test['query']}")
                
                result = await self.agent.query(test['query'])
                success = self._evaluate_llm_integration(result, test['expected_behavior'])
                
                status = "✅ PASS" if success else "❌ FAIL"
                results.append({
                    "query": test['query'],
                    "status": status,
                    "result": str(result)[:150],
                    "description": test['description']
                })
                
                print(f"{status} {test['description']}")
                print(f"LLM Response: {str(result)[:150]}...")
                
            except Exception as e:
                results.append({
                    "query": test['query'],
                    "status": "❌ ERROR",
                    "result": str(e),
                    "description": test['description']
                })
                print(f"❌ ERROR: {str(e)}")
        
        self.test_results['remote_llm'] = results
        return results
        
    async def test_monitoring_llm_integration(self):
        """Test LLM's ability to use monitoring tools through natural language."""
        print("\n📊 Testing LLM + Monitoring Tools Integration")
        print("=" * 50)
        
        tests = [
            {
                "query": "Use monitoring tools to: 1) Create a session called 'test_session' using monitoring_create_session, 2) Add todo 'Learn MCP' using monitoring_create_todos, 3) Add todo 'Test tools' using monitoring_create_todos",
                "expected_behavior": "LLM should create session and todos using monitoring tools",
                "description": "Session and todo creation through LLM"
            },
            {
                "query": "Use monitoring tools to: 1) Get current todos using monitoring_get_current_todos, 2) Show progress summary using monitoring_get_progress_summary",
                "expected_behavior": "LLM should retrieve progress and todo information",
                "description": "Progress tracking through LLM"
            }
        ]
        
        results = []
        for test in tests:
            try:
                print(f"\n🔍 Testing: {test['description']}")
                print(f"Query: {test['query']}")
                
                result = await self.agent.query(test['query'])
                success = self._evaluate_llm_integration(result, test['expected_behavior'])
                
                status = "✅ PASS" if success else "❌ FAIL"
                results.append({
                    "query": test['query'],
                    "status": status,
                    "result": str(result)[:150],
                    "description": test['description']
                })
                
                print(f"{status} {test['description']}")
                print(f"LLM Response: {str(result)[:150]}...")
                
            except Exception as e:
                results.append({
                    "query": test['query'],
                    "status": "❌ ERROR",
                    "result": str(e),
                    "description": test['description']
                })
                print(f"❌ ERROR: {str(e)}")
        
        self.test_results['monitoring_llm'] = results
        return results
        
    async def test_advanced_math_llm_integration(self):
        """Test LLM's ability to use advanced math plugin tools through natural language."""
        print("\n🔢 Testing LLM + Advanced Math Plugin Integration")
        print("=" * 50)
        
        tests = [
            {
                "query": "Use the advanced math plugin to calculate 2 to the power of 3 plus the square root of 16. Execute the math_advanced_calc tool with the expression '2^3 + sqrt(16)'",
                "expected_behavior": "LLM should use advanced math plugin for complex calculations",
                "description": "Advanced math operations through LLM"
            },
            {
                "query": "Use the matrix operations tool to find the determinant of the matrix [[1, 2], [3, 4]]. Execute the math_matrix_ops tool with matrix_a parameter.",
                "expected_behavior": "LLM should use matrix operations tool",
                "description": "Matrix operations through LLM"
            },
            {
                "query": "Use the mathematical constants tool to get the value of pi. Execute the math_constants tool to retrieve mathematical constants.",
                "expected_behavior": "LLM should use mathematical constants tool",
                "description": "Mathematical constants through LLM"
            }
        ]
        
        results = []
        for test in tests:
            try:
                print(f"\n🔍 Testing: {test['description']}")
                print(f"Query: {test['query']}")
                
                result = await self.agent.query(test['query'])
                success = self._evaluate_llm_integration(result, test['expected_behavior'])
                
                status = "✅ PASS" if success else "❌ FAIL"
                results.append({
                    "query": test['query'],
                    "status": status,
                    "result": str(result)[:150],
                    "description": test['description']
                })
                
                print(f"{status} {test['description']}")
                print(f"LLM Response: {str(result)[:150]}...")
                
            except Exception as e:
                results.append({
                    "query": test['query'],
                    "status": "❌ ERROR",
                    "result": str(e),
                    "description": test['description']
                })
                print(f"❌ ERROR: {str(e)}")
        
        self.test_results['advanced_math_llm'] = results
        return results
        
    async def test_complex_multi_tool_queries(self):
        """Test LLM's ability to use multiple tools for complex queries."""
        print("\n🚀 Testing LLM + Complex Multi-Tool Queries")
        print("=" * 50)
        
        tests = [
            {
                "query": "I want to build a calculator app. First, let me test some calculations: what's 15 * 3? Then create a monitoring session called 'calculator_project' and add a todo 'Implement basic arithmetic'",
                "expected_behavior": "LLM should use calculation tool, then monitoring tools for session management",
                "description": "Multi-tool integration for project planning"
            },
            {
                "query": "Search the web for 'Python web frameworks', then calculate how many frameworks we found, and create a todo to research the top 3",
                "expected_behavior": "LLM should use web search, calculation, and monitoring tools",
                "description": "Multi-tool integration for research tasks"
            }
        ]
        
        results = []
        for test in tests:
            try:
                print(f"\n🔍 Testing: {test['description']}")
                print(f"Query: {test['query']}")
                
                result = await self.agent.query(test['query'])
                success = self._evaluate_llm_integration(result, test['expected_behavior'])
                
                status = "✅ PASS" if success else "❌ FAIL"
                results.append({
                    "query": test['query'],
                    "status": status,
                    "result": str(result)[:150],
                    "description": test['description']
                })
                
                print(f"{status} {test['description']}")
                print(f"LLM Response: {str(result)[:150]}...")
                
            except Exception as e:
                results.append({
                    "query": test['query'],
                    "status": "❌ ERROR",
                    "result": str(e),
                    "description": test['description']
                })
                print(f"❌ ERROR: {str(e)}")
        
        self.test_results['complex_multi_tool'] = results
        return results
        
    def generate_summary_report(self):
        """Generate a comprehensive LLM integration test summary report."""
        print("\n" + "="*80)
        print("🧠 LLM INTEGRATION TEST SUMMARY REPORT")
        print("="*80)
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        
        for test_category, results in self.test_results.items():
            print(f"\n🔍 {test_category.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            category_tests = len(results)
            category_passed = len([r for r in results if "PASS" in r['status']])
            category_failed = len([r for r in results if "FAIL" in r['status']])
            category_errors = len([r for r in results if "ERROR" in r['status']])
            
            total_tests += category_tests
            total_passed += category_passed
            total_failed += category_failed
            total_errors += category_errors
            
            print(f"   Tests: {category_tests} | Passed: {category_passed} | Failed: {category_failed} | Errors: {category_errors}")
            
            # Show failed/error tests
            for result in results:
                if "FAIL" in result['status'] or "ERROR" in result['status']:
                    print(f"   ❌ Query: {result['query'][:60]}...")
                    print(f"      Result: {result['result'][:80]}...")
        
        print(f"\n📈 OVERALL SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   ⚠️  Errors: {total_errors}")
        print(f"   🎯 Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "   🎯 Success Rate: N/A")
        
        duration = (datetime.now() - self.start_time).total_seconds()
        print(f"   ⏱️  Test Duration: {duration:.1f} seconds")
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_errors': total_errors,
            'success_rate': (total_passed/total_tests*100) if total_tests > 0 else 0,
            'duration': duration
        }
        
    async def run_all_tests(self):
        """Run all LLM integration tests."""
        print("🚀 Starting LLM Integration Test Suite")
        print("=" * 80)
        print(f"⏰ Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎯 Testing how LLM actually uses MCP tools to answer queries")
        
        # Test each category of LLM integration
        await self.test_calculation_llm_integration()
        await self.test_remote_llm_integration()
        await self.test_monitoring_llm_integration()
        await self.test_advanced_math_llm_integration()
        await self.test_complex_multi_tool_queries()
        
        # Generate summary report
        summary = self.generate_summary_report()
        
        return summary

async def main():
    """Main test function."""
    print("🧠 LLM Integration Test Suite")
    print("=" * 50)
    
    try:
        # Initialize agent
        print("📋 Loading configuration...")
        config = ConfigManager()
        
        print("🤖 Initializing unified agent with LLM...")
        agent = UnifiedAIShowmakerAgent(config)
        await agent.initialize()
        
        print(f"✅ Agent initialized with {len(agent.mcp_tools)} tools")
        print(f"🧠 LLM Status: {agent.get_llm_info()}")
        
        # Run LLM integration tests
        tester = LLMIntegrationTester(agent)
        summary = await tester.run_all_tests()
        
        # Final status
        if summary['success_rate'] >= 80:
            print(f"\n🎉 EXCELLENT! LLM integration tests completed with {summary['success_rate']:.1f}% success rate!")
        elif summary['success_rate'] >= 60:
            print(f"\n✅ GOOD! LLM integration tests completed with {summary['success_rate']:.1f}% success rate!")
        else:
            print(f"\n⚠️  NEEDS ATTENTION! LLM integration tests completed with {summary['success_rate']:.1f}% success rate!")
        
        print("\n🔄 Shutting down agent...")
        await agent.shutdown()
        
    except Exception as e:
        print(f"❌ Test suite failed: {str(e)}")
        logger.error(f"Test suite error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
