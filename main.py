"""
AI-Showmaker Main Entry Point

Enhanced version using MCP-inspired architecture with multiple
specialized servers for different tool categories.
"""

import asyncio
import sys
import os
from pathlib import Path

# Set console encoding to UTF-8 for emoji support
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

import sys
sys.path.append('.')

from core.agent import AIShowmakerAgent
from core.config import ConfigManager  
from core.exceptions import AIShowmakerError


async def main():
    """Main application entry point."""
    try:
        # Initialize configuration
        print("Loading configuration...")
        config = ConfigManager()
        print(f"Configuration loaded successfully")
        
        # Initialize agent
        print("Initializing AI-Showmaker Agent...")
        agent = AIShowmakerAgent(config)
        await agent.initialize()
        print("Agent initialized successfully!")
        
        # Show available tools
        print("\nAvailable Tool Categories:")
        stats = await agent._get_server_stats()
        for server_name, server_info in stats.items():
            print(f"  • {server_name.title()}: {server_info['tool_count']} tools")
        
        print("\nAI-Showmaker Agent is ready!")
        print("=" * 50)
        
        # Example queries
        test_queries = [
            "What is the square root of 144 plus factorial of 5?",
            "Check what files are in the current directory on the remote server",
            "Show the git status of the current repository"
        ]
        
        print("Running example queries...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n[Example {i}] {query}")
            try:
                result = agent.run(query)
                print(f"Result: {result}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("All example queries completed!")
        
        # Interactive mode
        print("\nInteractive Mode (type 'quit' to exit):")
        while True:
            try:
                query = input("\nYour query: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if query:
                    result = agent.human_in_the_loop(query)
                    if result is None:
                        break
                        
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
        
        # Show final statistics
        stats = agent.get_statistics()
        print("\nFinal Statistics:")
        print(f"  • Total queries: {stats['agent_stats']['total_queries']}")
        print(f"  • Successful: {stats['agent_stats']['successful_queries']}")
        print(f"  • Failed: {stats['agent_stats']['failed_queries']}")
        print(f"  • Uptime: {stats['uptime_seconds']:.1f} seconds")
        
    except AIShowmakerError as e:
        print(f"AI-Showmaker Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return 1
    finally:
        if 'agent' in locals():
            print("\nShutting down servers...")
            await agent.shutdown()
            print("Shutdown complete")
    
    return 0


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)