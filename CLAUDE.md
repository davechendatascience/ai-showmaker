# CLAUDE.md

This file provides specific guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

🤖 **AI-Showmaker** is an enterprise-grade AI development assistant powered by an MCP-inspired architecture. For complete project overview, features, and architecture details, see [README.md](./ReadMe.md).

## Claude Code Quick Reference

**Key Commands for Claude Code:**
```bash
# Run tests with proper encoding (Windows)
set PYTHONIOENCODING=utf-8 && python -X utf8 run_tests.py

# Run integration tests
python -X utf8 "tests\integration\test_mcp_agent.py"

# Run the agent
python main.py

# Run interactive demo
python demo_mcp.py
```

## Claude Code Development Guidelines

### Testing Requirements
- **Always run tests after code changes**: Use `run_tests.py` for quick validation
- **Windows users**: Use UTF-8 encoding flags for Unicode output (emojis in logs)
- **Integration tests**: Run `test_mcp_agent.py` for full system validation

### Configuration for Claude Code
The project supports multiple configuration methods detailed in [README.md](./ReadMe.md#️-configuration). For Claude Code development:

1. **Environment variables** (recommended for production)
2. **.env file** (recommended for development)
3. **JSON configuration** (flexible alternative)

## MCP Server Architecture

**4 Specialized Servers, 22+ Tools** - detailed in [README.md](./ReadMe.md#️-architecture):
- 🧮 **Calculation Server**: Safe math evaluation, variables, scientific functions
- 🌐 **Remote Server**: SSH/SFTP operations with security validation  
- 🔧 **Development Server**: Git integration, file search, package management
- 📋 **Monitoring Server**: Todo tracking, session management, progress monitoring

## Claude Code Best Practices

### When Making Code Changes
1. **Always run tests first**: `python -X utf8 run_tests.py`
2. **Test specific functionality**: Use integration tests for complex features
3. **Check cross-platform compatibility**: Especially for Windows Unicode issues
4. **Validate security**: All file operations, SSH connections, input validation

### Common Tasks
```bash
# Fix failing tests
python -X utf8 run_tests.py

# Test remote operations
python -X utf8 "tests\integration\test_mcp_agent.py"

# Validate agent todo functionality  
python -X utf8 "tests\integration\test_agent_todos.py"

# Run interactive demo for manual testing
python demo_mcp.py
```

### Key Files to Know
- `core/agent.py` - Main agent orchestration
- `mcp_servers/*/server.py` - Individual MCP server implementations
- `run_tests.py` - Primary test runner (Windows-compatible)
- `tests/integration/` - Full system testing

For complete project details, testing instructions, configuration options, and architecture documentation, see [README.md](./ReadMe.md).

---

## Important Claude Code Reminders

**Development Workflow:**
- Use `develop` branch for new features
- Always run tests before committing changes
- Windows users: Set `PYTHONIOENCODING=utf-8` for Unicode output
- Create pull requests from `develop` → `main` for code review

**Security & Best Practices:**
- Never commit secrets or API keys
- All file operations include path traversal protection
- SSH connections use key-based authentication only
- Input validation is enforced via JSON schemas
- Use AST-based math evaluation (no `eval()`)

**Key Testing Commands:**
```bash
# Main test validation
python -X utf8 run_tests.py

# Full integration testing
python -X utf8 "tests\integration\test_mcp_agent.py"
```