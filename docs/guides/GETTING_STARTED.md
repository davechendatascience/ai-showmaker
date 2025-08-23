# Getting Started with AI-Showmaker

## 🚀 Quick Start

AI-Showmaker is an enterprise-grade AI development assistant powered by specialized MCP (Model Context Protocol) servers. It can perform mathematical calculations, manage remote servers, handle git operations, and track complex tasks with todo lists.

## 📋 Prerequisites

- **Python 3.11+**
- **Virtual Environment** (recommended)
- **SSH Access** to remote servers (optional)
- **Google API Key** for Gemini
- **Git Repository** (for development features)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/davechendatascience/ai-showmaker.git
cd ai-showmaker
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy the example environment file and configure:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional (for remote server features)
AWS_HOST=your.remote.server.com
AWS_USER=your_username
PEM_PATH=path/to/your/private_key.pem
```

## 🎯 Basic Usage

### Interactive Demo
```bash
python demo_mcp.py
```

Choose from:
1. **Basic functionality demo** - Automated showcase of all servers
2. **Interactive demo** - Human-in-the-loop conversation

### Direct Agent Usage
```bash
python main.py
```

This starts the full agent with example queries and interactive mode.

### Test the System
```bash
# Run all MCP server tests
python tests/mcp/test_servers.py

# Run integration tests
python tests/integration/test_mcp_agent.py
```

## 💡 Example Queries

### 🧮 Mathematical Calculations
```
"What is the square root of 144 plus factorial of 5?"
"Calculate compound interest for $1000 at 5% for 3 years"
"Set x = 25, then calculate x * 2 + sqrt(x)"
```

### 🌐 Remote Server Operations
```
"Check what files are in the home directory on the remote server"
"Create a Python script that prints 'Hello World' and deploy it"
"Run the greeting script interactively with input 'Alice'"
```

### 🔧 Development Tasks
```
"Show the git status of this repository"
"Find all Python files in the project"
"Search for the word 'MCP' in all files"
```

### 📋 Todo Management
```
"Create a todo list for building a web application"
"Show my current todo progress"
"Update the first todo to completed status"
```

### 🔄 Combined Operations
```
"Calculate 10 factorial, create a file with that result, and track progress with todos"
"Build a calculator app: create todos, implement it, and deploy to server"
```

## 🏗️ Architecture Overview

AI-Showmaker uses 4 specialized MCP servers:

### 🧮 Calculation Server (4 tools)
- Safe mathematical evaluation (no `eval()`)
- Variable management
- Scientific functions (sin, cos, log, etc.)
- Complex expressions

### 🌐 Remote Server (4 tools) 
- SSH command execution
- SFTP file operations
- Interactive program support
- Security validation

### 🔧 Development Server (8 tools)
- Git operations (status, commit, diff, log)
- File search and content search  
- Package management
- Development workflow

### 📋 Monitoring Server (6 tools)
- Todo list creation and management
- Progress tracking
- Session management
- Agent context maintenance

## 🔐 Security Features

### 🛡️ Built-in Protections
- **Path Traversal Prevention**: No `../../../etc/passwd` attacks
- **Safe Math Evaluation**: AST-based, no dangerous `eval()`
- **SSH Key Auth**: Secure remote access
- **Input Validation**: All parameters validated
- **File Extension Filtering**: Only safe file types allowed

### 🔒 Best Practices
- Store secrets in environment variables
- Use SSH keys instead of passwords  
- Keep your `.pem` files secure
- Regularly update dependencies

## 🧪 Development & Testing

### Running Tests
```bash
# Unit tests for individual servers
python tests/mcp/test_servers.py

# Integration tests for full system
python tests/integration/test_mcp_agent.py  

# Todo functionality tests
python tests/mcp/test_todo_fix.py
```

### Adding New Features
1. **Create feature branch**: `git checkout -b feature/new-feature`
2. **Implement in appropriate MCP server**
3. **Add tests** in `tests/` directory
4. **Update documentation**
5. **Submit pull request**

### Project Structure
```
ai-showmaker/
├── core/              # Agent orchestration & config
├── mcp_servers/       # 4 specialized MCP servers
├── tests/             # Comprehensive test suite
├── docs/              # API docs and guides  
├── main.py            # Primary entry point
├── demo_mcp.py        # Interactive demos
└── requirements.txt   # Dependencies
```

## 🎛️ Configuration Options

### Environment Variables
- `GOOGLE_API_KEY`: Required for agent LLM
- `AWS_HOST`: Remote server hostname
- `AWS_USER`: Remote server username  
- `PEM_PATH`: Path to SSH private key
- `PYTHONIOENCODING`: Set to `utf-8` for emoji support

### Config Sources (Priority Order)
1. Environment variables
2. `.env` file
3. `secrets/secrets.json`
4. Default values

### Advanced Configuration
```python
from core.config import ConfigManager

config = ConfigManager()
config_data = config.get_all_config()
```

## 🚨 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure you're in the project root and venv is activated
cd /path/to/ai-showmaker
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

#### Unicode/Emoji Issues (Windows)
```bash
# Set encoding environment variable
set PYTHONIOENCODING=utf-8
```

#### SSH Connection Issues
- Verify SSH key permissions: `chmod 600 your-key.pem`
- Test SSH connection manually: `ssh -i your-key.pem user@host`
- Check firewall settings

#### API Rate Limits
- Google API has usage limits
- Implement delays between requests if needed
- Monitor your API usage

### Getting Help

1. **Check Documentation**: `docs/` directory
2. **Run Tests**: Identify specific failing components
3. **Check Logs**: Agent provides detailed logging
4. **GitHub Issues**: Report bugs and feature requests

## 🔄 Updates & Maintenance

### Keeping Updated
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Branch Strategy
- **main**: Stable releases
- **develop**: Latest features
- **feature/***: New features in development

## 🎉 What's Next?

Once you're comfortable with basic usage:

1. **Explore Advanced Features**: Multi-step todo workflows
2. **Customize for Your Needs**: Add new MCP servers
3. **Integration**: Use in your development workflow
4. **Contribute**: Submit improvements and new features
5. **Deploy**: Use in production environments

## 📚 Additional Resources

- **API Documentation**: `docs/api/MCP_SERVERS.md`
- **Development Status**: `docs/DEVELOPMENT_STATUS.md`
- **Test Examples**: `tests/scenarios/test_queries.py`
- **GitHub Repository**: https://github.com/davechendatascience/ai-showmaker

---

*Happy coding with AI-Showmaker! 🚀*