# Repository Structure

## 🗂️ Current Structure Overview

```
ai-showmaker/
├── 📁 src/                   # ✅ ACTIVE - TypeScript source code
│   ├── agents/               # ✅ ACTIVE - AI agents (BFS, Validator)
│   ├── core/                 # ✅ ACTIVE - Core systems & memory
│   │   └── memory/           # ✅ ACTIVE - Rich context memory system
│   ├── llm/                  # ✅ ACTIVE - LLM integrations
│   ├── mcp/                  # ✅ ACTIVE - MCP client
│   └── types/                # ✅ ACTIVE - TypeScript definitions
├── 📁 mcp_servers/           # ✅ ACTIVE - Python MCP servers
├── 📁 tests/                 # ✅ ACTIVE - Test suite
├── 📁 docs/                  # ✅ ACTIVE - Documentation
├── 📁 resources/             # ✅ ACTIVE - Research & design docs
├── 📁 monitoring/            # ✅ ACTIVE - Monitoring UI
├── 📁 scripts/               # ✅ ACTIVE - Utility scripts
├── 📁 secrets/               # ✅ ACTIVE - SSH keys & API credentials
├── 📁 config/                # ⚠️ EMPTY - Future configuration files
├── 📁 deployment/            # ⚠️ EMPTY - Future Docker/infrastructure  
├── 📁 venv/                  # ✅ ACTIVE - Python virtual environment
└── 📄 main files             # ✅ ACTIVE - Entry points & configs
```

## 🎯 Active Components

### 🧠 **AI Agents** (`src/agents/`)
- **`enhanced-best-first-search-agent-with-memory-bank.ts`** - Main failure-aware BFS agent
- **`enhanced-best-first-search-agent.ts`** - Alternative BFS agent implementation
- **`validator-agent.ts`** - Evidence-based validation system

### 🧠 **Rich Memory System** (`src/core/memory/`)
- **`rich-memory-manager.ts`** - Central memory orchestration
- **`file-registry.ts`** - File operation tracking and metadata
- **`code-documentation.ts`** - Code analysis and documentation extraction
- **`rich-completion-rules.ts`** - Evidence-based completion validation
- **`rich-loop-prevention.ts`** - Loop detection and prevention
- **`rich-memory-types.ts`** - TypeScript type definitions

### 🔧 **Core Systems** (`src/core/`)
- **`config.ts`** - Configuration management
- **`session-manager.ts`** - Session and context management

### 🤖 **LLM Integrations** (`src/llm/`)
- **`openai-llm.ts`** - OpenAI API integration
- **`inference-net-llm.ts`** - Inference.net integration
- **`rate-limited-llm.ts`** - Rate limiting wrapper
- **`mock-llm.ts`** - Mock LLM for testing

### 🌐 **MCP Integration** (`src/mcp/`)
- **`http-mcp-client.ts`** - HTTP client for Python MCP servers

### 🐍 **Python MCP Servers** (`mcp_servers/`)
- **`calculation/`** - Math operations and calculations
- **`monitoring/`** - System monitoring and logging
- **`remote/`** - Remote execution capabilities
- **`websearch/`** - Web search functionality

### 📊 **Monitoring** (`monitoring/`)
- **`ui/`** - Web-based monitoring interface
- **`server.js`** - Monitoring server

### 📚 **Documentation** (`docs/`)
- **`README.md`** - Documentation index
- **`FAILURE_AWARE_BFS.md`** - Technical system documentation
- **`guides/`** - Getting started and development guides
- **`api/`** - API documentation

### 🔬 **Research** (`resources/`)
- **`perplexity_agent_memory_research.md`** - Memory system research
- **`rich-context-bfs-integration-design.md`** - System design documents
- **`a-practical-guide-to-building-agents.pdf`** - Agent development guide

## 📂 Empty Folders - Purpose & Future Plans

### 🐳 `deployment/` 
**Status**: Empty - Ready for Infrastructure  
**Purpose**: Container and infrastructure automation
**Planned Contents**:
```
deployment/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
└── terraform/
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```
**Use Case**: Production deployment automation

