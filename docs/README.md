# AI-Showmaker Documentation

Welcome to the AI-Showmaker documentation! This guide will help you understand, use, and contribute to our revolutionary failure-aware AI agent system.

## 🎯 What is AI-Showmaker?

AI-Showmaker is a breakthrough AI agent framework that features **failure-aware planning**, **rich context memory**, and **automatic adaptation**. Unlike traditional agents that get stuck in infinite loops, our system learns from failures and completes complex tasks efficiently.

## 📚 Documentation Overview

### 🚀 Getting Started
- **[Main README](../ReadMe.md)** - Project overview, quick start, and key features
- **[Getting Started Guide](guides/GETTING_STARTED.md)** - Detailed setup and first steps
- **[Remote Development Policy](guides/REMOTE_DEV_POLICY.md)** - Guidelines for remote development

### 🧠 Core System Documentation
- **[Failure-Aware BFS System](FAILURE_AWARE_BFS.md)** - Comprehensive technical documentation of our breakthrough agent system
- **[Repository Structure](REPOSITORY_STRUCTURE.md)** - Project organization and file structure

### 🔧 Technical References
- **[MCP Servers API](api/MCP_SERVERS.md)** - Model Context Protocol server documentation
- **[Local Models Guide](LOCAL_MODELS_GUIDE.md)** - Using local LLM models

### 📖 Research & Design
- **[Resources Directory](../resources/)** - Research papers, design documents, and implementation guides
  - `perplexity_agent_memory_research.md` - Research on agent memory systems
  - `rich-context-bfs-integration-design.md` - Design documents for our memory system
  - `a-practical-guide-to-building-agents.pdf` - Comprehensive agent development guide

## 🎯 Key Features

### ✅ **Failure-Aware Planning**
- Detects known failure patterns (path traversal, admin commands, etc.)
- Automatically adapts plans to avoid detected risks
- Eliminates infinite loops and repetitive failures

### ✅ **Rich Context Memory**
- Multi-layered memory system (short-term buffer, long-term records, knowledge graph)
- Evidence tracking for file creation, code implementation, and synthesis
- Semantic indexing for intelligent memory queries

### ✅ **Validator Integration**
- Evidence-based validation with confidence scoring
- Actionable feedback for improvement
- Seamless integration with BFS planning

### ✅ **Proven Capabilities**
- **Simple Tasks**: "What is 2+2?" → Completes in 1 iteration
- **Complex Tasks**: "Develop webapp on remote server" → Adapts to constraints
- **Advanced Tasks**: "Real-time data analytics dashboard" → Builds 4-component system

## 🚀 Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd ai-showmaker
   npm install
   ```

2. **Start the MCP bridge**:
   ```bash
   python full_mcp_bridge.py
   ```

3. **Run the system**:
   ```bash
   npm run monitor:ui
   ```

4. **Try sample queries**:
   - Simple: `what is 2+2`
   - Complex: `develop a webapp on remote server amazon linux`
   - Advanced: `Create a real-time data analytics dashboard...`

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                Enhanced BFS Agent                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Plan          │  │   Failure       │  │   Validator  │ │
│  │   Generation    │  │   Awareness     │  │   Integration│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                Rich Memory Manager                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│  │   File      │ │   Code      │ │   Loop      │ │   Rich │ │
│  │   Registry  │ │   Doc       │ │   Prevention│ │   Types│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
src/
├── agents/
│   ├── enhanced-best-first-search-agent-with-memory-bank.ts  # Main agent
│   ├── enhanced-best-first-search-agent.ts                   # Alternative agent
│   └── validator-agent.ts                                    # Validation system
├── core/
│   ├── memory/                                               # Rich memory system
│   │   ├── rich-memory-manager.ts                           # Central manager
│   │   ├── file-registry.ts                                 # File tracking
│   │   ├── code-documentation.ts                            # Code analysis
│   │   ├── rich-completion-rules.ts                         # Completion logic
│   │   ├── rich-loop-prevention.ts                          # Loop detection
│   │   └── rich-memory-types.ts                             # Type definitions
│   ├── config.ts                                             # Configuration
│   └── session-manager.ts                                    # Session management
├── llm/                                                      # LLM integrations
├── mcp/                                                      # MCP client
└── types/                                                    # TypeScript types
```

## 🎯 Success Stories

### Simple Task: "What is 2+2?"
- **Before**: Would get confused by TypeScript context, create unnecessary files
- **After**: Creates simple answer file, validates completion in 1 iteration

### Complex Task: "Develop a webapp on remote server"
- **Before**: 20+ iterations trying `systemctl` commands (admin blocked)
- **After**: 3 iterations, adapts to `python -m http.server` (user-level)

### Advanced Task: "Real-time data analytics dashboard"
- **Before**: Would get stuck on complex multi-component requirements
- **After**: Successfully builds 4-component system (ingestion, processing, visualization, API)

## 🔧 Configuration

Key environment variables:
```bash
BFS_VALIDATOR_MODE=action          # Validation mode
BFS_VALUE_TRIGGER=0.8              # Value threshold for validation
BFS_VALIDATION_COOLDOWN=2          # Iterations between validations
BFS_VALIDATOR_CONF=0.7             # Minimum validator confidence
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

## 📞 Support

If you have questions or need help:
1. Check the [Getting Started Guide](guides/GETTING_STARTED.md)
2. Review the [Failure-Aware BFS documentation](FAILURE_AWARE_BFS.md)
3. Open an issue on GitHub

**Welcome to the future of AI agent development!** 🚀
