# AI-Showmaker

A comprehensive LangChain-based agent framework that combines LLM capabilities with secure remote execution tools for development workflows.

## 🚀 Features

### 🧮 **Advanced Calculator**
- ✅ Secure AST-based mathematical evaluation (no eval!)
- ✅ Scientific functions: trigonometry, logarithms, factorials
- ✅ Variables and complex expressions
- ✅ Constants: pi, e, tau, inf, nan

### 🖥️ **Smart Remote Commands** 
- ✅ Unified tool for both regular and interactive commands
- ✅ SSH connection pooling for performance
- ✅ 30-second timeouts and proper error handling
- ✅ Exit code reporting and detailed output

### 📁 **Secure File Operations**
- ✅ SFTP file writing with security validation
- ✅ Path traversal protection
- ✅ File extension whitelisting
- ✅ Automatic directory creation

### 🔧 **Development Features**
- ✅ Human-in-the-loop confirmation system
- ✅ Comprehensive test framework with 50+ scenarios
- ✅ Flexible configuration (environment variables, .env, JSON)
- ✅ Connection pooling and resource management

## 🛡️ Security Features

- **Path Validation**: Prevents directory traversal attacks
- **File Extension Control**: Only allows safe file types
- **SSH Key Authentication**: Secure server connections
- **Input Sanitization**: All user inputs are validated
- **Connection Timeouts**: Prevents hanging connections

## 📊 Testing

- **Unit Tests**: Individual tool testing
- **Integration Tests**: Full workflow validation  
- **Interactive Tests**: Human-guided testing
- **Security Tests**: Validation bypass attempts