### ⚙️ `config/`
**Status**: Empty - Structured Configuration  
**Purpose**: Complex configuration management
**Planned Contents**:
```
config/
├── environments/
│   ├── development.yaml
│   ├── staging.yaml  
│   └── production.yaml
├── server_configs/
│   ├── calculation_server.yaml
│   └── remote_server.yaml
└── templates/
    └── config_template.yaml
```
**Use Case**: Environment-specific configurations

### 📚 `examples/`
**Status**: Empty - User Examples  
**Purpose**: Practical usage demonstrations
**Planned Contents**:
```
examples/
├── basic_usage/
│   ├── simple_calculator.py
│   └── remote_commands.py
├── advanced_workflows/
│   ├── ci_cd_pipeline.py
│   └── multi_server_tasks.py
└── integration_examples/
    ├── webhook_handler.py
    └── slack_bot.py
```
**Use Case**: Learning and onboarding

### 📊 `monitoring/`
**Status**: Empty - System Observability  
**Purpose**: Production monitoring and metrics
**Planned Contents**:
```
monitoring/
├── prometheus/
│   └── metrics.py
├── grafana/
│   └── dashboards.json
├── logs/
│   └── log_config.yaml
└── health_checks/
    └── endpoint_monitoring.py
```
**Use Case**: Production observability

### 🔧 `scripts/`
**Status**: Empty - Automation Scripts  
**Purpose**: Development and operational automation
**Planned Contents**:
```
scripts/
├── setup/
│   ├── install_dependencies.sh
│   └── configure_environment.py
├── maintenance/
│   ├── backup_configs.py
│   └── rotate_logs.sh
└── deployment/
    ├── deploy.sh
    └── rollback.sh
```
**Use Case**: DevOps automation

### 🛠️ `utils/`
**Status**: Empty - Shared Utilities  
**Purpose**: Common utility functions
**Planned Contents**:
```
utils/
├── file_operations.py
├── string_helpers.py
├── date_time.py
├── encryption.py
└── validation.py
```
**Use Case**: Shared functionality across servers

### 🗂️ `tools/` (Legacy)
**Status**: Empty - Post-Refactoring  
**Purpose**: Legacy structure from pre-MCP architecture
**Original Structure**:
```
tools/           # OLD - Before MCP refactoring
├── calculation/ # Moved to mcp_servers/calculation/
├── remote/      # Moved to mcp_servers/remote/
├── development/ # Moved to mcp_servers/development/
└── monitoring/  # Moved to mcp_servers/monitoring/
```
**Action Needed**: Can be safely removed as functionality moved to `mcp_servers/`

## 🎯 Priority for Population

### High Priority (Next Sprint)
1. **`examples/`** - Critical for user adoption
2. **`deployment/docker/`** - Enable containerization
3. **Clean up `tools/`** - Remove legacy structure

### Medium Priority  
4. **`config/environments/`** - Multi-environment support
5. **`scripts/setup/`** - Installation automation
6. **`utils/`** - Shared utilities as needed

### Low Priority
7. **`monitoring/`** - Production observability
8. **`deployment/terraform/`** - Infrastructure as code

## 📋 Folder Management Recommendations

### ✅ Keep As-Is
- `core/`, `mcp_servers/`, `tests/`, `docs/` - Core functionality
- `secrets/`, `venv/` - Essential infrastructure

### 🔄 Populate Soon
- `examples/` - Add basic usage examples
- `deployment/docker/` - Container support
- `scripts/setup/` - Onboarding automation

### ⚠️ Clean Up
- `tools/` - Remove legacy empty folders
- Review if all empty folders are needed

### 📝 Document
- Add README files to empty folders explaining their purpose
- Update this document as folders are populated

## 🚀 Next Steps

1. **Create Dockerfile** in `deployment/docker/`
2. **Add basic examples** in `examples/`
3. **Remove legacy `tools/`** folder structure
4. **Add setup scripts** in `scripts/`
5. **Populate `utils/`** with shared functions

---

*This structure supports scaling from current MVP to enterprise production system.*