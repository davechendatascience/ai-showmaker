# MCP Servers API Reference

## Overview
AI-Showmaker uses 4 specialized MCP (Model Context Protocol) inspired servers, each handling specific tool domains.

## 🧮 Calculation Server

**Server**: `CalculationMCPServer`  
**Tools**: 4  
**Purpose**: Safe mathematical computations with variable support

### Tools

#### `calculate`
Advanced mathematical calculator supporting arithmetic, trigonometry, logarithms, factorials, and complex expressions.

**Parameters:**
- `expression` (string): Mathematical expression to evaluate

**Examples:**
```python
# Basic arithmetic
{"expression": "2 + 3 * 4"}  # Returns: "14"

# Scientific functions  
{"expression": "sin(pi/2) + sqrt(16)"}  # Returns: "5.0"

# Variables
{"expression": "x * 2 + 5"}  # (if x=10) Returns: "25"
```

#### `set_variable`
Set a variable for use in calculations.

**Parameters:**
- `name` (string): Variable name
- `value` (number): Variable value

#### `get_variables`  
Get all currently defined variables.

#### `clear_variables`
Clear all variables from memory.

---

## 🌐 Remote Server

**Server**: `RemoteMCPServer`  
**Tools**: 4  
**Purpose**: SSH/SFTP operations with security validation

### Tools

#### `execute_command`
Execute commands on remote server supporting both regular and interactive programs.

**Parameters:**
- `command` (string): Command to execute on remote server
- `input_data` (string, optional): Input data for interactive programs

**Examples:**
```python
# Regular command
{"command": "ls -la"}

# Interactive program
{"command": "python3 script.py", "input_data": "Alice\n25"}
```

#### `write_file`
Write files to remote server via SFTP with security validation.

**Parameters:**
- `filename` (string): Name of file to create (relative path only)
- `content` (string): Content to write to the file

#### `read_file`
Read file content from remote server via SFTP.

#### `list_directory`
List contents of directory on remote server.

---

## 🔧 Development Server  

**Server**: `DevelopmentMCPServer`  
**Tools**: 8  
**Purpose**: Git operations, file search, and package management

### Git Tools

#### `git_status`
Get git repository status showing modified files, untracked files, and branch info.

#### `git_add`
Stage files for git commit.

**Parameters:**
- `files` (string): Files to stage (space-separated, use '.' for all files)

#### `git_commit`
Create git commit with message.

**Parameters:**
- `message` (string): Commit message

#### `git_log`
Show git commit history.

**Parameters:**
- `max_commits` (integer): Maximum number of commits to show (default: 10)

#### `git_diff`
Show git differences for files.

### File Tools

#### `find_files`
Search for files by name pattern.

**Parameters:**
- `pattern` (string): File name pattern to search for (supports wildcards)
- `directory` (string): Directory to search in (default: ".")
- `file_type` (string): File extension filter

#### `search_in_files`
Search for text content within files.

**Parameters:**
- `search_text` (string): Text to search for
- `case_sensitive` (boolean): Case sensitive search (default: false)

### Package Tools

#### `install_package`
Install Python packages via pip.

---

## 📋 Monitoring Server

**Server**: `MonitoringMCPServer`  
**Tools**: 6  
**Purpose**: Task tracking and agent context management

### Session Management

#### `create_session`
Create a new agent session for task tracking.

**Parameters:**
- `session_name` (string): Name for the session (default: "default")

### Todo Management

#### `create_todos`
Create todo list for complex multi-step tasks to track progress and maintain context.

**Parameters:**
- `todos` (array): List of todo items

**Input Formats:**
```python
# Simple strings
{"todos": ["Install dependencies", "Configure git", "Deploy app"]}

# Detailed objects
{"todos": [
    {"content": "Plan architecture", "status": "pending"},
    {"content": "Write code", "status": "in_progress", "activeForm": "Writing the code"},
    "Test application"  # Mixed format supported
]}
```

#### `update_todo_status`
Update the status of a specific todo item.

**Parameters:**
- `todo_id` (string): ID of the todo item to update
- `status` (string): New status (pending|in_progress|completed|failed)
- `notes` (string, optional): Notes about the status change

#### `get_current_todos`
Get current todo list to see what tasks are pending or in progress.

#### `clear_todos`
Clear all todo items (use when starting a new task).

#### `get_progress_summary`
Get overall progress summary for current session.

---

## 🔧 Usage Examples

### Agent Integration
```python
from core.agent import AIShowmakerAgent
from core.config import ConfigManager

# Initialize agent with all MCP servers
config = ConfigManager()
agent = AIShowmakerAgent(config)
await agent.initialize()

# Execute complex task with todo tracking
result = agent.run("Create a web application with proper todo tracking")
```

### Direct Server Usage
```python
from mcp_servers.calculation.server import CalculationMCPServer

# Use individual server
calc_server = CalculationMCPServer()
await calc_server.initialize()

result = await calc_server.execute_tool("calculate", {
    "expression": "sqrt(144) + factorial(5)"
})
print(result.data)  # "132"
```

## 🛡️ Security Features

### Path Traversal Protection
- File operations validate paths to prevent `../../../etc/passwd` attacks
- Only relative paths allowed for file creation
- Restricted file extensions for security

### Input Validation
- All parameters validated against schema definitions
- Safe AST-based math evaluation (no `eval()`)
- SSH key-based authentication only

### Resource Management
- Connection pooling for SSH operations
- Proper timeout handling
- Graceful cleanup on shutdown

## 📊 Performance Characteristics

- **Initialization**: ~1-2 seconds for all servers
- **Tool Execution**: Sub-second for most operations
- **Memory Usage**: Efficient async operations
- **Connection Pooling**: Reused SSH connections
- **Error Recovery**: Automatic reconnection handling