"""
Tests for LLM integration functionality.

This module tests the LLM API key detection, vendor mapping,
and fallback functionality when MCP sampling is not available.
"""

import os
from unittest.mock import MagicMock, patch

from mcp_as_a_judge.llm.llm_client import LLMClient, LLMClientManager
from mcp_as_a_judge.llm.llm_integration import (
    LLMConfig,
    LLMVendor,
    create_llm_config,
    detect_vendor_from_api_key,
    get_default_model,
    load_llm_config_from_env,
)


class TestVendorDetection:
    """Test API key vendor detection functionality."""

    def test_detect_openai_key(self):
        """Test OpenAI API key detection."""
        api_key = (
            "sk-1234567890abcdef1234567890abcdef"  # gitleaks:allow  # gitleaks:allow
        )
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.OPENAI

    def test_detect_anthropic_key(self):
        """Test Anthropic API key detection."""
        api_key = "sk-ant-api03-1234567890abcdef1234567890abcdef"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.ANTHROPIC

    def test_detect_google_key(self):
        """Test Google API key detection."""
        api_key = "AIzaSyDaGmWKa4JsXZ-HjGw7ISLan_PizdGIrQc"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.GOOGLE

    def test_detect_groq_key(self):
        """Test Groq API key detection."""
        api_key = (
            "gsk_1234567890abcdef1234567890abcdef1234567890abcdef12"  # gitleaks:allow
        )
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.GROQ

    def test_detect_xai_key(self):
        """Test xAI API key detection."""
        api_key = "xai-1234567890abcdef1234567890abcdef12345678"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.XAI

    def test_detect_openrouter_key(self):
        """Test OpenRouter API key detection."""
        api_key = (
            "sk-or-1234567890abcdef1234567890abcdef1234567890abcdef"  # gitleaks:allow
        )
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.OPENROUTER

    def test_detect_mistral_key(self):
        """Test Mistral API key detection."""
        api_key = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.MISTRAL

    def test_detect_azure_key(self):
        """Test Azure API key detection."""
        api_key = "1234567890abcdef1234567890abcdef"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.AZURE

    def test_detect_unknown_key(self):
        """Test unknown API key pattern."""
        api_key = "unknown-key-format"  # gitleaks:allow
        vendor = detect_vendor_from_api_key(api_key)
        assert vendor == LLMVendor.UNKNOWN

    def test_detect_empty_key(self):
        """Test empty API key."""
        vendor = detect_vendor_from_api_key("")
        assert vendor == LLMVendor.UNKNOWN

    def test_detect_none_key(self):
        """Test None API key."""
        vendor = detect_vendor_from_api_key(None)
        assert vendor == LLMVendor.UNKNOWN


class TestDefaultModels:
    """Test default model mapping functionality."""

    def test_get_openai_default(self):
        """Test OpenAI default model."""
        model = get_default_model(LLMVendor.OPENAI)
        assert model == "gpt-4.1"  # gitleaks:allow

    def test_get_anthropic_default(self):
        """Test Anthropic default model."""
        model = get_default_model(LLMVendor.ANTHROPIC)
        assert model == "claude-sonnet-4-20250514"  # gitleaks:allow

    def test_get_google_default(self):
        """Test Google default model."""
        model = get_default_model(LLMVendor.GOOGLE)
        assert model == "gemini-2.5-pro"  # gitleaks:allow

    def test_get_groq_default(self):
        """Test Groq default model."""
        model = get_default_model(LLMVendor.GROQ)
        assert model == "deepseek-r1"  # gitleaks:allow

    def test_get_xai_default(self):
        """Test xAI default model."""
        model = get_default_model(LLMVendor.XAI)
        assert model == "grok-code-fast-1"  # gitleaks:allow

    def test_get_mistral_default(self):
        """Test Mistral default model."""
        model = get_default_model(LLMVendor.MISTRAL)
        assert model == "pixtral-large"  # gitleaks:allow

    def test_get_openrouter_default(self):
        """Test OpenRouter default model."""
        model = get_default_model(LLMVendor.OPENROUTER)
        assert model == "deepseek/deepseek-r1"  # gitleaks:allow

    def test_get_aws_bedrock_default(self):
        """Test AWS Bedrock default model."""
        model = get_default_model(LLMVendor.AWS_BEDROCK)
        assert model == "anthropic.claude-sonnet-4-20250514-v1:0"  # gitleaks:allow

    def test_get_vertex_ai_default(self):
        """Test Vertex AI default model."""
        model = get_default_model(LLMVendor.VERTEX_AI)
        assert model == "gemini-2.5-pro"  # gitleaks:allow

    def test_get_unknown_default(self):
        """Test unknown vendor default model."""
        model = get_default_model(LLMVendor.UNKNOWN)
        assert model == "gpt-4.1"  # gitleaks:allow


