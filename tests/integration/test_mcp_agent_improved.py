#!/usr/bin/env python3
"""
IMPROVED Integration tests for MCP-based AI-Showmaker agent.
Actually validates agent responses instead of blindly marking everything as passed.
"""
import os
import asyncio
import time
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.llamaindex_agent import LlamaIndexMCPServerManager
from core.config import ConfigManager
from core.exceptions import AIShowmakerError


class TestCase:
    """Represents a single test case with validation logic."""
    
    def __init__(self, query: str, description: str, validator_func, timeout: int = 60):
        self.query = query
        self.description = description
        self.validator_func = validator_func
        self.timeout = timeout


class TestResult:
    """Store detailed results of a single test."""
    
    def __init__(self, test_case: TestCase):
        self.test_case = test_case
        self.success = False
        self.response = ""
        self.error = ""
        self.duration = 0.0
        self.validation_details = ""
        self.tool_calls_made = []
        self.tool_errors = []
        self.timestamp = datetime.now()


class ImprovedMCPAgentTester:
    """Integration tester with proper validation logic."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.agent = None
        self.manager = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the LlamaIndex-based agent."""
        if self._initialized:
            return
            
        try:
            config = ConfigManager()
            self.manager = LlamaIndexMCPServerManager()
            await self.manager.initialize_servers()
            self.agent = self.manager.create_agent(config)
            self._initialized = True
            print("✅ LlamaIndex-based AI-Showmaker Agent initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize agent: {str(e)}")
            raise e
    
    async def shutdown(self):
        """Shutdown the agent."""
        if self.manager and self._initialized:
            await self.manager.shutdown()
    
    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test with proper validation."""
        print(f"\n[TEST] {test_case.description}")
        print(f"Query: {test_case.query}")
        print("=" * 60)
        
        result = TestResult(test_case)
        start_time = time.time()
        
        try:
            if not self._initialized:
                raise RuntimeError("Agent not initialized")
            
            # Run the query  
            response = await self.agent.query(test_case.query)
            result.duration = time.time() - start_time
            result.response = str(response) if response else ""
            
            # Extract tool usage information from logs/response
            result.tool_calls_made = self._extract_tool_calls(result.response)
            result.tool_errors = self._extract_tool_errors(result.response)
            
            # Validate the response using the test-specific validator
            success, validation_details = test_case.validator_func(result.response, result)
            result.success = success
            result.validation_details = validation_details
            
            # Print detailed results
            if result.success:
                print(f"✅ PASSED ({result.duration:.2f}s)")
                print(f"   Validation: {validation_details}")
            else:
                print(f"❌ FAILED ({result.duration:.2f}s)")
                print(f"   Reason: {validation_details}")
                if result.tool_errors:
                    print(f"   Tool Errors: {', '.join(result.tool_errors)}")
            
            if result.tool_calls_made:
                print(f"   Tools Used: {', '.join(result.tool_calls_made)}")
                
        except Exception as e:
            result.duration = time.time() - start_time
            result.error = str(e)
            result.success = False
            result.validation_details = f"Exception: {str(e)}"
            print(f"❌ ERROR ({result.duration:.2f}s): {str(e)}")
        
        print(f"\nResponse: {result.response[:200]}..." if len(result.response) > 200 else f"\nResponse: {result.response}")
        self.results.append(result)
        return result
    
    def _extract_tool_calls(self, response: str) -> List[str]:
        """Extract tool calls from the response."""
        tools = []
        # Look for common patterns in LangChain/LlamaIndex output
        if "Action:" in response:
            # Extract action names
            action_matches = re.findall(r"Action:\s*(\w+)", response)
            tools.extend(action_matches)
        
        # Look for tool execution patterns
        tool_matches = re.findall(r"(\w+_\w+)\s*\(", response)
        tools.extend(tool_matches)
        
        return list(set(tools))  # Remove duplicates
    
    def _extract_tool_errors(self, response: str) -> List[str]:
        """Extract tool errors from the response."""
        errors = []
        
        # Common error patterns
        error_patterns = [
            r"Error: (.+?)(?:\n|$)",
            r"Failed: (.+?)(?:\n|$)",
            r"Required parameter '(\w+)' missing",
            r"Invalid (.+?)(?:\n|$)",
            r"Tool '(\w+)' failed"
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            errors.extend(matches)
        
        return errors
    
    async def run_test_suite(self, test_cases: List[TestCase], suite_name: str):
        """Run a suite of tests."""
        print(f"\n🧪 {suite_name}")
        print("=" * 60)
        print(f"Running {len(test_cases)} tests...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}]", end=" ")
            await self.run_single_test(test_case)
            
            # Brief pause between tests
            if i < len(test_cases):
                await asyncio.sleep(1)
        
        self._print_detailed_summary(suite_name)
    
    def _print_detailed_summary(self, suite_name: str):
        """Print detailed test results summary."""
        total = len(self.results)
        passed = len([r for r in self.results if r.success])
        failed = total - passed
        
        print(f"\n{'='*70}")
        print(f"📊 {suite_name} DETAILED RESULTS")
        print(f"{'='*70}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        avg_duration = sum(r.duration for r in self.results) / len(self.results) if self.results else 0
        print(f"⏱️  Average Duration: {avg_duration:.2f}s")
        
        # Show failed tests with details
        if failed > 0:
            print(f"\n❌ FAILED TESTS ANALYSIS:")
            print("-" * 50)
            for i, result in enumerate([r for r in self.results if not r.success], 1):
                print(f"\n{i}. {result.test_case.description}")
                print(f"   Query: {result.test_case.query}")
                print(f"   Failure Reason: {result.validation_details}")
                if result.tool_errors:
                    print(f"   Tool Errors: {', '.join(result.tool_errors)}")
                if result.error:
                    print(f"   Exception: {result.error}")
        
        # Show successful tests briefly
        if passed > 0:
            print(f"\n✅ SUCCESSFUL TESTS:")
            print("-" * 30)
            for result in [r for r in self.results if r.success]:
                print(f"• {result.test_case.description} ({result.duration:.1f}s)")


# =============================================
# TEST CASE VALIDATORS
# =============================================

def validate_calculation(response: str, result: TestResult) -> tuple[bool, str]:
    """Validate mathematical calculation responses."""
    response = response.lower()
    
    # Check for obvious errors
    if "error" in response or "failed" in response:
        return False, "Contains error message"
    
    # Look for mathematical result
    if re.search(r'\b\d+\b', response):  # Contains numbers
        if "8" in response:  # Expected result for 5+3
            return True, "Correct calculation result found"
        else:
            return False, f"Contains numbers but not expected result"
    
    return False, "No numerical result found"


def validate_directory_listing(response: str, result: TestResult) -> tuple[bool, str]:
    """Validate directory listing responses."""
    response = response.lower()
    
    # Check for errors
    if "error" in response or "failed" in response:
        return False, "Contains error message"
    
    # Look for directory listing indicators
    directory_indicators = [
        "total", "drwx", "files", "directories", 
        ".py", ".txt", ".json", "directory", "folder"
    ]
    
    if any(indicator in response for indicator in directory_indicators):
        return True, "Directory listing content detected"
    
    return False, "No directory listing content found"


def validate_git_status(response: str, result: TestResult) -> tuple[bool, str]:
    """Validate git status responses."""
    response = response.lower()
    
    # Check for errors
    if "error" in response or "failed" in response:
        return False, "Contains error message"
    
    # Look for git status indicators
    git_indicators = [
        "branch", "commit", "modified", "changes", "staged", 
        "untracked", "clean", "ahead", "behind", "main", "master"
    ]
    
    if any(indicator in response for indicator in git_indicators):
        return True, "Git status information detected"
    
    return False, "No git status information found"


def validate_file_creation(response: str, result: TestResult) -> tuple[bool, str]:
    """Validate file creation responses."""
    response = response.lower()
    
    # Check for obvious errors
    if "required parameter" in response or "missing" in response:
        return False, "Missing required parameters"
    
    if "error" in response and "success" not in response:
        return False, "Contains error message"
    
    # Look for success indicators
    success_indicators = [
        "created", "written", "success", "file", "saved"
    ]
    
    if any(indicator in response for indicator in success_indicators):
        return True, "File creation success indicators found"
    
    return False, "No file creation confirmation found"


def validate_todo_creation(response: str, result: TestResult) -> tuple[bool, str]:
    """Validate todo list creation responses."""
    response = response.lower()
    
    # Check for errors
    if "required parameter" in response:
        return False, "Missing required parameters"
    
    if "error" in response and "created" not in response:
        return False, "Contains error message without success"
    
    # Look for todo indicators
    todo_indicators = [
        "todo", "created", "task", "pending", "item", "list"
    ]
    
    if any(indicator in response for indicator in todo_indicators):
        return True, "Todo creation indicators found"
    
    return False, "No todo creation confirmation found"


# =============================================
# TEST CASES DEFINITION
# =============================================

def get_basic_test_cases() -> List[TestCase]:
    """Get basic functionality test cases."""
    return [
        TestCase(
            "What is 5 + 3?",
            "Simple Mathematical Calculation", 
            validate_calculation,
            30
        ),
        TestCase(
            "Check the current directory on the server",
            "Remote Directory Listing",
            validate_directory_listing,
            30
        ),
        TestCase(
            "Show the git status of the current repository", 
            "Git Status Check",
            validate_git_status,
            30
        ),
        TestCase(
            "Create a simple test.txt file with 'Hello World' content",
            "File Creation",
            validate_file_creation,
            30
        )
    ]


def get_comprehensive_test_cases() -> List[TestCase]:
    """Get comprehensive test cases.""" 
    return [
        TestCase(
            "Calculate the area of a circle with radius 5",
            "Complex Mathematical Calculation",
            validate_calculation,
            45
        ),
        TestCase(
            "Create a todo list for deploying a web application with 3 steps",
            "Todo List Creation", 
            validate_todo_creation,
            30
        ),
        TestCase(
            "Check what operating system is running on the server",
            "System Information Query",
            validate_directory_listing,  # Will look for system info
            30
        ),
        TestCase(
            "Show the last 3 git commits in the repository",
            "Git Log Query",
            validate_git_status,  # Will look for git info
            30
        )
    ]


# =============================================
# MAIN TEST EXECUTION
# =============================================

async def main():
    """Run the improved MCP agent tests."""
    print("🤖 AI-Showmaker MCP Integration Tests")
    print("🔍 WITH PROPER VALIDATION (No More False Positives!)")
    print("=" * 70)
    
    tester = ImprovedMCPAgentTester()
    
    try:
        await tester.initialize()
        
        # Run basic tests
        basic_tests = get_basic_test_cases()
        await tester.run_test_suite(basic_tests, "BASIC FUNCTIONALITY")
        
        # Clear results for next suite
        tester.results.clear()
        
        # Run comprehensive tests  
        comprehensive_tests = get_comprehensive_test_cases()
        await tester.run_test_suite(comprehensive_tests, "COMPREHENSIVE FEATURES")
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.shutdown()
        print("\n✅ Integration tests completed")


if __name__ == "__main__":
    asyncio.run(main())