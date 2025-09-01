#!/usr/bin/env python3
"""
Check available Qwen models on Hugging Face
"""

import requests
import json

def check_qwen_models():
    """Check what Qwen models are available."""
    print("🔍 Checking available Qwen models...")
    print("=" * 50)
    
    # Try different repository paths
    repos_to_check = [
        "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "TheBloke/Qwen2.5-7B-Instruct-GGUF",
        "Qwen/Qwen2.5-7B-Instruct",
        "TheBloke/Qwen2.5-7B-Instruct"
    ]
    
    for repo in repos_to_check:
        print(f"\n📁 Checking: {repo}")
        try:
            # Get repository info
            url = f"https://huggingface.co/api/repos/{repo}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                repo_info = response.json()
                print(f"✅ Repository exists: {repo}")
                print(f"   - Name: {repo_info.get('name', 'N/A')}")
                print(f"   - Type: {repo_info.get('type', 'N/A')}")
                
                # Try to get files
                files_url = f"https://huggingface.co/api/repos/{repo}/tree/main"
                files_response = requests.get(files_url, timeout=10)
                
                if files_response.status_code == 200:
                    files = files_response.json()
                    print(f"   - Files found: {len(files)}")
                    
                    # Look for GGUF files
                    gguf_files = [f for f in files if f.get('path', '').endswith('.gguf')]
                    if gguf_files:
                        print("   - GGUF files:")
                        for file in gguf_files[:5]:  # Show first 5
                            print(f"     * {file['path']} ({file.get('size', 'N/A')} bytes)")
                        if len(gguf_files) > 5:
                            print(f"     ... and {len(gguf_files) - 5} more")
                    else:
                        print("   - No GGUF files found")
                else:
                    print(f"   - Could not access files: {files_response.status_code}")
                    
            else:
                print(f"❌ Repository not found: {repo}")
                
        except Exception as e:
            print(f"❌ Error checking {repo}: {e}")
    
    print("\n🎯 Recommended approach:")
    print("1. Visit https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF")
    print("2. Look for files ending with .gguf")
    print("3. Choose the precision you want (Q8_0, Q4_K_M, etc.)")
    print("4. Use the exact filename in the download command")

if __name__ == "__main__":
    check_qwen_models()