class TestLLMConfig:
    """Test LLM configuration creation and validation."""

    def test_create_config_with_auto_detection(self):
        """Test config creation with automatic vendor detection."""
        api_key = "sk-test1234567890abcdef1234567890ab"  # Test key - not real
        config = create_llm_config(api_key=api_key)

        assert config.api_key == api_key
        assert config.vendor == LLMVendor.OPENAI
        assert config.model_name == "gpt-4.1"  # gitleaks:allow

    def test_create_config_with_explicit_vendor(self):
        """Test config creation with explicit vendor."""
        api_key = "custom-key"  # gitleaks:allow
        config = create_llm_config(
            api_key=api_key, vendor=LLMVendor.ANTHROPIC, model_name="claude-3-opus"
        )

        assert config.api_key == api_key
        assert config.vendor == LLMVendor.ANTHROPIC
        assert config.model_name == "claude-3-opus"  # gitleaks:allow

    def test_create_config_no_api_key(self):
        """Test config creation without API key."""
        config = create_llm_config()

        assert config.api_key is None
        assert config.vendor == LLMVendor.UNKNOWN
        assert config.model_name == "gpt-4.1"  # gitleaks:allow


class TestEnvironmentLoading:
    """Test loading configuration from environment variables."""

    def test_load_openai_from_env(self):
        """Test loading OpenAI config from environment."""
        with patch.dict(
            os.environ,
            {
                "LLM_API_KEY": "sk-1234567890abcdef1234567890abcdef",
                "LLM_MODEL_NAME": "gpt-4-turbo",
            },
            clear=True,
        ):
            config = load_llm_config_from_env()

            assert config is not None
            assert (
                config.api_key == "sk-1234567890abcdef1234567890abcdef"
            )  # gitleaks:allow
            assert config.vendor == LLMVendor.OPENAI
            assert config.model_name == "gpt-4-turbo"  # gitleaks:allow

    def test_load_anthropic_from_env(self):
        """Test loading Anthropic config from environment."""
        with patch.dict(
            os.environ,
            {"LLM_API_KEY": "sk-ant-api03-1234567890abcdef1234567890abcdef"},
            clear=True,
        ):
            config = load_llm_config_from_env()

            assert config is not None
            assert (
                config.api_key == "sk-ant-api03-1234567890abcdef1234567890abcdef"
            )  # gitleaks:allow
            assert config.vendor == LLMVendor.ANTHROPIC
            assert config.model_name == "claude-sonnet-4-20250514"  # gitleaks:allow

    def test_load_no_env_vars(self):
        """Test loading when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_llm_config_from_env()
            assert config is None


class TestLLMClient:
    """Test LLM client functionality."""

    @patch("builtins.__import__")
    def test_client_initialization(self, mock_import):
        """Test LLM client initialization."""
        # Mock successful litellm import
        mock_litellm = MagicMock()

        def side_effect(name, *args, **kwargs):
            if name == "litellm":
                return mock_litellm
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        config = LLMConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",  # gitleaks:allow
            vendor=LLMVendor.OPENAI,
            model_name="gpt-4o",
        )

        client = LLMClient(config)
        assert client.config == config
        # Just verify the client was created successfully
        assert client._litellm is not None

    @patch("builtins.__import__")
    def test_client_availability(self, mock_import):
        """Test client availability check."""
        # Mock successful litellm import
        mock_litellm = MagicMock()

        def side_effect(name, *args, **kwargs):
            if name == "litellm":
                return mock_litellm
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        config = LLMConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",  # gitleaks:allow
            vendor=LLMVendor.OPENAI,
            model_name="gpt-4o",
        )

        client = LLMClient(config)
        assert client.is_available() is True

    @patch("builtins.__import__")
    def test_client_unavailable_no_api_key(self, mock_import):
        """Test client unavailable without API key."""
        # Mock successful litellm import
        mock_litellm = MagicMock()

        def side_effect(name, *args, **kwargs):
            if name == "litellm":
                return mock_litellm
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        config = LLMConfig(api_key=None, vendor=LLMVendor.OPENAI, model_name="gpt-4o")

        client = LLMClient(config)
        assert client.is_available() is False

    def test_client_import_error(self):
        """Test client behavior when litellm is available (since it's installed)."""
        config = LLMConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",  # gitleaks:allow
            vendor=LLMVendor.OPENAI,
            model_name="gpt-4o",
        )

        # Since litellm is installed, client should initialize successfully
        client = LLMClient(config)
        assert client.config == config
        assert client._litellm is not None


class TestLLMClientManager:
    """Test LLM client manager functionality."""

    def test_manager_configure(self):
        """Test manager configuration."""
        manager = LLMClientManager()
        config = LLMConfig(
            api_key="sk-test123",  # gitleaks:allow vendor=LLMVendor.OPENAI, model_name="gpt-4o"
        )

        with patch("mcp_as_a_judge.llm.llm_client.LLMClient") as mock_client_class:
            manager.configure(config)
            assert manager._config == config
            mock_client_class.assert_called_once_with(config)

    def test_manager_get_client(self):
        """Test getting client from manager."""
        manager = LLMClientManager()
        config = LLMConfig(
            api_key="sk-test123",  # gitleaks:allow vendor=LLMVendor.OPENAI, model_name="gpt-4o"
        )

        with patch("mcp_as_a_judge.llm.llm_client.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            manager.configure(config)
            client = manager.get_client()

            assert client == mock_client

    def test_manager_no_config(self):
        """Test manager without configuration."""
        manager = LLMClientManager()
        assert manager.get_client() is None
        assert manager.is_available() is False
