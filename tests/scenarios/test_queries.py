"""
Test queries for the MCP-based AI-Showmaker agent.
Each test focuses on specific tool combinations and capabilities.
"""

# Test cases organized by complexity and MCP server usage
TEST_QUERIES = {
    
    # ===== CALCULATION SERVER TESTS =====
    "calculation_basic": [
        "What is 15 + 27?",
        "Calculate 2^10",
        "What's the square root of 144?",
    ],
    
    "calculation_advanced": [
        "Calculate sin(pi/4) * sqrt(2). Is the result close to 1?",
        "Set x = 25, then calculate x * 2 + sqrt(x)",
        "What's the factorial of 8 divided by factorial of 5?",
        "Find the greatest common divisor of 48 and 18",
    ],
    
    "calculation_complex": [
        "Calculate the compound interest: principal=1000, rate=5%, time=3 years, compounded annually",
        "Find the hypotenuse of a right triangle with sides 3 and 4, then calculate its area",
    ],
    
    # ===== REMOTE SERVER TESTS =====
    "remote_basic": [
        "Check what's in the home directory on the remote server",
        "What's the current date and time on the server?", 
        "Check the disk usage of the server",
        "Show the server's uptime and load average",
    ],
    
    "remote_system": [
        "Check what Python version is installed on the server",
        "List all running processes on the server",
        "Check the server's network interfaces and IP addresses", 
        "Show the server's memory usage",
    ],
    
    "remote_interactive": [
        "Create a Python script that asks for a name and age, then run it with sample inputs",
        "Make a greeting program that prompts for user input and run it interactively",
        "Create and run a simple quiz program with predefined answers",
    ],
    
    # ===== DEVELOPMENT SERVER TESTS =====
    "development_git": [
        "Show the git status of the current repository",
        "Display the last 5 commit messages",
        "Show what files have been modified since last commit",
    ],
    
    "development_files": [
        "Find all Python files in the project",
        "Search for the word 'MCP' in all project files",
        "List all files with 'test' in their name",
    ],
    
    # ===== MONITORING SERVER TESTS =====
    "monitoring_todos": [
        "Create a todo list for setting up a new development environment",
        "Show my current todo list",
        "Update the first todo item to completed status",
        "Get a progress summary of my current session",
    ],
    
    # ===== FILE WRITING TESTS =====
    "file_basic": [
        "Create a simple 'hello.py' file that prints 'Hello, World!' on the remote server",
        "Write a basic HTML page called 'index.html' with a welcome message",
        "Create a JSON configuration file with some sample data",
    ],
    
    "file_advanced": [
        "Create a Python script that calculates fibonacci numbers and save it as 'fibonacci.py'",
        "Write a shell script that checks system health and save it as 'health_check.sh'",
        "Create a simple web server script in Python that serves on port 8000",
    ],
    
    # ===== COMBINED MCP SERVER TESTS =====
    "combined_calc_remote": [
        "Calculate 2^8, then create a file called 'result.txt' with that number on the server",
        "Calculate the factorial of 6, then write a Python script that prints this number",
    ],
    
    "combined_dev_remote": [
        "Check git status, then create a deployment script based on what files are modified",
        "Find all Python files in the project, then create a summary file on the remote server",
    ],
    
    "combined_all_servers": [
        "Create a todo list for building a calculator app, then start implementing by creating the calculator script and deploying it",
        "Calculate optimal server settings for 100 users, create a config file, commit it to git, and deploy to remote server",
    ],
    
    # ===== REAL-WORLD MCP SCENARIOS =====
    "web_deployment": [
        "Create a todo list for web deployment, then build a simple blog website and deploy it to the server",
        "Set up a basic API server with health check endpoint and track progress with todos",
        "Deploy a static website with HTML, CSS, and basic JavaScript while tracking each step",
    ],
    
    "development_workflow": [
        "Create a complete Python project structure with proper git tracking and todo management",
        "Set up a development environment with all necessary files and track progress",
        "Create and deploy a monitoring script while maintaining a todo list for each step",
    ],
    
    # ===== ERROR HANDLING TESTS =====
    "error_scenarios": [
        "Try to calculate 1/0 and handle the error gracefully",
        "Attempt to create a file with an invalid path and see what happens",
        "Run a command that doesn't exist on the server",
        "Try to write to a protected system directory",
    ],
    
    # ===== SECURITY TESTS =====
    "security_validation": [
        "Try to create a file with path '../../../etc/passwd' (should be blocked)",
        "Attempt to write a file with .exe extension (should be blocked)", 
        "Try to run a potentially harmful command and see if it's handled safely",
    ],
}

# Test execution helpers
def get_test_by_category(category: str):
    """Get all tests for a specific category."""
    return TEST_QUERIES.get(category, [])

def get_all_basic_tests():
    """Get a quick set of basic tests to validate core MCP functionality."""
    return [
        "What is 5 + 3?",  # Calculation server
        "Check the current directory on the server",  # Remote server
        "Show the git status of the current repository",  # Development server
        "Create a simple test.txt file with 'Hello World' content",  # Remote file writing
    ]

def get_comprehensive_test_suite():
    """Get a comprehensive test covering all MCP server functionality."""
    return [
        # Calculation Server
        "Calculate the area of a circle with radius 5",
        
        # Remote Server - commands  
        "Check what operating system is running on the server",
        
        # Development Server - git
        "Show the last 3 git commits in the repository",
        
        # Remote Server - file operations
        "Create a Python script called 'greet.py' that asks for a name and greets the user",
        
        # Interactive commands
        "Create a greeting script and run it with the input 'Alice'",
        
        # Monitoring Server - todos
        "Create a todo list for deploying a web application with 3 steps",
        
        # Combined operations
        "Calculate 10! (factorial of 10), then create a file called 'factorial_result.txt' with that number and deploy it to the server",
        
        # Real-world scenario with multiple servers
        "Create a todo for building a calculator, then implement and deploy a simple interactive calculator script",
    ]

def get_mcp_server_tests():
    """Get tests that specifically validate each MCP server individually."""
    return {
        'calculation': TEST_QUERIES['calculation_basic'] + TEST_QUERIES['calculation_advanced'][:2],
        'remote': TEST_QUERIES['remote_basic'][:2] + TEST_QUERIES['file_basic'][:1],
        'development': TEST_QUERIES['development_git'][:2] + TEST_QUERIES['development_files'][:1],
        'monitoring': TEST_QUERIES['monitoring_todos'][:2]
    }

if __name__ == "__main__":
    print("Available test categories for MCP-based AI-Showmaker:")
    for category in TEST_QUERIES.keys():
        print(f"- {category}: {len(TEST_QUERIES[category])} tests")
    
    print(f"\nMCP Server-specific tests:")
    server_tests = get_mcp_server_tests()
    for server, tests in server_tests.items():
        print(f"- {server}: {len(tests)} tests")