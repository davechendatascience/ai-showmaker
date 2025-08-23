"""
Enhanced test runner for AI-Showmaker agent with better structure and logging.
"""
import os
import json
import time
import sys
from datetime import datetime
from tools import *
from config import get_config
from test_queries import TEST_QUERIES, get_all_basic_tests, get_comprehensive_test_suite

# Load configuration
config = get_config()
os.environ["GOOGLE_API_KEY"] = config['google_api_key']
os.environ["AWS_HOST"] = config['aws_host']
os.environ["AWS_USER"] = config['aws_user'] 
os.environ["PEM_PATH"] = config['pem_path']

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import initialize_agent, AgentType

class TestResult:
    """Store results of a single test."""
    def __init__(self, query: str, success: bool = False, response: str = "", error: str = "", duration: float = 0.0):
        self.query = query
        self.success = success
        self.response = response
        self.error = error
        self.duration = duration
        self.timestamp = datetime.now()

class AgentTester:
    """Enhanced agent tester with better structure and reporting."""
    
    def __init__(self, interactive: bool = True, timeout: int = 60):
        self.interactive = interactive
        self.timeout = timeout
        self.results = []
        
        # Initialize agent
        self.tools = [
            Tool(
                name="Calculator", 
                func=calculator_tool, 
                description="Advanced mathematical calculator supporting arithmetic, trigonometry, logarithms, factorials, variables, and complex expressions. Use for any mathematical computation including scientific functions."
            ),
            Tool(
                name="RemoteCommand",
                func=smart_remote_command_tool,
                description="Execute commands on the remote server. Input: JSON string. For regular commands: '{{\"command\": \"ls -la\"}}'. For interactive programs that need user input: '{{\"command\": \"python3 script.py\", \"input_data\": \"input1\\\\ninput2\"}}'. Automatically handles both types."
            ),
            Tool(
                name="RemoteWriteFile",
                func=remote_sftp_write_file_tool,
                description="Write code/text files to the remote server via SFTP. Input: JSON string '{{\"filename\": \"file.py\", \"code\": \"content\"}}'. Includes security validation and directory creation."
            )
        ]
        
        system_message = "You are an expert assistant that tackles complex problems stepwise, calling tools when appropriate. Always provide clear explanations of your actions."
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}")
        ])
        
        chat = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        
        self.agent = initialize_agent(
            self.tools,
            chat,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
    
    def run_single_test(self, query: str) -> TestResult:
        """Run a single test query."""
        print(f"\n{'='*50}")
        print(f"TESTING: {query}")
        print(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            if self.interactive:
                response = self.human_in_the_loop(query)
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
    
    def human_in_the_loop(self, task_description: str, max_retries: int = 2):
        """Interactive testing with human feedback."""
        current_task = task_description
        
        for attempt in range(max_retries):
            try:
                response = self.agent.run(current_task)
                print(f"\n--- Agent Response ---")
                print(response)
                print(f"--- End Response ---\n")
                
                if self.interactive:
                    confirm = input("Is the task completed successfully? (y/n/q for quit): ").strip().lower()
                    if confirm == "q":
                        print("Test aborted by user.")
                        return None
                    elif confirm == "y":
                        print("✅ Task confirmed!")
                        return response
                    else:
                        feedback = input("What should be improved for the next attempt? ")
                        current_task = (
                            f"Previous task: {task_description}\n"
                            f"Previous attempt: {response}\n"
                            f"User feedback: {feedback}\n"
                            f"Please try again with improvements."
                        )
                else:
                    return response
                    
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
                return None
            except Exception as e:
                print(f"Error during attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise e
        
        print("Max retries reached.")
        return None
    
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

def main():
    """Main test execution function."""
    print("🤖 AI-Showmaker Agent Tester")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("\nAvailable test modes:")
        print("1. basic - Quick functionality test")
        print("2. comprehensive - Full feature test")
        print("3. interactive - Custom interactive testing")
        print("4. category [name] - Test specific category")
        
        mode = input("\nSelect test mode (1-4): ").strip()
    
    tester = AgentTester(interactive=True)
    
    if mode in ["1", "basic"]:
        tests = get_all_basic_tests()
        tester.run_test_suite(tests, "Basic Functionality")
        
    elif mode in ["2", "comprehensive"]:
        tests = get_comprehensive_test_suite()
        tester.run_test_suite(tests, "Comprehensive Feature")
        
    elif mode in ["3", "interactive"]:
        print("\n🎯 Interactive Testing Mode")
        print("Enter test queries (type 'quit' to exit):")
        
        while True:
            query = input("\nTest Query: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if query:
                tester.run_single_test(query)
        
        tester.print_summary("Interactive Session")
        
    elif mode.startswith("4") or mode.startswith("category"):
        category = input("Enter category name: ").strip()
        if category in TEST_QUERIES:
            tests = TEST_QUERIES[category]
            tester.run_test_suite(tests, f"Category: {category}")
        else:
            print(f"❌ Category '{category}' not found.")
            print("Available categories:", list(TEST_QUERIES.keys()))
    
    else:
        print(f"❌ Unknown mode: {mode}")

if __name__ == "__main__":
    main()