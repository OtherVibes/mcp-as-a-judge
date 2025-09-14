#!/usr/bin/env python3
"""
Rate Limit Handling Demo for MCP as a Judge

This script demonstrates the rate limit handling functionality with exponential backoff
using tenacity decorators in the LLM client.
"""

import asyncio
from unittest.mock import patch

import litellm

from mcp_as_a_judge.llm.llm_client import LLMClient
from mcp_as_a_judge.llm.llm_integration import LLMConfig, LLMVendor


async def demo_rate_limit_handling():
    """Demonstrate rate limit handling with exponential backoff."""
    print("🚀 Rate Limit Handling Demo")
    print("=" * 50)

    # Create a test LLM configuration
    config = LLMConfig(
        api_key="demo-key",
        model_name="gpt-4",
        vendor=LLMVendor.OPENAI,
        max_tokens=1000,
        temperature=0.1,
    )

    client = LLMClient(config)

    print("📝 Test 1: Successful retry after rate limit errors")
    print("-" * 50)

    # Mock response for successful case
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Success after retries!"

    # Simulate rate limit errors followed by success
    with patch.object(client, "_litellm") as mock_litellm:
        mock_litellm.completion.side_effect = [
            litellm.RateLimitError("Rate limit exceeded", "openai", "gpt-4"),
            litellm.RateLimitError("Rate limit exceeded", "openai", "gpt-4"),
            mock_response,  # Success on third attempt
        ]

        messages = [{"role": "user", "content": "Hello, world!"}]

        try:
            result = await client.generate_text(messages)
            print(f"✅ Success: {result}")
            print(f"📊 Total attempts: {mock_litellm.completion.call_count}")
        except Exception as e:
            print(f"❌ Failed: {e}")

    print("\n📝 Test 2: Rate limit exhaustion (all retries fail)")
    print("-" * 50)

    # Simulate persistent rate limit errors
    with patch.object(client, "_litellm") as mock_litellm:
        mock_litellm.completion.side_effect = litellm.RateLimitError(
            "Rate limit exceeded", "openai", "gpt-4"
        )

        messages = [{"role": "user", "content": "This will fail"}]

        try:
            result = await client.generate_text(messages)
            print(f"✅ Unexpected success: {result}")
        except Exception as e:
            print(f"❌ Expected failure after retries: {e}")
            print(f"📊 Total attempts: {mock_litellm.completion.call_count}")

    print("\n📝 Test 3: Non-rate-limit error (no retries)")
    print("-" * 50)

    # Simulate a different type of error
    with patch.object(client, "_litellm") as mock_litellm:
        mock_litellm.completion.side_effect = ValueError("Invalid input")

        messages = [{"role": "user", "content": "This will fail immediately"}]

        try:
            result = await client.generate_text(messages)
            print(f"✅ Unexpected success: {result}")
        except Exception as e:
            print(f"❌ Expected immediate failure: {e}")
            print(f"📊 Total attempts: {mock_litellm.completion.call_count}")

    print("\n🎯 Rate Limit Configuration")
    print("-" * 50)
    print("• Max retries: 5 attempts")
    print("• Base delay: 2 seconds")
    print("• Max delay: 120 seconds")
    print("• Exponential base: 2.0")
    print("• Jitter: Enabled (±20%)")
    print("\nDelay pattern: ~2s, ~4s, ~8s, ~16s, ~32s")

    print("\n✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_rate_limit_handling())
