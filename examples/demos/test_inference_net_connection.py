#!/usr/bin/env python3
"""
Test script to check inference.net connection status and configuration.
"""

import os
import asyncio
import aiohttp
import json
from pathlib import Path
from core.config import ConfigManager
from core.exceptions import ConfigurationError

async def test_inference_net_connection():
    """Test connection to inference.net API."""
    print("🔍 Testing inference.net connection...")
    print("=" * 50)
    
    try:
        # Load configuration
        config = ConfigManager()
        print("✅ Configuration loaded successfully")
        
        # Get inference.net configuration
        api_key = config.get('inference_net_key')
        base_url = config.get('inference_net_base_url')
        model = config.get('inference_net_model')
        
        print(f"📋 Configuration Details:")
        print(f"   Base URL: {base_url}")
        print(f"   Model: {model}")
        print(f"   API Key: {'*' * 8 if api_key else 'NOT SET'}")
        
        if not api_key:
            print("❌ ERROR: INFERENCE_DOT_NET_KEY is not set!")
            print("   Please set the environment variable or add it to your .env file")
            return False
        
        # Test basic connectivity
        print("\n🌐 Testing basic connectivity...")
        async with aiohttp.ClientSession() as session:
            try:
                # Test a simple API call
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Simple test payload
                test_data = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Hello, this is a connection test."}
                    ],
                    "max_tokens": 10
                }
                
                print(f"   Sending test request to: {base_url}/chat/completions")
                
                async with session.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=test_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        print("✅ SUCCESS: Connection to inference.net established!")
                        print("   Server is responding correctly")
                        
                        # Try to get response content
                        try:
                            result = await response.json()
                            print(f"   Response received: {len(str(result))} characters")
                        except:
                            print("   Response received (non-JSON)")
                        
                        return True
                    else:
                        print(f"❌ ERROR: Server returned status {response.status}")
                        try:
                            error_text = await response.text()
                            print(f"   Error details: {error_text[:200]}...")
                        except:
                            print("   Could not read error details")
                        return False
                        
            except aiohttp.ClientError as e:
                print(f"❌ CONNECTION ERROR: {str(e)}")
                return False
            except asyncio.TimeoutError:
                print("❌ TIMEOUT: Request timed out after 30 seconds")
                return False
                
    except ConfigurationError as e:
        print(f"❌ CONFIGURATION ERROR: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        return False

def check_environment_variables():
    """Check what environment variables are currently set."""
    print("\n🔧 Environment Variables Check:")
    print("-" * 30)
    
    env_vars = [
        'INFERENCE_DOT_NET_KEY',
        'INFERENCE_NET_BASE_URL', 
        'INFERENCE_NET_MODEL'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if 'KEY' in var:
                print(f"   {var}: {'*' * 8}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: NOT SET")
    
    # Check for .env file
    env_file = Path('.env')
    if env_file.exists():
        print(f"\n📁 .env file found: {env_file.absolute()}")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                print(f"   Contains {len(lines)} configuration lines")
        except Exception as e:
            print(f"   Error reading .env file: {e}")
    else:
        print(f"\n📁 .env file not found")

async def main():
    """Main test function."""
    print("🚀 AI-Showmaker Inference.net Connection Test")
    print("=" * 60)
    
    # Check environment variables first
    check_environment_variables()
    
    # Test connection
    success = await test_inference_net_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! inference.net is properly connected.")
    else:
        print("💥 Connection test failed. Please check your configuration.")
        print("\n📝 Troubleshooting steps:")
        print("   1. Ensure INFERENCE_DOT_NET_KEY is set")
        print("   2. Check your .env file configuration")
        print("   3. Verify your API key is valid")
        print("   4. Check network connectivity to api.inference.net")

if __name__ == "__main__":
    asyncio.run(main())
