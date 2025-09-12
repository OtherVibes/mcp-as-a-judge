# Rate Limit Handling Implementation

This document describes the rate limit handling implementation added to MCP as a Judge to handle `litellm.RateLimitError` with exponential backoff.

## Overview

The implementation uses the popular `tenacity` library to provide robust retry logic with exponential backoff specifically for rate limit errors from LiteLLM. This addresses the issue where OpenAI and other LLM providers return rate limit errors when token limits are exceeded.

## Implementation Details

### Dependencies Added

- **tenacity>=8.0.0**: Popular Python retry library with decorators

### Files Modified

1. **`pyproject.toml`**: Added tenacity dependency
2. **`src/mcp_as_a_judge/llm/llm_client.py`**: Added rate limit handling with retry logic
3. **`tests/test_rate_limit_handling.py`**: Comprehensive tests for rate limit handling
4. **`examples/rate_limit_demo.py`**: Demonstration script

### Key Features

#### Retry Configuration

```python
@retry(
    retry=retry_if_exception_type(litellm.RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=120),
    reraise=True,
)
```

- **Max retries**: 5 attempts (total of 6 tries including initial)
- **Base delay**: 2 seconds
- **Max delay**: 120 seconds (2 minutes)
- **Exponential multiplier**: 2.0
- **Jitter**: Built into tenacity's exponential wait

#### Delay Pattern

The exponential backoff follows this pattern:
- Attempt 1: Immediate
- Attempt 2: ~2 seconds delay
- Attempt 3: ~4 seconds delay  
- Attempt 4: ~8 seconds delay
- Attempt 5: ~16 seconds delay
- Attempt 6: ~32 seconds delay

Total maximum wait time: ~62 seconds across all retries.

### Error Handling

#### Rate Limit Errors
- **Specific handling**: `litellm.RateLimitError` is caught and retried with exponential backoff
- **Logging**: Each retry attempt is logged with timing information
- **Final failure**: After all retries are exhausted, a clear error message is provided

#### Other Errors
- **No retry**: Non-rate-limit errors (e.g., authentication, validation) fail immediately
- **Preserved behavior**: Existing error handling for other exception types is unchanged

### Code Structure

#### New Method: `_generate_text_with_retry`

```python
@retry(...)
async def _generate_text_with_retry(self, completion_params: dict[str, Any]) -> Any:
    """Generate text with retry logic for rate limit errors."""
```

This method is decorated with tenacity retry logic and handles the actual LiteLLM completion call.

#### Modified Method: `generate_text`

The main `generate_text` method now:
1. Builds completion parameters
2. Calls `_generate_text_with_retry` for the actual LLM call
3. Handles response parsing
4. Provides specific error messages for rate limit vs. other errors

## Usage Examples

### Automatic Retry on Rate Limits

```python
from mcp_as_a_judge.llm.llm_client import LLMClient
from mcp_as_a_judge.llm.llm_integration import LLMConfig, LLMVendor

config = LLMConfig(
    api_key="your-api-key",
    model_name="gpt-4",
    vendor=LLMVendor.OPENAI,
)

client = LLMClient(config)
messages = [{"role": "user", "content": "Hello!"}]

# This will automatically retry on rate limit errors
try:
    response = await client.generate_text(messages)
    print(f"Success: {response}")
except Exception as e:
    print(f"Failed after retries: {e}")
```

### Error Types

#### Rate Limit Error (with retries)
```
ERROR: Rate limit exceeded after retries: litellm.RateLimitError: RateLimitError: OpenAIException - Request too large for gpt-4.1...
```

#### Other Errors (immediate failure)
```
ERROR: LLM generation failed: Invalid API key
```

## Testing

### Test Coverage

The implementation includes comprehensive tests:

1. **Successful retry**: Rate limit errors followed by success
2. **Retry exhaustion**: All retries fail with rate limit errors
3. **Non-retryable errors**: Other errors fail immediately without retries
4. **Successful generation**: Normal operation without retries
5. **Timing verification**: Exponential backoff timing validation

### Running Tests

```bash
# Run rate limit specific tests
uv run pytest tests/test_rate_limit_handling.py -v

# Run all LLM-related tests
uv run pytest tests/ -k "llm" --tb=short

# Run the demo
uv run python examples/rate_limit_demo.py
```

## Benefits

1. **Resilience**: Automatic recovery from temporary rate limit issues
2. **User Experience**: Reduces failed requests due to rate limiting
3. **Efficiency**: Exponential backoff prevents overwhelming the API
4. **Transparency**: Clear logging and error messages
5. **Selective**: Only retries appropriate errors, fails fast on others

## Configuration

The retry behavior is currently hardcoded but can be easily made configurable by:

1. Adding retry settings to `LLMConfig`
2. Passing configuration to the retry decorator
3. Supporting environment variables for retry tuning

## Monitoring

The implementation provides detailed logging:

- Debug logs for each attempt
- Warning logs for retry attempts with timing
- Error logs for final failures
- Success logs when retries succeed

This allows for monitoring and tuning of the retry behavior in production environments.
