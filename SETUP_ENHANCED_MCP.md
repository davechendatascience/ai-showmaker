# Enhanced MCP Integration Setup Guide

## Quick Start

### 1. Install Dependencies

**Option A: Automated Installation (Recommended)**
```bash
python install_dependencies.py
```

**Option B: Manual Installation**
```bash
# Install core dependencies
pip install langchain langchain-openai llama-index llama-index-llms-openai paramiko

# Install async dependencies
pip install aiohttp>=3.8.0 asyncio-mqtt>=0.11.0

# Install testing dependencies
pip install pytest>=7.0.0 pytest-asyncio>=0.21.0 pytest-cov>=4.0.0 pytest-mock>=3.10.0

# Install data handling dependencies
pip install pydantic>=2.0.0 jsonschema>=4.17.0

# Install logging dependencies
pip install structlog>=23.0.0
```

### 2. Verify Installation

Test that all dependencies are working:
```bash
python test_async_dependencies.py
```

### 3. Set Up Environment Variables

Create a `.env` file or set environment variables:
```bash
# Required
export INFERENCE_NET_KEY="your_api_key_here"
export INFERENCE_NET_MODEL="mistralai/mistral-nemo-12b-instruct/fp-8"
export INFERENCE_NET_BASE_URL="https://api.inference.net/v1"

# Optional
export LOG_LEVEL="INFO"
export TOOL_TIMEOUT="30"
```

### 4. Run the Demo

```bash
python demo_enhanced_mcp.py
```

### 5. Run Tests

```bash
# Run all integration tests
python -m pytest tests/integration/test_enhanced_mcp_integration.py -v

# Run with coverage
python -m pytest tests/integration/test_enhanced_mcp_integration.py -v --cov=core
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Error**: `ModuleNotFoundError: No module named 'aiohttp'`
**Solution**: Install async dependencies
```bash
pip install aiohttp>=3.8.0
```

#### 2. Pytest-AsyncIO Issues
**Error**: `pytest-asyncio not found`
**Solution**: Install pytest-asyncio
```bash
pip install pytest-asyncio>=0.21.0
```

#### 3. Pydantic Version Conflicts
**Error**: `ImportError: cannot import name 'BaseModel' from 'pydantic'`
**Solution**: Upgrade to Pydantic v2
```bash
pip install --upgrade pydantic>=2.0.0
```

#### 4. LlamaIndex Import Issues
**Error**: `ImportError: cannot import name 'FunctionTool' from 'llama_index.core.tools'`
**Solution**: Update LlamaIndex
```bash
pip install --upgrade llama-index llama-index-llms-openai
```

### Dependency Verification

Run the dependency test script to check all components:
```bash
python test_async_dependencies.py
```

Expected output:
```
🧪 Testing Enhanced MCP Integration Dependencies
============================================================

📋 Basic Async:
🔄 Testing basic async/await...
✅ Basic async/await works

📋 AIOHTTP:
✅ aiohttp imported successfully
✅ aiohttp HTTP request works

📋 Pytest-AsyncIO:
✅ pytest-asyncio imported successfully

📋 Pydantic:
✅ pydantic imported successfully
✅ pydantic model creation works: TestModel(name='test', value=42)

📋 JSONSchema:
✅ jsonschema imported successfully
✅ jsonschema validation works

📋 LlamaIndex:
✅ llama-index imported successfully

📋 Concurrent Futures:
✅ concurrent.futures imported successfully
✅ ThreadPoolExecutor works

============================================================
📊 Test Results Summary:
  Basic Async: ✅ PASS
  AIOHTTP: ✅ PASS
  Pytest-AsyncIO: ✅ PASS
  Pydantic: ✅ PASS
  JSONSchema: ✅ PASS
  LlamaIndex: ✅ PASS
  Concurrent Futures: ✅ PASS

🎯 Overall: 7/7 tests passed
🎉 All dependencies are working correctly!
```

## Usage Examples

### Basic Usage

```python
from core.enhanced_mcp_agent import EnhancedAIShowmakerAgent
from core.config import ConfigManager

# Initialize
config = ConfigManager()
agent = EnhancedAIShowmakerAgent(config)
await agent.initialize()

# Query the agent
result = await agent.query("Calculate the factorial of 5")
print(result)
```

### Advanced Usage

```python
# Get comprehensive tool information
tools_info = agent.get_tools_info()
for tool in tools_info:
    print(f"Tool: {tool['name']}")
    print(f"Server: {tool['server']}")
    print(f"Parameters: {tool['parameters']}")

# Get detailed statistics
stats = agent.get_statistics()
print(f"Total queries: {stats['agent_stats']['total_queries']}")
print(f"Success rate: {stats['agent_stats']['successful_queries']}/{stats['agent_stats']['total_queries']}")
```

## Development Setup

### 1. Clone and Setup
```bash
git clone <your-repo>
cd ai-showmaker
python install_dependencies.py
```

### 2. Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
python install_dependencies.py
```

### 3. Development Dependencies
```bash
# Install additional development tools
pip install black flake8 mypy pre-commit

# Setup pre-commit hooks
pre-commit install
```

## Performance Optimization

### 1. Async Configuration
The enhanced integration uses async/await for better performance. Ensure your environment supports it:

```python
# Check Python version (3.8+ required)
import sys
print(f"Python version: {sys.version}")

# Test async support
import asyncio
print("Async support: ✅")
```

### 2. Memory Management
The enhanced integration includes better memory management:

```python
# Clean shutdown
await agent.shutdown()

# Monitor memory usage
stats = agent.get_statistics()
print(f"Memory size: {stats['memory_size']} messages")
```

## Support

### Getting Help

1. **Check Dependencies**: Run `python test_async_dependencies.py`
2. **Check Logs**: Enable debug logging
3. **Run Tests**: `python -m pytest tests/integration/ -v`
4. **Check Documentation**: See `docs/ENHANCED_MCP_INTEGRATION.md`

### Debug Mode

Enable debug logging for troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("ai_showmaker.enhanced_llamaindex_agent").setLevel(logging.DEBUG)
```

---

For more information, see the [Enhanced MCP Integration Documentation](docs/ENHANCED_MCP_INTEGRATION.md).
