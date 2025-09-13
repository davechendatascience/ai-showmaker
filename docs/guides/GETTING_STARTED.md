# Getting Started with AI-Showmaker

## 🚀 Quick Start

AI-Showmaker is a revolutionary AI agent framework featuring **failure-aware planning**, **rich context memory**, and **automatic adaptation**. Unlike traditional agents that get stuck in infinite loops, our system learns from failures and completes complex tasks efficiently.

## 📋 Prerequisites

- **Node.js 18+**
- **Python 3.11+**
- **OpenAI API Key** (for LLM integration)
- **Virtual Environment** (recommended for Python)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/davechendatascience/ai-showmaker.git
cd ai-showmaker
```

### 2. Install Dependencies
```bash
# Install Node.js dependencies
npm install

# Set up Python environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# OPENAI_KEY=sk-your-openai-key-here
# MCP_HTTP_BASE=http://127.0.0.1:3310/api/bridge
```

### 4. Start the System
```bash
# Start the MCP bridge (Python)
python full_mcp_bridge.py

# In another terminal, start the monitoring UI
npm run monitor:ui
```

## 🎯 Try Sample Queries

Once the system is running, try these sample queries:

### Simple Tasks
- `what is 2+2` - Basic math calculation
- `solve leetcode 1234` - Coding problem with tests

### Complex Tasks  
- `develop a webapp on remote server amazon linux` - Full web application setup
- `Create a real-time data analytics dashboard that processes streaming data, performs statistical analysis, visualizes trends, and provides interactive insights` - Multi-component system

## 🎉 What to Expect

You'll see the system:
1. **Detect failure risks** and adapt plans automatically
2. **Create files and code** with proper structure
3. **Validate completion** with evidence-based assessment
4. **Complete tasks efficiently** without infinite loops

## 📚 Next Steps

- Read the [Failure-Aware BFS documentation](../FAILURE_AWARE_BFS.md) for technical details
- Check the [Repository Structure](../REPOSITORY_STRUCTURE.md) to understand the codebase
- Explore the [MCP Servers API](../api/MCP_SERVERS.md) for available tools

## 🆘 Troubleshooting

### Common Issues
- **MCP Bridge not starting**: Check Python virtual environment is activated
- **OpenAI API errors**: Verify your API key in `.env`
- **Port conflicts**: Ensure port 3310 is available for MCP bridge

### Getting Help
1. Check the logs in the monitoring UI
2. Review the [troubleshooting section](../README.md#troubleshooting)
3. Open an issue on GitHub

---

**Welcome to AI-Showmaker!** 🚀 You're now ready to experience the future of AI agent development.