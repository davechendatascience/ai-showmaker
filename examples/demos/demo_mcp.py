"""
Demo script for MCP-based AI-Showmaker agent.
Shows how to use the new MCP-inspired architecture with human-in-the-loop feedback.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from core.agent import AIShowmakerAgent
from core.config import ConfigManager
from core.exceptions import AIShowmakerError


async def demo_basic_functionality():
    """Demo basic functionality of all MCP servers."""
    print("🤖 AI-Showmaker MCP Demo")
    print("=" * 40)
    
    # Initialize agent
    config = ConfigManager()
    agent = AIShowmakerAgent(config)
    
    try:
        await agent.initialize()
        print("✅ Agent initialized with MCP servers!")
        
        # Show available servers
        stats = await agent._get_server_stats()
        print("\n📋 Available MCP Servers:")
        for server_name, server_info in stats.items():
            print(f"  • {server_name.title()}: {server_info['tool_count']} tools")
        
        # Demo queries for each server
        demo_queries = [
            "Calculate the square root of 256 plus factorial of 4",  # Calculation server
            "Show the git status of this repository",               # Development server
            "Check what files are in the current directory on the remote server",  # Remote server
            "Create a todo list for setting up a new web application",  # Monitoring server
        ]
        
        print(f"\n🎯 Running {len(demo_queries)} demo queries...")
        
        for i, query in enumerate(demo_queries, 1):
            print(f"\n[Demo {i}/{len(demo_queries)}] {query}")
            try:
                result = agent.run(query)
                print(f"✅ Result: {result[:100]}{'...' if len(result) > 100 else ''}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print(f"\n{'='*50}")
        print("🎉 Demo completed! All MCP servers working!")
        
    except AIShowmakerError as e:
        print(f"❌ Demo failed: {str(e)}")
        return 1
    finally:
        await agent.shutdown()
        print("✅ Demo shutdown complete")
    
    return 0


async def interactive_demo():
    """Interactive demo with human-in-the-loop."""
    print("🎯 Interactive MCP Demo")
    print("=" * 30)
    
    config = ConfigManager()
    agent = AIShowmakerAgent(config)
    
    try:
        await agent.initialize()
        print("✅ Agent ready for interactive demo!")
        
        print("\n💡 Try these example queries:")
        print("  • 'Calculate compound interest for $1000 at 5% for 3 years'")
        print("  • 'Create a Python hello world script and deploy it to the server'")
        print("  • 'Show git status and create a todo list for my next commit'")
        print("  • 'Find all Python files and create a summary report'")
        
        while True:
            try:
                query = input("\n🤖 Your query (or 'quit' to exit): ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if query:
                    print(f"\n{'='*60}")
                    result = agent.human_in_the_loop(query)
                    if result is None:
                        print("❌ Task cancelled or failed")
                    else:
                        print("✅ Task completed successfully!")
                        
            except KeyboardInterrupt:
                print("\n👋 Demo interrupted")
                break
    
    except AIShowmakerError as e:
        print(f"❌ Interactive demo failed: {str(e)}")
        return 1
    finally:
        await agent.shutdown()
        print("✅ Interactive demo complete")
    
    return 0


async def main():
    """Main demo function."""
    print("AI-Showmaker MCP Demo Options:")
    print("1. Basic functionality demo")
    print("2. Interactive demo with human-in-the-loop")
    
    try:
        choice = input("\nSelect demo mode (1-2): ").strip()
        
        if choice == "1":
            return await demo_basic_functionality()
        elif choice == "2":
            return await interactive_demo()
        else:
            print("❌ Invalid choice")
            return 1
            
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)