# Local Models Integration Guide

This guide explains how to use local models (like Qwen) with the AI-Showmaker infrastructure.

## 🎯 Overview

Our infrastructure now supports local models through:
1. **Llama.cpp Integration** - High-performance, efficient local model inference (Recommended)
2. **Ollama Integration** - Easy-to-use alternative for beginners
3. **Custom LLM Classes** - Seamless integration with LlamaIndex
4. **Remote Repository Management** - Complete development workflow

## ⚡ Performance Comparison

| Feature | Llama.cpp | Ollama |
|---------|-----------|--------|
| **Speed** | ⭐⭐⭐⭐⭐ Very Fast | ⭐⭐⭐ Moderate |
| **Memory Efficiency** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |
| **Setup Complexity** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Easy |
| **Model Support** | ⭐⭐⭐⭐⭐ Extensive | ⭐⭐⭐⭐ Good |
| **GPU Acceleration** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |

## 🚀 Quick Start

### Prerequisites

1. **Environment Variables** (for remote server):
   ```bash
   AWS_HOST=your-ec2-instance.compute.amazonaws.com
   AWS_USER=ec2-user
   PEM_PATH=path/to/your/key.pem
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Option 1: Llama.cpp Setup (Recommended)

Llama.cpp provides the best performance and efficiency for local model inference.

#### 1.1 Install Llama.cpp

```bash
# Clone the repository
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Build with CMake (recommended)
mkdir build && cd build
cmake .. -DLLAMA_CURL=OFF
make -j$(nproc)

# Or build with specific optimizations
cmake .. -DLLAMA_CURL=OFF -DLLAMA_BLAS=ON -DLLAMA_AVX=ON
make -j$(nproc)
```

#### 1.2 Download Qwen Model

```bash
# Create models directory
mkdir -p models

# Download Qwen2.5:7B GGUF model with Q8_0 precision (recommended)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.Q8_0.gguf -O models/qwen2.5-7b-instruct-q8_0.gguf

# Or download other precision variants:
# Q4_K_M (4-bit, smaller file, faster, lower quality)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.Q4_K_M.gguf -O models/qwen2.5-7b-instruct-q4_km.gguf

# Q5_K_M (5-bit, good balance)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.Q5_K_M.gguf -O models/qwen2.5-7b-instruct-q5_km.gguf

# Q6_K (6-bit, higher quality)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.Q6_K.gguf -O models/qwen2.5-7b-instruct-q6_k.gguf

# F16 (16-bit, highest quality, largest file)
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.F16.gguf -O models/qwen2.5-7b-instruct-f16.gguf
```

#### 1.3 Test Llama.cpp

```bash
# Test the model
./bin/llama-cli -m models/qwen2.5-7b-instruct.gguf -n 128 -p "Hello! How are you?"

# Interactive chat mode
./bin/llama-cli -m models/qwen2.5-7b-instruct.gguf -i

# Server mode (for API access)
./bin/llama-server -m models/qwen2.5-7b-instruct.gguf --host 0.0.0.0 --port 8080
```

#### 1.4 Use with Our Infrastructure

```python
from core.local_llm import LlamaCppLLM

# Create Llama.cpp LLM
llm = LlamaCppLLM(
    model_path="llama.cpp/models/qwen2.5-7b-instruct.gguf",
    temperature=0.1,
    max_tokens=2048,
    n_ctx=4096
)

# Test completion
response = llm.complete("What is 2+2?")
print(response.text)
```

### Option 2: Local Ollama Setup

1. **Install Ollama locally**:
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama
   ollama serve
   ```

2. **Pull Qwen model**:
   ```bash
   ollama pull qwen2.5:7b
   ```

3. **Test with our infrastructure**:
   ```python
   from core.local_llm import OllamaLLM
   
   # Create local LLM
   llm = OllamaLLM(
       model_name="qwen2.5:7b",
       temperature=0.1
   )
   
   # Test completion
   response = llm.complete("Hello! How are you?")
   print(response.text)
   ```

### Option 2: Remote Ollama Setup

1. **Use our remote server tools**:
   ```python
   from mcp_servers.remote.server import RemoteMCPServer
   
   # Initialize remote server
   remote_server = RemoteMCPServer()
   await remote_server.initialize()
   
   # Install Ollama on remote server
   await remote_server._install_ollama()
   
   # Pull Qwen model
   await remote_server._pull_model("qwen2.5:7b")
   
   # Test the model
   response = await remote_server._test_local_model(
       "qwen2.5:7b", 
       "Hello! Can you tell me a joke?"
   )
   print(response)
   ```

