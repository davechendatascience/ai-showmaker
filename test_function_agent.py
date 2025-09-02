#!/usr/bin/env python3
"""Simple test script for FunctionAgent with basic tools."""

import asyncio
from typing import Optional
from llama_index.core.tools import FunctionTool
from llama_index.core.agent.workflow import FunctionAgent
from core.agent import MCPIntegratedAgent
from core.config import ConfigManager

# Define simple test tools
def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""
    return a * b

def search_web(query: str) -> str:
    """Searches the web and returns results for the query."""
    return f"Web results for '{query}': Example answer from search."

async def test_function_agent():
    print("=== FunctionAgent Test ===")
    
    # Test 1: Simple FunctionAgent with basic tools
    print("\n1. Testing FunctionAgent with basic tools...")
    try:
        # Create tools
        multiply_tool = FunctionTool.from_defaults(multiply)
        search_tool = FunctionTool.from_defaults(search_web)
        
        # Initialize our custom LLM
        config = ConfigManager()
        api_key = config.get('inference_net_key')
        base_url = config.get('inference_net_base_url', 'https://api.inference.net')
        model = config.get('inference_net_model', 'mistral-7b-instruct')
        
        if not api_key:
            print("   ❌ No inference_net_key found in config")
            return
        
        # Create a function-calling LLM wrapper for our InferenceNet LLM
        from llama_index.core.llms import CustomLLM
        from core.custom_llm import InferenceNetLLM
        
        class FunctionCallingInferenceNetLLM(CustomLLM):
            api_key: str
            base_url: str
            model: str
            
            def __init__(self, api_key: str, base_url: str, model: str):
                super().__init__(api_key=api_key, base_url=base_url, model=model)
                self._inference_llm = InferenceNetLLM(api_key=api_key, base_url=base_url, model=model)
            
            @property
            def metadata(self):
                from llama_index.core.llms import LLMMetadata
                return LLMMetadata(
                    model_name=self.model,
                    is_chat_model=True,
                    is_function_calling_model=True,  # This is the key!
                    context_window=4096
                )
            
            def complete(self, prompt: str, **kwargs):
                response = self._inference_llm.complete(prompt)
                return response
            
            def stream_complete(self, prompt: str, **kwargs):
                response = self._inference_llm.complete(prompt)
                yield response
            
            async def astream_chat_with_tools(
                self,
                tools: list,
                chat_history: Optional[list] = None,
                **kwargs
            ):
                # Convert chat history to a single prompt for the inference LLM
                if chat_history:
                    prompt = "\n".join([msg.content for msg in chat_history])
                else:
                    prompt = "Please provide a query."
                
                response = self._inference_llm.complete(prompt)
                # Return as an async generator as expected by LlamaIndex
                yield response
        
        llm = FunctionCallingInferenceNetLLM(api_key=api_key, base_url=base_url, model=model)
        
        # Create a simple ReActAgent that doesn't require streaming
        from llama_index.core.agent import ReActAgent
        
        agent = ReActAgent(
            tools=[multiply_tool, search_tool],
            llm=llm,
            system_prompt="You are a helpful assistant that can multiply numbers and search the web."
        )
        
        print("   ✅ FunctionAgent created successfully")
        
        # Test the agent
        print("\n2. Testing agent.run() method...")
        response = await agent.run("What is 1234 * 4567?")
        print(f"   Response: {response}")
        
        print("\n3. Testing web search...")
        response = await agent.run("Search for information about Python programming", max_iterations=50)
        print(f"   Response: {response}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_function_agent())
