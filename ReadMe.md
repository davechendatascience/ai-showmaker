# AI-Showmaker

A TypeScript-based AI agent framework that integrates with MCP (Model Context Protocol) servers and LangChain for intelligent task execution.

## 🏗️ Architecture

### Core Components

- **LangGraph MCP Agent** (`src/agents/langgraph-mcp-agent.ts`) - Main agent that handles complex task orchestration
- **HTTP MCP Client** (`src/mcp/http-mcp-client.ts`) - Communicates with Python MCP servers via HTTP
- **Rate-Limited LLM** (`src/llm/rate-limited-llm.ts`) - Inference.net LLM with rate limiting
- **Session Manager** (`src/core/session-manager.ts`) - Manages conversation context and history

### Key Features

✅ **Simple Query Input** - Just provide the initial task, no complex instructions  
✅ **LangGraph Workflow** - Automatic tool selection and orchestration  
✅ **MCP Integration** - 39 tools available from Python servers  
✅ **Session Management** - Conversation continuity and context  
✅ **Rate Limiting** - Handles API limits gracefully  
✅ **TypeScript** - Full type safety and modern development experience  

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Inference.net API key

### Setup

1. **Clone and install dependencies:**
   ```bash
   git clone <repository>
   cd ai-showmaker
   npm install
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your INFERENCE_NET_KEY
   ```

4. **Start the MCP bridge:**
   ```bash
   python full_mcp_bridge.py
   ```

5. **Run the agent:**
   ```bash
   npx ts-node tests/integration/test_langgraph_mcp_agent.ts
   ```

## 🧠 How It Works

### LangGraph MCP Agent

The core agent follows the **LangGraph workflow pattern**:

1. **Input**: Simple task query (e.g., "Solve LeetCode problem 1: Two Sum")
2. **Tool Discovery**: Automatically discovers 39 available MCP tools
3. **LLM Decision**: LLM decides which tools to use and when
4. **Tool Execution**: Executes tools via HTTP MCP bridge
5. **Response**: Provides natural language response with results

### Example Usage

```typescript
const agent = new LangGraphMCPAgent(mcpClient, llm, sessionManager);

// Simple task - LangGraph handles the rest
const result = await agent.executeComplexTask(
    "Help me solve a math problem: What is 15 * 23?", 
    sessionId
);
```

### Available Tools

The agent has access to 39 tools across 5 MCP servers:

- **Calculation Server**: Math operations, variable management
- **Development Server**: File operations, code execution
- **Web Search Server**: Web search capabilities
- **Remote Server**: Remote execution and monitoring
- **Monitoring Server**: System monitoring and logging

## 🧪 Testing

### Core Tests

- `test_langgraph_mcp_agent.ts` - Main agent functionality
- `test_agent_demo.ts` - Basic agent capabilities
- `test_mock_llm.ts` - Mock LLM testing
- `test_inference_net_direct.ts` - Direct LLM testing

### Python MCP Bridge Tests

- `test_all_servers.py` - All MCP servers
- `test_bridge_simple.py` - Basic bridge functionality
- `test_calculation_direct.py` - Calculation server

## 📁 Project Structure

```
src/
├── agents/
│   └── langgraph-mcp-agent.ts    # Main LangGraph agent
├── core/
│   ├── config.ts                 # Configuration management
│   └── session-manager.ts        # Session and context management
├── llm/
│   ├── inference-net-llm.ts      # Inference.net LLM integration
│   ├── mock-llm.ts              # Mock LLM for testing
│   └── rate-limited-llm.ts      # Rate-limited LLM wrapper
├── mcp/
│   └── http-mcp-client.ts       # HTTP MCP client
└── types/
    └── index.ts                 # TypeScript type definitions

tests/integration/               # Integration tests
mcp_servers/                    # Python MCP servers
full_mcp_bridge.py             # HTTP bridge to Python servers
```

## 🔧 Development

### Adding New Tools

1. Create a new MCP server in `mcp_servers/`
2. Register it in `full_mcp_bridge.py`
3. The agent automatically discovers new tools

