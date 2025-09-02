"""
Custom LLM class for inference.net compatibility
"""
import openai
from llama_index.core.llms import CustomLLM
from llama_index.core.llms import ChatMessage, MessageRole, CompletionResponse, ChatResponse
from typing import Any, List, Optional
import json
import ssl
import urllib3


class InferenceNetLLM(CustomLLM):
    """Custom LLM for inference.net that bypasses model validation"""
    
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    client: Optional[Any] = None
    verify_ssl: bool = False  # Add SSL verification control
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        verify_ssl: bool = False,  # Add SSL verification parameter
        **kwargs: Any
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        self.verify_ssl = verify_ssl
        
        # Disable SSL warnings if verification is disabled
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Create OpenAI client with custom base URL and SSL settings
        if not verify_ssl:
            # Create custom HTTP client without SSL verification
            import httpx
            http_client = httpx.Client(verify=False)
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
        else:
            # Use default client with SSL verification
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
    
    @property
    def metadata(self) -> Any:
        """Get LLM metadata."""
        return {
            "model_name": self.model,
            "is_chat_model": True,
            "is_function_calling_model": False,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt."""
        try:
            # Convert prompt to chat format
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            return CompletionResponse(text=response.choices[0].message.content)
        except Exception as e:
            # Provide more detailed error information
            error_msg = f"LLM completion failed: {str(e)}"
            if "SSL" in str(e) or "certificate" in str(e).lower():
                error_msg += "\nThis appears to be an SSL certificate issue. Try setting verify_ssl=False or check your network configuration."
            raise Exception(error_msg) from e
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the model."""
        try:
            # Convert ChatMessage objects to OpenAI format
            openai_messages = []
            for msg in messages:
                if msg.role == MessageRole.USER:
                    openai_messages.append({"role": "user", "content": msg.content})
                elif msg.role == MessageRole.ASSISTANT:
                    openai_messages.append({"role": "assistant", "content": msg.content})
                elif msg.role == MessageRole.SYSTEM:
                    openai_messages.append({"role": "system", "content": msg.content})
                else:
                    # Handle other roles as user messages
                    openai_messages.append({"role": "user", "content": msg.content})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=response.choices[0].message.content))
        except Exception as e:
            # Provide more detailed error information
            error_msg = f"LLM chat failed: {str(e)}"
            if "SSL" in str(e) or "certificate" in str(e).lower():
                error_msg += "\nThis appears to be an SSL certificate issue. Try setting verify_ssl=False or check your network configuration."
            raise Exception(error_msg) from e
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> Any:
        """Stream complete the prompt."""
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            **kwargs
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield CompletionResponse(text=chunk.choices[0].delta.content)
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Any:
        """Stream chat with the model."""
        openai_messages = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                openai_messages.append({"role": "user", "content": msg.content})
            elif msg.role == MessageRole.ASSISTANT:
                openai_messages.append({"role": "assistant", "content": msg.content})
            elif msg.role == MessageRole.SYSTEM:
                openai_messages.append({"role": "system", "content": msg.content})
            else:
                openai_messages.append({"role": "user", "content": msg.content})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            **kwargs
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield CompletionResponse(text=chunk.choices[0].delta.content)
