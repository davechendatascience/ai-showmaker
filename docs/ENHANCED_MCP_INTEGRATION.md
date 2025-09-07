# Enhanced MCP Integration with LlamaIndex

## Overview

This document describes the enhanced integration between LlamaIndex and MCP (Model Context Protocol) servers in the AI-Showmaker project. The enhanced integration provides better tool management, improved error handling, and native protocol support.

## Key Improvements

### 1. Native MCP Protocol Support

The enhanced integration provides native support for MCP protocol features:

- **Enhanced Tool Metadata**: Rich metadata including parameters, categories, versions, and examples
- **Better Parameter Validation**: Comprehensive parameter validation with detailed error messages
- **Improved Error Handling**: Robust error handling with proper error propagation
- **Execution Statistics**: Detailed statistics for monitoring and debugging

### 2. Enhanced Tool Wrapper

The `MCPToolWrapper` class provides a bridge between MCP tools and LlamaIndex:

```python
class MCPToolWrapper:
    """Enhanced wrapper for MCP tools with better LlamaIndex integration."""
    
    def __init__(self, mcp_tool, server_name: str, server_instance):
        self.mcp_tool = mcp_tool
        self.server_name = server_name
        self.server_instance = server_instance
        self.metadata = self._create_metadata()
```

### 3. Enhanced Agent Architecture

The `EnhancedLlamaIndexAgent` provides:

- **Better Tool Registration**: Enhanced tool registration with metadata
- **Improved Function Calling**: Better function call parsing and execution
- **Enhanced System Prompts**: Detailed system prompts with tool information
- **Comprehensive Statistics**: Detailed execution statistics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced MCP Integration                 │
├─────────────────────────────────────────────────────────────┤
│  EnhancedLlamaIndexAgent                                    │
│  ├── MCPToolWrapper (per tool)                             │
│  ├── Enhanced Tool Registry                                │
│  ├── Enhanced System Prompts                               │
│  └── Comprehensive Statistics                              │
├─────────────────────────────────────────────────────────────┤
│  MCP Servers                                                │
│  ├── Calculation Server                                     │
│  ├── Remote Server                                          │
│  ├── Development Server                                     │
│  └── Monitoring Server                                      │
└─────────────────────────────────────────────────────────────┘
```

## Usage

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
    print(f"Category: {tool['category']}")
    print(f"Parameters: {tool['parameters']}")

# Get detailed statistics
stats = agent.get_statistics()
print(f"Total queries: {stats['agent_stats']['total_queries']}")
print(f"Success rate: {stats['agent_stats']['successful_queries']}/{stats['agent_stats']['total_queries']}")
print(f"Average response time: {stats['agent_stats']['avg_response_time']:.2f}s")
```

## Key Features

### 1. Enhanced Tool Metadata

Each MCP tool now includes rich metadata:

```python
@dataclass
class MCPToolMetadata:
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    category: str
    version: str
    timeout: int
    requires_auth: bool
    examples: List[Dict[str, Any]] = None
```

### 2. Enhanced Tool Results

Tool execution results include comprehensive information:

```python
@dataclass
class MCPToolResult:
    success: bool
    data: Any
    message: str
    execution_time: float
    tool_name: str
    server_name: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
```

### 3. Better Error Handling

The enhanced integration provides:

- **Parameter Validation**: Validates required parameters before execution
- **Timeout Handling**: Proper timeout handling for long-running operations
- **Error Recovery**: Graceful error recovery and reporting
- **Detailed Logging**: Comprehensive logging for debugging

### 4. Enhanced System Prompts

System prompts now include detailed tool information:

```
Available tools:
- calculation_calculate: Perform mathematical calculations
  Parameters:
    expression (string) (required): Mathematical expression to evaluate
    precision (integer): Number of decimal places for result

- remote_list_directory: List directory contents
  Parameters:
    path (string) (required): Directory path to list
    recursive (boolean): List subdirectories recursively
```

## Migration from Legacy Integration

### Before (Legacy)

```python
# Legacy approach
from core.llamaindex_agent import LlamaIndexAgent

agent = LlamaIndexAgent(config)
agent.set_mcp_servers(servers)
result = await agent.query("Calculate 5 + 3")
```

### After (Enhanced)

```python
# Enhanced approach
from core.enhanced_mcp_agent import EnhancedAIShowmakerAgent

agent = EnhancedAIShowmakerAgent(config)
await agent.initialize()
result = await agent.query("Calculate 5 + 3")

# Get enhanced statistics
stats = agent.get_statistics()
tools_info = agent.get_tools_info()
```

## Benefits

### 1. Better Performance

- **Optimized Tool Execution**: Better async/await integration
- **Reduced Latency**: Improved function call parsing
- **Better Resource Management**: Proper cleanup and shutdown

