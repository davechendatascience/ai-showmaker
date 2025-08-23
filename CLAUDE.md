# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

🤖 **AI-Showmaker** is an enterprise-grade AI development assistant powered by an **MCP (Model Context Protocol) inspired architecture** with specialized servers for comprehensive development workflows. Transform from simple tasks to complex multi-step projects with built-in progress tracking and context management.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/davechendatascience/ai-showmaker.git
cd ai-showmaker
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure (copy .env.example to .env and add your keys)
cp .env.example .env

# Run interactive demo
python demo_mcp.py

# Or run the full agent
python main.py
```

## MCP Architecture Overview

**4 Specialized MCP Servers, 22+ Professional Tools:**

### 🧮 **Calculation Server** (4 Tools)
- Safe mathematical evaluation (AST-based, no dangerous `eval()`)
- Advanced functions: trigonometry, logarithms, factorials, GCD/LCM  
- Variable management with persistent calculations
- Scientific constants: π, e, τ, ∞

### 🌐 **Remote Server** (4 Tools)  
- SSH operations with connection pooling
- Interactive program support with input handling
- SFTP file management with security validation
- Directory operations and remote filesystem management

### 🔧 **Development Server** (8 Tools)
- Git integration: status, add, commit, log, diff operations
- File search with pattern matching across projects  
- Package management for Python dependencies
- Complete version control and project management

### 📋 **Monitoring Server** (6 Tools)
- Todo lists for complex multi-step task tracking
- Progress monitoring with real-time status updates  
- Session management across long development workflows
- Agent memory with persistent task history

## Configuration

Choose one of these configuration approaches (priority order):

**Option 1: Environment Variables (Production)**
```bash
export GOOGLE_API_KEY="your-api-key-here"
export AWS_HOST="your-ec2-host"
export AWS_USER="ec2-user"
export PEM_PATH="secrets/your-key.pem"
```

**Option 2: .env file (Development)**
```bash
cp .env.example .env
# Edit .env with your configuration values
```

**Option 3: JSON Configuration (Flexible)**
```json
{
  "google_api_key": "your-api-key",
  "aws_host": "your-ec2-host",
  "aws_user": "ec2-user",
  "pem_path": "secrets/your-key.pem"
}
```

## Running Tests

**Run all MCP server tests:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run unit tests for individual servers
python -m pytest tests/mcp/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run specific test scenarios
python tests/scenarios/test_queries.py

# Quick MCP server validation
python -m tests.mcp.test_servers
```

**Test Categories:**
- `tests/mcp/` - Unit tests for individual MCP servers
- `tests/integration/` - Full agent system testing  
- `tests/scenarios/` - Real-world usage patterns

## Enterprise Security Features

- 🚫 **No `eval()` usage**: Safe AST-based mathematical evaluation
- 🛡️ **Path traversal protection**: Comprehensive file path validation  
- 🔐 **SSH key authentication**: No password-based authentication
- ✅ **Input validation**: All parameters validated against JSON schemas
- 🔒 **Secret management**: Environment-based configuration system
- ⏱️ **Resource management**: Connection pooling with proper cleanup

## Development Workflow

**Branch Strategy:**
- `main` - Production releases
- `develop` - Active development (use for new features)

**Making Changes:**
```bash
# Switch to develop branch
git checkout develop

# Make your changes, then commit
git add .
git commit -m "Your change description"

# Push to develop branch
git push origin develop
```

**Pull Request Process:**
Yes, for proper code review process, create pull requests to merge `develop` → `main`:
```bash
# Using GitHub CLI (if available)
gh pr create --title "Your PR Title" --base main --head develop

# Or through GitHub web interface
# Navigate to repository → Pull requests → New pull request
# Base: main ← Compare: develop
```

## Running the Agent

**Interactive Demo:**
```bash
python demo_mcp.py
```

**Full Agent System:**
```bash
python main.py
```

**Agent Features:**
- Multi-server orchestration with 22+ tools
- Built-in todo list management for complex tasks
- Interactive command support for remote servers
- Comprehensive error handling and retry mechanisms
- Session persistence across long workflows

## Project Structure

```
ai-showmaker/
├── 🎯 core/              # Agent orchestration & configuration
│   ├── agent.py          # Main agent with MCP server integration
│   └── config.py         # Multi-source configuration management
├── 🏗️ mcp_servers/       # 4 specialized MCP servers
│   ├── base/            # Base server classes and interfaces
│   ├── calculation/     # Mathematical operations server
│   ├── remote/          # SSH/SFTP operations server  
│   ├── development/     # Git & file operations server
│   └── monitoring/      # Todo & session management server
├── 🧪 tests/            # Comprehensive test suite
│   ├── mcp/            # Unit tests for individual servers
│   ├── integration/    # Full system integration tests
│   └── scenarios/      # Real-world usage patterns
├── 📚 docs/            # Comprehensive documentation
├── 🚀 main.py          # Primary entry point
└── 🎮 demo_mcp.py      # Interactive demonstrations
```

## Security Considerations

- ✅ Secrets stored securely in environment variables or `secrets/` directory
- ✅ All file operations include path traversal attack prevention
- ✅ SSH connections use key-based authentication only
- ✅ Mathematical evaluation uses AST parsing (no dangerous `eval()`)
- ✅ All user inputs validated against JSON schemas
- ✅ Connection pooling with proper resource cleanup