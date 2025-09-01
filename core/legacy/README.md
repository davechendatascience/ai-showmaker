# Legacy Agent Files

This directory contains the previous agent implementations that have been replaced by the unified `core/agent.py`.

## Files

- **`reliable_mcp_agent.py`** - Reliable MCP agent with error handling and retry logic
- **`llamaindex_agent.py`** - Basic LlamaIndex-based agent implementation
- **`enhanced_mcp_agent.py`** - Enhanced MCP agent with advanced features
- **`intelligent_search_agent.py`** - Agent specialized for search operations
- **`intelligent_task_planner.py`** - Task planning and decomposition logic
- **`intelligent_reliable_agent.py`** - Combination of intelligent planning and reliability features

## Current Status

These files are kept for reference and potential future improvements. The current active implementation is in `core/agent.py` which consolidates the best features from these legacy implementations.

## Migration Notes

If you need to use any of these legacy agents, you can import them from `core.legacy.*`. However, it's recommended to use the unified agent in `core/agent.py` for new development.

## Features Preserved

The unified agent maintains:
- MCP server integration
- LLM support (Inference.net, Ollama, LlamaCpp)
- Tool discovery and execution
- Error handling and logging
- Configuration management