### 2. Enhanced Monitoring

- **Detailed Statistics**: Comprehensive execution statistics
- **Better Logging**: Enhanced logging for debugging
- **Performance Metrics**: Response time and success rate tracking

### 3. Improved Reliability

- **Better Error Handling**: Robust error handling and recovery
- **Parameter Validation**: Comprehensive parameter validation
- **Timeout Management**: Proper timeout handling

### 4. Enhanced Developer Experience

- **Rich Metadata**: Detailed tool information
- **Better Documentation**: Comprehensive tool descriptions
- **Easy Debugging**: Enhanced logging and error messages

## Configuration

### Environment Variables

```bash
# Required
INFERENCE_NET_KEY=your_api_key
INFERENCE_NET_MODEL=mistralai/mistral-nemo-12b-instruct/fp-8
INFERENCE_NET_BASE_URL=https://api.inference.net/v1

# Optional
LOG_LEVEL=INFO
TOOL_TIMEOUT=30
MAX_RETRIES=3
```

### Configuration File

```python
# config.py
config = {
    'inference_net_key': 'your_api_key',
    'inference_net_model': 'mistralai/mistral-nemo-12b-instruct/fp-8',
    'inference_net_base_url': 'https://api.inference.net/v1',
    'tool_timeout': 30,
    'max_retries': 3,
    'log_level': 'INFO'
}
```

## Testing

### Running the Demo

```bash
python demo_enhanced_mcp.py
```

### Running Tests

```bash
python -m pytest tests/integration/test_enhanced_mcp_integration.py -v
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all required packages are installed
   ```bash
   pip install llama-index llama-index-llms-openai
   ```

2. **Tool Registration Failures**: Check MCP server initialization
   ```python
   # Check server status
   server_stats = await agent._get_server_stats()
   print(server_stats)
   ```

3. **Function Call Parsing Issues**: Check LLM response format
   ```python
   # Enable debug logging
   logging.getLogger("ai_showmaker.enhanced_llamaindex_agent").setLevel(logging.DEBUG)
   ```

### Debug Mode

Enable debug mode for detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("ai_showmaker.enhanced_llamaindex_agent").setLevel(logging.DEBUG)
```

## Orchestration: Best‑First Search Agent + Validator

In addition to the enhanced MCP integration, AI‑Showmaker introduces a policy+value Best‑First Search (BFS) agent paired with a Validator agent. Validation becomes a first‑class action that gates completion, and the agent exposes evidence to the validator for reliable decisions.

Highlights

- Validation as action: The agent injects `synthesize_answer → validate` when plan value exceeds a threshold; success requires validator pass (confidence ≥ min).
- Evidence gating: The agent delays validation until fresh evidence exists; when validator requests tests, it generates/attaches self‑tests before re‑validating.
- Code tasks: Composer includes code + a fenced JSON cases block and a short walkthrough; validator accepts code + self‑tests without real execution.
- Dev/Ops tasks: Composer includes concrete shell commands and verification (curl/systemctl/ss) with a rollback note; validator rejects high‑level summaries alone.
- Observability: Logs include `[BFS] act`, `explain`, `schedule`, `draft` (code/tests/ops meta), and `[BFS][validator]` rationale.

See also

- Migration notes: `docs/MIGRATION_BFS_VALIDATOR.md`
- Remote dev/deploy policy: `docs/guides/REMOTE_DEV_POLICY.md`

## Future Enhancements

### Planned Features

1. **Streaming Support**: Real-time tool execution updates
2. **Tool Composition**: Combining multiple tools in workflows
3. **Advanced Caching**: Intelligent result caching
4. **Plugin System**: Extensible tool registration system

### Roadmap

- **Q1 2024**: Streaming support and advanced caching
- **Q2 2024**: Tool composition and workflow management
- **Q3 2024**: Plugin system and extensibility
- **Q4 2024**: Performance optimizations and monitoring

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Run tests: `python -m pytest tests/`

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add comprehensive docstrings
- Write unit tests for new features

### Pull Request Process

1. Create a feature branch
2. Implement changes with tests
3. Update documentation
4. Submit pull request with description

## Support

### Getting Help

- **Documentation**: Check this document and other docs in the `docs/` directory
- **Issues**: Report issues on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Community

- **GitHub**: https://github.com/your-repo/ai-showmaker
- **Discussions**: https://github.com/your-repo/ai-showmaker/discussions
- **Issues**: https://github.com/your-repo/ai-showmaker/issues

---

For more information, see the [main documentation](ReadMe.md), the BFS+Validator [migration notes](docs/MIGRATION_BFS_VALIDATOR.md), the [remote dev policy](docs/guides/REMOTE_DEV_POLICY.md), and the [API reference](docs/api/).
