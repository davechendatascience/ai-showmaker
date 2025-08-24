#!/usr/bin/env python3
"""
Comprehensive Test Runner for AI-Showmaker Intelligent Task Planning System

Runs all tests including:
- Legacy MCP server tests
- Intelligent task planning tests
- LlamaIndex integration tests
- Output validation tests
- Integration tests
"""
import os
import sys
import asyncio
from pathlib import Path

# Set encoding first, before any imports
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def run_legacy_tests():
    """Run legacy MCP server tests."""
    print("🔧 Testing Legacy MCP Servers...")
    try:
        from tests.mcp.test_servers import main as test_servers
        result = await test_servers()
        if result == 0:
            print("✅ Legacy MCP Server tests passed")
            return True
        else:
            print("❌ Legacy MCP Server tests failed")
            return False
    except Exception as e:
        print(f"❌ Legacy MCP Server tests error: {e}")
        return False

async def run_todo_tests():
    """Run todo functionality tests."""
    print("📋 Testing Todo Functionality...")
    try:
        from tests.mcp.test_todo_fix import main as test_todo_fix
        result = await test_todo_fix()
        if result == 0:
            print("✅ Todo functionality tests passed")
            return True
        else:
            print("❌ Todo functionality tests failed")
            return False
    except Exception as e:
        print(f"❌ Todo functionality tests error: {e}")
        return False

async def run_intelligent_task_planning_tests():
    """Run intelligent task planning tests."""
    print("🧠 Testing Intelligent Task Planning...")
    try:
        import subprocess
        import sys
        
        # Run pytest for the intelligent task planning tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/integration/test_intelligent_task_planning.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        
        if result.returncode == 0:
            print("✅ Intelligent task planning tests passed")
            return True
        else:
            print(f"❌ Intelligent task planning tests failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Intelligent task planning tests error: {e}")
        return False

async def run_robust_task_planning_tests():
    """Run robust task planning tests."""
    print("🛡️ Testing Robust Task Planning...")
    try:
        import subprocess
        import sys
        
        # Run pytest for the robust task planning tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/integration/test_intelligent_task_planning_robust.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        
        if result.returncode == 0:
            print("✅ Robust task planning tests passed")
            return True
        else:
            print(f"❌ Robust task planning tests failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Robust task planning tests error: {e}")
        return False

async def run_enhanced_mcp_tests():
    """Run enhanced MCP integration tests."""
    print("🚀 Testing Enhanced MCP Integration...")
    try:
        import subprocess
        import sys
        
        # Run pytest for the enhanced MCP integration tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/integration/test_enhanced_mcp_integration.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        
        if result.returncode == 0:
            print("✅ Enhanced MCP integration tests passed")
            return True
        else:
            print(f"❌ Enhanced MCP integration tests failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Enhanced MCP integration tests error: {e}")
        return False

async def run_mcp_agent_improved_tests():
    """Run improved MCP agent tests."""
    print("🤖 Testing Improved MCP Agent...")
    try:
        import subprocess
        import sys
        
        # Run pytest for the improved MCP agent tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/integration/test_mcp_agent_improved.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        
        if result.returncode == 0:
            print("✅ Improved MCP agent tests passed")
            return True
        else:
            print(f"❌ Improved MCP agent tests failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Improved MCP agent tests error: {e}")
        return False

async def main():
    """Run all comprehensive tests."""
    print("🧪 Running AI-Showmaker Comprehensive Tests")
    print("=" * 60)
    print("Testing Intelligent Task Planning System with LlamaIndex Integration")
    print("=" * 60)
    
    results = []
    
    # Test 1: Legacy MCP Servers
    results.append(await run_legacy_tests())
    
    # Test 2: Todo Functionality
    results.append(await run_todo_tests())
    
    # Test 3: Intelligent Task Planning
    results.append(await run_intelligent_task_planning_tests())
    
    # Test 4: Robust Task Planning
    results.append(await run_robust_task_planning_tests())
    
    # Test 5: Enhanced MCP Integration
    results.append(await run_enhanced_mcp_tests())
    
    # Test 6: Improved MCP Agent
    results.append(await run_mcp_agent_improved_tests())
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary:")
    print(f"{'='*60}")
    
    test_names = [
        "Legacy MCP Servers",
        "Todo Functionality", 
        "Intelligent Task Planning",
        "Robust Task Planning",
        "Enhanced MCP Integration",
        "Improved MCP Agent"
    ]
    
    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1:2d}. {name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{len(results)} tests passed")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("✅ Intelligent Task Planning System is fully functional")
        print("✅ LlamaIndex Integration is working correctly")
        print("✅ Output Validation System is operational")
        print("✅ All MCP servers are functioning properly")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed")
        print("Please check the failed tests above for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