## 🔧 Available Models

### Qwen Models - Precision Comparison

| Precision | File Size | Memory Usage | Speed | Quality | Use Case |
|-----------|-----------|--------------|-------|---------|----------|
| **Q4_K_M** | ~4.4GB | ~6GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Fast inference, limited memory |
| **Q5_K_M** | ~5.1GB | ~7GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Good balance, general use |
| **Q6_K** | ~6.1GB | ~8GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High quality, moderate speed |
| **Q8_0** | ~7.8GB | ~10GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **Recommended** - Best balance |
| **F16** | ~13.8GB | ~16GB | ⭐⭐ | ⭐⭐⭐⭐⭐ | Maximum quality, research |

### Model Size Options
- **Qwen2.5:7B** - 7B parameters (recommended for testing)
- **Qwen2.5:14B** - 14B parameters (better quality, 2x memory)
- **Qwen2.5:32B** - 32B parameters (best quality, 4x memory)

### Recommended Setup
For a powerful Linux server, we recommend:
- **Qwen2.5:7B with Q8_0 precision** - Best balance of quality and performance
- **Qwen2.5:14B with Q6_K precision** - Higher quality for production use

### Other Popular Models
- `llama3.1:8b` - Meta's Llama 3.1 8B
- `mistral:7b` - Mistral 7B
- `codellama:7b` - Code-focused model
- `phi3:3.8b` - Microsoft's Phi-3

## 📋 Available Tools

### Repository Management
- `init_workspace` - Initialize remote workspace
- `clone_repository` - Clone repositories to remote server
- `list_repositories` - List available repositories
- `switch_repository` - Switch between repositories

### Git Operations
- `git_status` - Check repository status
- `git_log` - View commit history
- `git_diff` - View changes
- `git_add` - Stage files
- `git_commit` - Commit changes
- `git_push` - Push to remote
- `git_pull` - Pull from remote

### Local Model Management
- `install_ollama` - Install Ollama on remote server
- `pull_model` - Download model to Ollama
- `list_ollama_models` - List available models
- `test_local_model` - Test model with prompt

### File Operations
- `write_file` - Write files to remote server
- `read_file` - Read files from remote server
- `list_directory` - List directory contents
- `execute_command` - Execute commands on remote server

## 🧪 Testing

Run the comprehensive test script:

```bash
python test_local_models.py
```

This will test:
1. Remote Ollama setup
2. Model downloading and testing
3. Repository workflow
4. Local model integration

## 🔄 Integration with Existing Agents

### Using Local Models with LlamaIndex Agents

```python
from core.local_llm import RemoteOllamaLLM
from core.llamaindex_agent import AIShowmakerAgent
from config import get_config

# Get configuration
config = get_config()

# Create remote Ollama LLM
llm = RemoteOllamaLLM(
    model_name="qwen2.5:7b",
    remote_host=config['aws_host'],
    temperature=0.1
)

# Create agent with local model
agent = AIShowmakerAgent(
    llm=llm,
    config=config
)

# Initialize and use
await agent.initialize()
response = await agent.process_query("What is the weather like?")
```

### Using Local Models with MCP Servers

```python
from mcp_servers.remote.server import RemoteMCPServer
from core.local_llm import RemoteOllamaLLM

# Initialize remote server
remote_server = RemoteMCPServer()
await remote_server.initialize()

# Test local model through remote server
response = await remote_server._test_local_model(
    "qwen2.5:7b",
    "Explain quantum computing in simple terms"
)
print(response)
```

## 🎯 Precision Selection Guide

### Understanding GGUF Quantization

GGUF models come in different quantization levels that trade off file size, memory usage, speed, and quality:

- **Q4_K_M**: 4-bit quantization, smallest file (~4.4GB), fastest inference, lowest quality
- **Q5_K_M**: 5-bit quantization, good balance of size and quality
- **Q6_K**: 6-bit quantization, higher quality, moderate speed
- **Q8_0**: 8-bit quantization, **recommended** for most use cases
- **F16**: 16-bit float, highest quality, largest file (~13.8GB)

### Choosing the Right Precision

