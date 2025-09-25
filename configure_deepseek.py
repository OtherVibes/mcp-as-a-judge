#!/usr/bin/env python3
\"\"\"
DeepSeek Configuration Script for MCP as a Judge

This script helps configure MCP as a Judge to use DeepSeek as the LLM provider
by setting up the necessary environment variables.
\"\"\"

import os
import sys
from pathlib import Path

def main():
    print(\"DeepSeek Configuration for MCP as a Judge\")
    print(\"=\"*50)
    
    # Get DeepSeek API key from user
    api_key = input(\"Enter your DeepSeek API key: \").strip()
    
    # Validate the API key format (basic check)
    if not api_key.startswith(\"sk-\") or not api_key.endswith(\"-deeplearning-ai\"):
        print(\"\\n⚠️  Warning: DeepSeek API keys typically start with 'sk-' and end with '-deeplearning-ai'\")
        confirm = input(\"Do you want to continue with this API key? (y/N): \").strip().lower()
        if confirm != 'y':
            print(\"Configuration cancelled.\")
            sys.exit(1)
    
    print(f\"\\nConfiguring MCP as a Judge to use DeepSeek...\")
    
    # Set environment variables
    os.environ['LLM_API_KEY'] = api_key
    os.environ['LLM_MODEL_NAME'] = 'deepseek-chat'  # Default DeepSeek model
    
    print(f\"\\n✅ Environment variables set:\")
    print(f\"   LLM_API_KEY: {'*' * (len(api_key) - 10)}{api_key[-10:]}\"))  # Mask the key
    print(f\"   LLM_MODEL_NAME: deepseek-chat\")
    
    # Show example usage
    print(f\"\\n📝 To use MCP as a Judge with DeepSeek, run:\")
    print(f\"   LLM_API_KEY='{api_key}' LLM_MODEL_NAME='deepseek-chat' uv run mcp-as-a-judge\")
    
    # Or if using Docker:
    print(f\"\\n🐳 For Docker usage:\")
    print(f\"   docker run -e LLM_API_KEY='{api_key}' -e LLM_MODEL_NAME='deepseek-chat' ghcr.io/othervibes/mcp-as-a-judge:latest\")
    
    print(f\"\\n📋 You can also add these to your shell profile (~/.bashrc, ~/.zshrc, etc.):")
    print(f\"   export LLM_API_KEY='{api_key}'\")
    print(f\"   export LLM_MODEL_NAME='deepseek-chat'\")
    
    print(f\"\\n✅ Configuration complete! MCP as a Judge will now use DeepSeek as the LLM provider.\")
    print(f\"   The system will automatically detect your DeepSeek API key and use the 'deepseek-chat' model.\")

if __name__ == \"__main__\":
    main()