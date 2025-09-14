"""
LLM client module using LiteLLM for MCP as a Judge.

This module provides the actual LLM client implementation using LiteLLM
to support multiple providers as a fallback when MCP sampling is not available.
"""

import asyncio
from typing import Any

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mcp_as_a_judge.core.constants import DEFAULT_REASONING_EFFORT
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.llm.llm_integration import LLMConfig, LLMVendor

litellm.drop_params = True
litellm.suppress_debug_info = True
litellm.set_verbose = False

# Set up logger
logger = get_logger(__name__)


class LLMClient:
    """LLM client using LiteLLM for multiple provider support."""

    def __init__(self, config: LLMConfig):
        """Initialize LLM client with configuration.

        Args:
            config: LLM configuration including API key and model settings
        """
        self.config = config
        self._litellm: Any = None
        self._initialize_litellm()

    def _initialize_litellm(self) -> None:
        """Initialize LiteLLM with lazy loading."""
        try:
            self._litellm = litellm

            # Set API key based on vendor
            if self.config.api_key:
                self._set_api_key_for_vendor()

        except ImportError as e:
            raise ImportError(
                "LiteLLM is required for LLM fallback functionality. "
                "Install it with: pip install litellm"
            ) from e

    def _set_api_key_for_vendor(self) -> None:
        """Set the appropriate API key for the detected vendor."""
        if not self._litellm or not self.config.api_key:
            return

        vendor = self.config.vendor
        api_key = self.config.api_key

        # Set vendor-specific API key
        if vendor == LLMVendor.OPENAI:
            self._litellm.openai_key = api_key
        elif vendor == LLMVendor.ANTHROPIC:
            self._litellm.anthropic_key = api_key
        elif vendor == LLMVendor.GOOGLE:
            self._litellm.gemini_key = api_key
        elif vendor == LLMVendor.GROQ:
            self._litellm.groq_key = api_key
        elif vendor == LLMVendor.XAI:
            self._litellm.xai_key = api_key
        elif vendor == LLMVendor.MISTRAL:
            self._litellm.mistral_key = api_key
        elif vendor == LLMVendor.OPENROUTER:
            self._litellm.openrouter_key = api_key
        elif vendor == LLMVendor.AZURE:
            # Azure might need additional configuration
            self._litellm.azure_key = api_key
        elif vendor == LLMVendor.AWS_BEDROCK:
            # AWS Bedrock uses AWS credentials
            self._litellm.aws_access_key_id = api_key
        elif vendor == LLMVendor.VERTEX_AI:
            # Vertex AI uses service account JSON
            self._litellm.vertex_ai_key = api_key
        else:
            # Fallback to generic API key
            self._litellm.api_key = api_key

    def _get_model_name(self) -> str:
        """Get the full model name with vendor prefix for LiteLLM."""
        if not self.config.model_name:
            raise ValueError("Model name is required")

        vendor = self.config.vendor
        model_name = self.config.model_name

        # Add vendor prefix if not already present
        if vendor == LLMVendor.OPENAI and not model_name.startswith("openai/"):
            return f"openai/{model_name}"
        elif vendor == LLMVendor.ANTHROPIC and not model_name.startswith("anthropic/"):
            return f"anthropic/{model_name}"
        elif vendor == LLMVendor.GOOGLE and not model_name.startswith("gemini/"):
            return f"gemini/{model_name}"
        elif vendor == LLMVendor.GROQ and not model_name.startswith("groq/"):
            return f"groq/{model_name}"
        elif vendor == LLMVendor.XAI and not model_name.startswith("xai/"):
            return f"xai/{model_name}"
        elif vendor == LLMVendor.MISTRAL and not model_name.startswith("mistral/"):
            return f"mistral/{model_name}"
        elif vendor == LLMVendor.OPENROUTER and not model_name.startswith(
            "openrouter/"
        ):
            return f"openrouter/{model_name}"
        elif vendor == LLMVendor.AZURE and not model_name.startswith("azure/"):
            return f"azure/{model_name}"
        elif vendor == LLMVendor.AWS_BEDROCK and not model_name.startswith("bedrock/"):
            return f"bedrock/{model_name}"
        elif vendor == LLMVendor.VERTEX_AI and not model_name.startswith("vertex_ai/"):
            return f"vertex_ai/{model_name}"

        return model_name

    @retry(
        retry=retry_if_exception_type(litellm.RateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=120),
        reraise=True,
    )
    async def _generate_text_with_retry(self, completion_params: dict[str, Any]) -> Any:
        """Generate text with retry logic for rate limit errors.

        This method is decorated with tenacity retry logic to handle
        litellm.RateLimitError with exponential backoff.

        Args:
            completion_params: Parameters for LiteLLM completion

        Returns:
            LiteLLM response object

        Raises:
            litellm.RateLimitError: If rate limit is exceeded after all retries
            Exception: For other LiteLLM errors
        """
        logger.debug(
            f"Attempting LLM completion with model: {completion_params.get('model')}"
        )

        # Run the synchronous LiteLLM call in a thread pool
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._litellm.completion(**completion_params)
        )

        logger.debug("LLM completion successful")
        return response

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using LiteLLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate (uses config default if not provided)
            temperature: Temperature for generation (uses config default if not provided)
            **kwargs: Additional arguments for LiteLLM

        Returns:
            Generated text response

        Raises:
            Exception: If LLM generation fails
        """
        if not self._litellm:
            raise RuntimeError("LiteLLM not initialized")

        if not self.config.api_key:
            raise ValueError("API key is required for LLM generation")

        # Use config defaults if not provided
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature

        try:
            model_name = self._get_model_name()

            # Build completion parameters
            completion_params = {
                "model": model_name,
                "messages": messages,
                "api_key": self.config.api_key,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "reasoning_effort": DEFAULT_REASONING_EFFORT,  # Set reasoning to lowest level
                **kwargs,
            }

            # Add JSON response format if requested
            if kwargs.get("response_format") == "json":
                completion_params["response_format"] = {"type": "json_object"}

            # Use retry helper for rate limit handling
            response = await self._generate_text_with_retry(completion_params)

            # Extract text from response
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    content = choice.message.content

                    # Handle empty responses
                    if not content or len(content.strip()) == 0:
                        raise ValueError("Empty response from LLM")

                    return str(content)

            raise ValueError(
                f"Unexpected response format from LLM. Response: {response}"
            )

        except litellm.RateLimitError as e:
            # Rate limit error with specific handling
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise Exception(f"LLM generation failed due to rate limiting: {e}") from e
        except Exception as e:
            # Other errors
            logger.error(f"LLM generation failed: {e}")
            raise Exception(f"LLM generation failed: {e}") from e

    def is_available(self) -> bool:
        """Check if the LLM client is properly configured and available.

        Returns:
            True if client is available, False otherwise
        """
        return (
            self._litellm is not None
            and self.config.api_key is not None
            and self.config.model_name is not None
        )


class LLMClientManager:
    """Manager for LLM client instances."""

    def __init__(self) -> None:
        """Initialize LLM client manager."""
        self._client: LLMClient | None = None
        self._config: LLMConfig | None = None

    def configure(self, config: LLMConfig) -> None:
        """Configure the LLM client.

        Args:
            config: LLM configuration
        """
        self._config = config
        if config.api_key:
            self._client = LLMClient(config)

    def get_client(self) -> LLMClient | None:
        """Get the configured LLM client.

        Returns:
            LLM client if configured, None otherwise
        """
        return self._client

    def is_available(self) -> bool:
        """Check if LLM client is available.

        Returns:
            True if client is available, False otherwise
        """
        return self._client is not None and self._client.is_available()


# Global LLM client manager instance
llm_manager = LLMClientManager()