| Use Case | Recommended Precision | Reason |
|----------|----------------------|---------|
| **Development/Testing** | Q4_K_M | Fast iteration, minimal resources |
| **Production (General)** | Q8_0 | Best balance of quality and performance |
| **High-Quality Output** | Q6_K or F16 | Maximum quality, research tasks |
| **Resource-Constrained** | Q4_K_M or Q5_K_M | Limited memory/CPU |

### For Your Powerful Linux Server

Since you have a powerful Linux server, we recommend:
- **Q8_0 precision** for most tasks - excellent quality with good performance
- **Q6_K precision** for high-quality applications
- **F16 precision** for research or maximum quality requirements

## 🛠️ Advanced Configuration

### Custom Model Parameters

```python
llm = OllamaLLM(
    model_name="qwen2.5:7b",
    temperature=0.7,  # Higher creativity
    max_tokens=2048   # Limit response length
)
```

### Streaming Responses

```python
# Stream completion
for chunk in llm.stream_complete("Write a story about a robot:"):
    print(chunk.text, end="", flush=True)

# Stream chat
messages = [
    ChatMessage(role=MessageRole.USER, content="Hello!"),
    ChatMessage(role=MessageRole.ASSISTANT, content="Hi there!"),
    ChatMessage(role=MessageRole.USER, content="Tell me a joke")
]

for chunk in llm.stream_chat(messages):
    print(chunk.text, end="", flush=True)
```

### Model Fine-tuning

```python
# Use custom model with specific parameters
llm = OllamaLLM(
    model_name="qwen2.5:7b",
    base_url="http://localhost:11434",
    temperature=0.1
)

# Create custom prompt template
system_prompt = "You are a helpful coding assistant. Always provide code examples."
user_prompt = "How do I implement a binary search tree in Python?"

full_prompt = f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:"
response = llm.complete(full_prompt)
```

## 🔒 Security Considerations

1. **Remote Server Access**: Ensure your AWS credentials are secure
2. **Model Downloads**: Be aware of storage costs for large models
3. **Network Security**: Use HTTPS for remote model communication
4. **Resource Limits**: Monitor CPU/memory usage with large models

## 🚨 Troubleshooting

### Common Issues

1. **"Ollama not found"**:
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama serve
   ```

2. **"Model not found"**:
   ```bash
   # Pull the model
   ollama pull qwen2.5:7b
   ```

3. **"Connection refused"**:
   - Check if Ollama is running: `ollama serve`
   - Verify port 11434 is accessible
   - Check firewall settings

4. **"Out of memory"**:
   - Use smaller models (7B instead of 32B)
   - Close other applications
   - Consider using remote server with more RAM

### Performance Optimization

1. **Model Selection**:
   - 7B models: Good for most tasks, fast inference
   - 14B models: Better quality, moderate speed
   - 32B models: Best quality, slower inference

2. **Hardware Requirements**:
   - 7B models: 8GB RAM minimum
   - 14B models: 16GB RAM minimum
   - 32B models: 32GB RAM minimum

3. **GPU Acceleration**:
   ```bash
   # Install CUDA version (if available)
   ollama pull qwen2.5:7b
   ```

## 📚 Examples

### Complete Workflow Example

```python
import asyncio
from mcp_servers.remote.server import RemoteMCPServer
from core.local_llm import RemoteOllamaLLM

async def complete_workflow():
    # 1. Setup remote server
    remote_server = RemoteMCPServer()
    await remote_server.initialize()
    
    # 2. Install and setup Ollama
    await remote_server._install_ollama()
    await remote_server._pull_model("qwen2.5:7b")
    
    # 3. Initialize workspace and clone repository
    await remote_server._init_workspace()
    await remote_server._clone_repository(
        "https://github.com/your-repo/your-project.git",
        "my-project"
    )
    await remote_server._switch_repository("my-project")
    
    # 4. Use local model for development
    response = await remote_server._test_local_model(
        "qwen2.5:7b",
        "Review this code and suggest improvements: [code here]"
    )
    print(response)
    
    # 5. Commit changes
    await remote_server._git_add(".")
    await remote_server._git_commit("Improvements suggested by AI")
    
    await remote_server.shutdown()

# Run the workflow
asyncio.run(complete_workflow())
```

This guide provides everything you need to get started with local models in your AI-Showmaker project!
