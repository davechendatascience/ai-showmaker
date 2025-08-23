# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Showmaker is a LangChain-based agent framework that combines LLM capabilities with remote execution tools. It provides an interactive agent system with human-in-the-loop functionality and remote server management capabilities.

## Setup and Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration Options

Choose one of these configuration approaches:

**Option 1: Environment Variables (Recommended for production)**
```bash
export GOOGLE_API_KEY="your-api-key-here"
export AWS_HOST="your-ec2-host"
export AWS_USER="ec2-user"
export PEM_PATH="secrets/your-key.pem"
```

**Option 2: .env file (Recommended for development)**
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

**Option 3: Legacy secrets.json (Backward compatibility)**
Place files in the `secrets/` directory:
- `secrets/secrets.json` with your Google API key
- `secrets/ai-showmaker.pem` for AWS EC2 access

## Core Architecture

The project consists of two main components:

### 1. Agent Framework (`agent_demo.py`)
- **LLM Backend**: Uses Google's Gemini 2.5 Flash via LangChain
- **Agent Type**: Zero-shot ReAct (Reasoning + Acting) agent
- **Human-in-the-Loop**: Interactive confirmation system with retry mechanism
- **Remote Configuration**: Hardcoded AWS EC2 connection details for remote execution

### 2. Tool System (`tools.py`)
- **Calculator Tool**: Basic math evaluation using `eval()`
- **Remote Command Tool**: SSH-based command execution on AWS EC2
- **Remote File Writer**: SFTP-based file creation on remote server
- **Service Deployment Tool**: SystemD service deployment functionality

### Key Design Patterns
- Tools accept JSON string inputs for complex parameters
- SSH connections use Ed25519 key authentication
- All remote operations include comprehensive error handling
- Human feedback is incorporated into agent retry loops

## Running the Agent

Execute the main demo:
```bash
python agent_demo.py
```

The agent will process the hardcoded query about creating an art gallery and publishing it to the web, with interactive confirmation at each step.

## Remote Server Integration

The system is configured to work with AWS EC2 instances:
- **Host**: Configured in `agent_demo.py` (currently hardcoded)
- **User**: `ec2-user` (Amazon Linux)
- **Authentication**: Ed25519 SSH key via `.pem` file
- **Capabilities**: Command execution, file writing, service deployment

## Security Considerations

- Secrets are stored in the `secrets/` directory (git-ignored)
- Use environment variables or `.env` files for sensitive configuration
- SSH private keys are stored in `secrets/` directory
- Remote commands execute with full user privileges
- Calculator tool uses `eval()` - be cautious with user input