### Adding New LLM Providers

1. Extend the base LLM class in `src/llm/`
2. Implement the required interface methods
3. Add rate limiting if needed

### Testing

```bash
# Run all TypeScript tests
npm test

# Run specific test
npx ts-node tests/integration/test_langgraph_mcp_agent.ts

# Run Python MCP tests
python tests/integration/test_all_servers.py
```

## 🎯 Core Principles

1. **Simple Input** - Just provide the task, let LangGraph handle the workflow
2. **MCP Integration** - Leverage Model Context Protocol for tool connectivity
3. **TypeScript First** - Full type safety and modern development
4. **Session Management** - Maintain context across conversations
5. **Rate Limiting** - Handle API limits gracefully

## 📊 Current Status

✅ **Working**: LangGraph MCP Agent with 39 tools  
✅ **Working**: Session management and conversation continuity  
✅ **Working**: Rate-limited LLM integration  
✅ **Working**: HTTP MCP bridge to Python servers  
✅ **Working**: TypeScript type safety and modern tooling  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

## Best‑First Search Agent + Validator (New Orchestration)

AI‑Showmaker now includes a Best‑First Search (BFS) policy+value agent orchestrated with a dedicated Validator agent. This pairing improves reliability by making validation an explicit, first‑class action that gates completion.

Key concepts

- Best‑First Search: Proposes high‑level actions (e.g., gather_info, extract_data, design, implement_code, test_example, synthesize_answer, validate) and explores them with a value function.
- Validation as action: The main agent injects `synthesize_answer` → `validate` when its plan value exceeds a threshold. Task success is gated on a validator pass (confidence ≥ minimum).
- Evidence gating: The agent delays validation until there is fresh evidence; when the validator requests tests, the agent first ensures self‑tests exist before re‑validating.
- Self‑tests (code tasks): Composer includes a fenced JSON block with cases plus a short walkthrough; the agent detects and logs tests presence for the validator.
- Dev/Ops checks (remote/web tasks): Composer includes concrete shell commands and verification steps (curl/systemctl/ss/firewall), and a rollback note. Validator requires these (won’t accept summaries alone).

Environment variables

- `BFS_VALIDATOR_MODE` (default: `action`): `action` | `periodic` | `both`
- `BFS_VALUE_TRIGGER` (default: `0.8`): Value threshold to schedule synthesize/validate
- `BFS_VALIDATION_COOLDOWN` (default: `2`): Iterations between validations
- `BFS_VALIDATOR_CONF` (default: `0.7`): Minimum validator confidence to accept completion
- `BFS_HINT_BOOST` (default: `0.35`): Score boost for plans matching validator suggestions
- `BFS_SPECIAL_HINT_BOOST` (default: `0.1`): Extra boost for `implement_code`/`test_example`
- `BFS_EXPLAIN_MAX` (default: `400`): Max chars for inline explanations
- `BFS_EXPLAIN_LOG_MAX` (default: `0`): Max chars printed for `[BFS] explain:` (0 = no truncation)

Logs to expect

- `[BFS] act:` chosen action and tool
- `[BFS] explain:` inline, evidence‑grounded step summary
- `[BFS] schedule:` injection of synthesize/validate (or test_example when tests are required)
- `[BFS] draft:` draft meta summary (code/lang, tests presence/cases, ops checks snippet)
- `[BFS][validator]` completion/confidence, rationale, and hints

Acceptance policies (validator)

- Code tasks: Require code + self‑tests (JSON cases + short walkthrough). Real execution is optional.
- Dev/Ops tasks: Require operational commands and verification steps; validator rejects high‑level summaries without checks.

Where it lives

- Main agent: `src/agents/best-first-search-agent.ts`
- Validator: `src/agents/validator-agent.ts`

Quick start with BFS agent

1. Set env vars as needed (e.g., `BFS_VALIDATOR_MODE=action`).
2. Run the app and issue tasks (coding or dev/ops).
3. Watch `[BFS] draft:` and `[BFS][validator]` logs to see evidence and decisions.
