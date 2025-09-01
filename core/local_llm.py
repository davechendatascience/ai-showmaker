"""
Local LLM class for Ollama and other local model support
"""
import requests
import json
import subprocess
import os
from llama_index.core.llms import CustomLLM
from llama_index.core.llms import ChatMessage, MessageRole, CompletionResponse, ChatResponse
from typing import Any, List, Optional
import asyncio


class LlamaCppLLM(CustomLLM):
    """Custom LLM for Llama.cpp local models"""
    
    model_path: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    n_ctx: int = 4096
    n_threads: int = 4
    llama_cpp_path: str = "./llama.cpp/build/bin/llama-cli"
    
    def __init__(
        self,
        model_path: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        n_ctx: int = 4096,
        n_threads: int = 4,
        llama_cpp_path: str = "./llama.cpp/build/bin/llama-cli",
        **kwargs: Any
    ):
        super().__init__(
            model_path=model_path,
            temperature=temperature,
            max_tokens=max_tokens,
            n_ctx=n_ctx,
            n_threads=n_threads,
            llama_cpp_path=llama_cpp_path,
            **kwargs
        )
    
    @property
    def metadata(self) -> Any:
        """Get LLM metadata."""
        return {
            "model_name": os.path.basename(self.model_path),
            "is_chat_model": True,
            "is_function_calling_model": False,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt using Llama.cpp CLI."""
        try:
            # Build command
            cmd = [
                self.llama_cpp_path,
                "-m", self.model_path,
                "-n", str(self.max_tokens or 128),
                "-p", prompt,
                "--temp", str(self.temperature),
                "--ctx-size", str(self.n_ctx),
                "--threads", str(self.n_threads)
            ]
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Extract response from output
                output = result.stdout.strip()
                # Remove the prompt from the response
                if prompt in output:
                    response = output.split(prompt, 1)[1].strip()
                else:
                    response = output
                return CompletionResponse(text=response)
            else:
                raise Exception(f"Llama.cpp error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Llama.cpp request timed out")
        except Exception as e:
            raise Exception(f"Llama.cpp request failed: {str(e)}")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the model using Llama.cpp CLI."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the complete method
            completion = self.complete(prompt, **kwargs)
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=completion.text))
            
        except Exception as e:
            raise Exception(f"Llama.cpp chat failed: {str(e)}")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> Any:
        """Stream complete the prompt using Llama.cpp CLI."""
        try:
            # Build command
            cmd = [
                self.llama_cpp_path,
                "-m", self.model_path,
                "-n", str(self.max_tokens or 128),
                "-p", prompt,
                "--temp", str(self.temperature),
                "--ctx-size", str(self.n_ctx),
                "--threads", str(self.n_threads),
                "--streaming"
            ]
            
            # Execute command with streaming
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in process.stdout:
                if line.strip():
                    yield CompletionResponse(text=line.strip())
                    
            process.wait()
            
        except Exception as e:
            raise Exception(f"Llama.cpp streaming failed: {str(e)}")
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Any:
        """Stream chat with the model using Llama.cpp CLI."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the stream_complete method
            for completion in self.stream_complete(prompt, **kwargs):
                yield completion
                
        except Exception as e:
            raise Exception(f"Llama.cpp streaming chat failed: {str(e)}")


class LlamaCppServerLLM(CustomLLM):
    """Custom LLM for Llama.cpp server mode"""
    
    server_url: str = "http://localhost:8080"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    
    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        super().__init__(
            server_url=server_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @property
    def metadata(self) -> Any:
        """Get LLM metadata."""
        return {
            "model_name": "llama-cpp-server",
            "is_chat_model": True,
            "is_function_calling_model": False,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt using Llama.cpp server API."""
        try:
            payload = {
                "prompt": prompt,
                "n_predict": self.max_tokens or 128,
                "temperature": self.temperature,
                "stream": False
            }
            
            response = requests.post(
                f"{self.server_url}/completion",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return CompletionResponse(text=result.get("content", ""))
            
        except Exception as e:
            raise Exception(f"Llama.cpp server request failed: {str(e)}")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the model using Llama.cpp server API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the complete method
            completion = self.complete(prompt, **kwargs)
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=completion.text))
            
        except Exception as e:
            raise Exception(f"Llama.cpp server chat failed: {str(e)}")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> Any:
        """Stream complete the prompt using Llama.cpp server API."""
        try:
            payload = {
                "prompt": prompt,
                "n_predict": self.max_tokens or 128,
                "temperature": self.temperature,
                "stream": True
            }
            
            response = requests.post(
                f"{self.server_url}/completion",
                json=payload,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "content" in data:
                            yield CompletionResponse(text=data["content"])
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            raise Exception(f"Llama.cpp server streaming failed: {str(e)}")
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Any:
        """Stream chat with the model using Llama.cpp server API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the stream_complete method
            for completion in self.stream_complete(prompt, **kwargs):
                yield completion
                
        except Exception as e:
            raise Exception(f"Llama.cpp server streaming chat failed: {str(e)}")


class OllamaLLM(CustomLLM):
    """Custom LLM for Ollama local models"""
    
    model_name: str
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    
    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @property
    def metadata(self) -> Any:
        """Get LLM metadata."""
        return {
            "model_name": self.model_name,
            "is_chat_model": True,
            "is_function_calling_model": False,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt using Ollama API."""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                }
            }
            
            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens
            
            # Make the API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return CompletionResponse(text=result.get("response", ""))
            
        except Exception as e:
            raise Exception(f"Ollama API request failed: {str(e)}")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the model using Ollama API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the complete method
            completion = self.complete(prompt, **kwargs)
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=completion.text))
            
        except Exception as e:
            raise Exception(f"Ollama chat failed: {str(e)}")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> Any:
        """Stream complete the prompt using Ollama API."""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                }
            }
            
            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens
            
            # Make the streaming API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "response" in data:
                            yield CompletionResponse(text=data["response"])
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            raise Exception(f"Ollama streaming failed: {str(e)}")
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Any:
        """Stream chat with the model using Ollama API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the stream_complete method
            for completion in self.stream_complete(prompt, **kwargs):
                yield completion
                
        except Exception as e:
            raise Exception(f"Ollama streaming chat failed: {str(e)}")


class RemoteOllamaLLM(CustomLLM):
    """Custom LLM for Ollama models running on remote server"""
    
    model_name: str
    remote_host: str
    remote_port: int = 11434
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    
    def __init__(
        self,
        model_name: str,
        remote_host: str,
        remote_port: int = 11434,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        super().__init__(
            model_name=model_name,
            remote_host=remote_host,
            remote_port=remote_port,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        self.base_url = f"http://{remote_host}:{remote_port}"
    
    @property
    def metadata(self) -> Any:
        """Get LLM metadata."""
        return {
            "model_name": self.model_name,
            "is_chat_model": True,
            "is_function_calling_model": False,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt using remote Ollama API."""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                }
            }
            
            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens
            
            # Make the API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return CompletionResponse(text=result.get("response", ""))
            
        except Exception as e:
            raise Exception(f"Remote Ollama API request failed: {str(e)}")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the remote model using Ollama API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the complete method
            completion = self.complete(prompt, **kwargs)
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=completion.text))
            
        except Exception as e:
            raise Exception(f"Remote Ollama chat failed: {str(e)}")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> Any:
        """Stream complete the prompt using remote Ollama API."""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                }
            }
            
            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens
            
            # Make the streaming API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "response" in data:
                            yield CompletionResponse(text=data["response"])
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            raise Exception(f"Remote Ollama streaming failed: {str(e)}")
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Any:
        """Stream chat with the remote model using Ollama API."""
        try:
            # Convert messages to a single prompt
            prompt = ""
            for msg in messages:
                if msg.role == MessageRole.USER:
                    prompt += f"User: {msg.content}\n"
                elif msg.role == MessageRole.ASSISTANT:
                    prompt += f"Assistant: {msg.content}\n"
                elif msg.role == MessageRole.SYSTEM:
                    prompt += f"System: {msg.content}\n"
                else:
                    prompt += f"User: {msg.content}\n"
            
            prompt += "Assistant: "
            
            # Use the stream_complete method
            for completion in self.stream_complete(prompt, **kwargs):
                yield completion
                
        except Exception as e:
            raise Exception(f"Remote Ollama streaming chat failed: {str(e)}")
