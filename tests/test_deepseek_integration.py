"""
Test cases specifically for DeepSeek API integration.
"""

from mcp_as_a_judge.llm.llm_integration import (
    LLMVendor,
    detect_vendor_from_api_key,
    create_llm_config,
    get_default_model
)


def test_detect_deepseek_key():
    """Test detection of DeepSeek API keys."""
    deepseek_key = "sk-12345678901234567890-deeplearning-ai"
    detected_vendor = detect_vendor_from_api_key(deepseek_key)
    assert detected_vendor == LLMVendor.DEEPSEEK


def test_get_deepseek_default():
    """Test getting default model for DeepSeek."""
    default_model = get_default_model(LLMVendor.DEEPSEEK)
    assert default_model == "deepseek-chat"


def test_create_deepseek_config():
    """Test creating LLM config with DeepSeek vendor."""
    api_key = "sk-12345678901234567890-deeplearning-ai"
    config = create_llm_config(api_key=api_key)
    
    # Should auto-detect as DeepSeek
    assert config.vendor == LLMVendor.DEEPSEEK
    assert config.model_name == "deepseek-chat"
    assert config.api_key == api_key


def test_create_deepseek_config_explicit():
    """Test creating LLM config with explicit DeepSeek vendor."""
    api_key = "sk-12345678901234567890-deeplearning-ai"
    config = create_llm_config(api_key=api_key, vendor=LLMVendor.DEEPSEEK)
    
    assert config.vendor == LLMVendor.DEEPSEEK
    assert config.model_name == "deepseek-chat"
    assert config.api_key == api_key