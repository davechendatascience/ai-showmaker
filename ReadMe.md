# AI-Showmaker

🤖 **Intelligent AI Development Assistant**

An advanced AI agent with **Intelligent Task Planning** powered by **MCP (Model Context Protocol) inspired architecture** and **LlamaIndex integration**. Automatically detects complex multi-step tasks and executes them systematically with built-in progress tracking, output validation, and context management.

## 🏗️ Architecture

**Intelligent Agent System** - 3 agent types, 4 specialized servers, 22+ professional tools:

### 🧠 **Intelligent Task Planning**
- ✅ **Automatic Task Detection**: Identifies complex multi-step tasks
- ✅ **Domain-Specific Planning**: Flask, deployment, monitoring, data processing
- ✅ **Systematic Execution**: Step-by-step task execution with progress tracking
- ✅ **Output Validation**: Intelligent pattern matching and error detection
- ✅ **Error Recovery**: Graceful failure handling with detailed reporting

### 🤖 **Agent Types**
- ✅ **LangChain Agent**: Traditional MCP integration
- ✅ **LlamaIndex Agent**: Enhanced LLM capabilities with inference.net
- ✅ **Intelligent Agent**: Advanced task planning with automatic execution

### 🧮 **Calculation Server** (4 Tools)
- ✅ **Safe Mathematical Evaluation**: AST-based parsing (no dangerous `eval()`)
- ✅ **Advanced Functions**: Trigonometry, logarithms, factorials, GCD/LCM  
- ✅ **Variable Management**: Multi-step calculations with persistent variables
- ✅ **Scientific Constants**: π, e, τ, ∞ and comprehensive math library

### 🌐 **Remote Server** (4 Tools)  
- ✅ **SSH Operations**: Secure command execution with connection pooling
- ✅ **Interactive Programs**: Full support for programs requiring user input
- ✅ **SFTP File Management**: Secure file read/write with path validation
- ✅ **Directory Operations**: List, navigate, and manage remote filesystems

### 🔧 **Development Server** (8 Tools)
- ✅ **Git Integration**: Status, add, commit, log, diff operations
- ✅ **File Search**: Pattern matching and content search across projects  
- ✅ **Package Management**: Python package installation and dependency management
- ✅ **Development Workflow**: Complete version control and project management

### 📋 **Monitoring Server** (6 Tools)
- ✅ **Todo Lists**: Create and manage complex multi-step task tracking
- ✅ **Progress Monitoring**: Real-time status updates with emoji indicators  
- ✅ **Session Management**: Maintain context across long development sessions
- ✅ **Agent Memory**: Persistent task history and progress analytics

## ⚡ Quick Start

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

## 🎯 Example Capabilities

### 🧠 Intelligent Task Planning
```
"Create a Flask web application with:
1. Basic web server on port 5000
2. Welcome page with current time
3. Health check endpoint
4. Basic logging
5. Requirements.txt with Flask dependency
6. Startup script
7. Test the application startup"

→ Agent automatically detects this as a complex task and executes all 6 steps systematically!
```

### 🧪 Multi-Server Workflows
```
"Create a todo list for building a web calculator, then implement it step by step:
1. Plan the architecture 
2. Write the Python Flask backend
3. Create the HTML frontend  
4. Deploy to the remote server
5. Test the complete application"
```

### 🔬 Complex Development Tasks  
```
"Check the git status, calculate the optimal server configuration for 100 users, 
create a deployment script with those specifications, and track progress with todos"
```

### 🎛️ Interactive Programming
```
"Create a Python script that asks for user preferences, deploy it to the server,
then run it interactively with sample inputs"
```

## 🛡️ Enterprise Security

- **🚫 No `eval()`**: Safe AST-based mathematical evaluation
- **🛡️ Path Traversal Protection**: Comprehensive file path validation  
- **🔐 SSH Key Authentication**: No password-based authentication
- **✅ Input Validation**: All parameters validated against JSON schemas
- **🔒 Secret Management**: Environment-based configuration system
- **⏱️ Resource Management**: Connection pooling with proper cleanup

## 🧪 Comprehensive Testing

### Test Organization
```
tests/
├── mcp/           # Unit tests for individual MCP servers
├── integration/   # Full agent system testing  
├── scenarios/     # Real-world usage patterns
└── unit/         # Component-level testing
```

### Test Coverage
- **✅ 20+ Test Files**: Comprehensive validation of all functionality
- **✅ Intelligent Task Planning Tests**: Complex task detection and execution
- **✅ LlamaIndex Integration Tests**: Enhanced LLM capabilities
- **✅ Output Validation Tests**: Pattern matching and error detection
- **✅ Offline Testing**: MCP servers can be tested without internet
- **✅ Integration Testing**: Full agent workflows with todo tracking
- **✅ Security Testing**: Path traversal and input validation tests
- **✅ Performance Testing**: Connection pooling and async operations

## 📁 Project Structure

```
ai-showmaker/
├── 🎯 core/              # Agent orchestration & configuration
├── 🏗️ mcp_servers/       # 4 specialized MCP servers
│   ├── calculation/      # Mathematical operations
│   ├── remote/          # SSH/SFTP operations  
│   ├── development/     # Git & file operations
│   └── monitoring/      # Todo & session management
├── 🧪 tests/            # Comprehensive test suite
├── 📚 docs/             # API docs, guides, & architecture
├── 🚀 main.py           # Primary entry point
└── 🎮 demo_mcp.py       # Interactive demonstrations
```

## ⚙️ Configuration

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

## 🧪 Running Tests

**Windows (with UTF-8 support):**
```bash
# Ensure virtual environment is activated
venv\Scripts\activate

# Set encoding for Unicode output (emojis in logs)
set PYTHONIOENCODING=utf-8

# Run comprehensive test suite (recommended)
python -X utf8 run_comprehensive_tests.py

# Run legacy test suite (basic MCP servers only)
python -X utf8 run_tests.py

# Run individual integration tests
python -X utf8 "tests\integration\test_intelligent_task_planning.py"
```

**Linux/Mac:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Run comprehensive test suite (recommended)
python run_comprehensive_tests.py

# Run legacy test suite (basic MCP servers only)
python run_tests.py

# Run individual integration tests
python tests/integration/test_intelligent_task_planning.py
```

**Test Categories:**
- `tests/mcp/` - Unit tests for individual MCP servers
- `tests/integration/` - Full agent system testing  
- `tests/scenarios/` - Real-world usage patterns

## 🔄 Development Workflow

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

## 📊 Performance & Statistics

- **⚡ Startup Time**: ~2-3 seconds (all servers initialized)
- **🎯 Tool Execution**: Sub-second response for most operations  
- **💾 Memory Efficient**: Async operations with connection pooling
- **📈 Scalable**: Modular architecture supports easy expansion
- **🔄 Session Tracking**: Built-in metrics and progress monitoring
