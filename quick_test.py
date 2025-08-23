"""
Quick manual testing script for AI-Showmaker agent.
Simple approach without complex frameworks.
"""

# List of test queries organized by tool
QUICK_TESTS = {
    "Calculator Tests": [
        "What is 12 + 8?",
        "Calculate 2 to the power of 8",
        "Find the square root of 81",
        "What's sin(pi/2)?",
        "Set x = 15, then calculate x * 3",
    ],
    
    "Remote Command Tests": [
        "Check what directory we're in on the server",
        "What's the current date on the server?", 
        "List files in the home directory",
        "Check server uptime",
    ],
    
    "File Writing Tests": [
        "Create a simple hello.py file that prints hello world",
        "Write a basic HTML page called test.html",
        "Create a JSON config file with sample settings",
    ],
    
    "Combined Tests": [
        "Calculate 5 factorial, then create a file result.txt with that number",
        "Create a Python script that prints the current time, then deploy it to the server",
        "Make a simple calculator web page with HTML and deploy it",
    ]
}

def print_test_menu():
    """Print available test categories."""
    print("\n=== AI-Showmaker Quick Tests ===")
    print("Available test categories:")
    for i, category in enumerate(QUICK_TESTS.keys(), 1):
        count = len(QUICK_TESTS[category])
        print(f"{i}. {category} ({count} tests)")
    print("5. Custom query")
    print("0. Exit")

def show_tests(category):
    """Show tests in a category."""
    tests = QUICK_TESTS[category]
    print(f"\n--- {category} ---")
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test}")
    print("0. Back to menu")
    
    while True:
        try:
            choice = int(input("\nSelect test (0 to go back): "))
            if choice == 0:
                return None
            elif 1 <= choice <= len(tests):
                return tests[choice - 1]
            else:
                print("Invalid choice!")
        except ValueError:
            print("Please enter a number!")

def main():
    """Main testing interface."""
    print("🤖 AI-Showmaker Quick Tester")
    print("Use this to manually test queries with agent_demo.py")
    print("\nInstructions:")
    print("1. Choose a test category")
    print("2. Copy the test query") 
    print("3. Run: python agent_demo.py")
    print("4. Paste the query when prompted")
    
    while True:
        print_test_menu()
        
        try:
            choice = int(input("\nEnter choice: "))
            
            if choice == 0:
                print("Goodbye! 👋")
                break
                
            elif choice == 5:
                query = input("Enter your custom query: ").strip()
                if query:
                    print(f"\n📋 Your test query:")
                    print(f"'{query}'")
                    print(f"\nCopy this and run: python agent_demo.py")
                
            elif 1 <= choice <= 4:
                categories = list(QUICK_TESTS.keys())
                selected_category = categories[choice - 1]
                
                query = show_tests(selected_category)
                if query:
                    print(f"\n📋 Selected test query:")
                    print(f"'{query}'")
                    print(f"\nCopy this and run: python agent_demo.py")
                    input("Press Enter to continue...")
            
            else:
                print("Invalid choice!")
                
        except ValueError:
            print("Please enter a number!")
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break

if __name__ == "__main__":
    main()