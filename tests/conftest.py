"""
Test configuration and fixtures for MCP as a Judge.

This module provides pytest fixtures and configuration for testing
the MCP server functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_as_a_judge.models import JudgeResponse


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_mcp_server():
    """Mock MCP server for testing."""
    mock_server = MagicMock()
    mock_server.call_tool = AsyncMock()
    return mock_server


@pytest.fixture
def sample_judge_response():
    """Sample JudgeResponse for testing."""
    return JudgeResponse(
        approved=True,
        required_improvements=[],
        feedback="The plan follows all software engineering best practices.",
    )


@pytest.fixture
def sample_rejected_response():
    """Sample rejected JudgeResponse for testing."""
    return JudgeResponse(
        approved=False,
        required_improvements=[
            "Add comprehensive error handling",
            "Implement input validation",
            "Add unit tests",
        ],
        feedback="The plan needs several improvements before approval.",
    )


@pytest.fixture
def sample_coding_plan():
    """Sample coding plan for testing."""
    return {
        "plan": "Create a REST API with FastAPI for user management",
        "design": "Use FastAPI with SQLAlchemy ORM, PostgreSQL database, JWT authentication",
        "research": "Analyzed FastAPI docs, SQLAlchemy patterns, JWT best practices",
        "user_requirements": "Build a secure user management system with registration and login",
        "context": "Building a web application backend",
    }


@pytest.fixture
def sample_code_change():
    """Sample code change for testing."""
    return {
        "code_change": """
def create_user(user_data: dict) -> User:
    # Validate input
    if not user_data.get('email'):
        raise ValueError("Email is required")

    # Create user
    user = User(**user_data)
    db.session.add(user)
    db.session.commit()
    return user
""",
        "user_requirements": "Create a function to safely create new users with validation",
        "file_path": "app/models/user.py",
        "change_description": "Add user creation function with input validation",
    }


@pytest.fixture
def sample_obstacle():
    """Sample obstacle for testing."""
    return {
        "problem": "Cannot access LLM sampling - client doesn't support it",
        "research": "Researched alternatives: configure client, use different client, mock responses",
        "options": [
            "Configure Cursor to support sampling",
            "Use Claude Desktop instead",
            "Mock the sampling for testing",
            "Cancel the evaluation",
        ],
    }


@pytest.fixture
def sample_missing_requirements():
    """Sample missing requirements scenario for testing."""
    return {
        "current_request": "Build a Slack integration",
        "identified_gaps": [
            "What specific Slack functionality is needed?",
            "What type of integration (bot, app, webhook)?",
            "What are the authentication requirements?",
        ],
        "specific_questions": [
            "Do you want to send messages TO Slack or receive messages FROM Slack?",
            "Should this be a bot that responds to commands?",
            "What user permissions are required?",
        ],
    }


@pytest.fixture
def mock_sampling_context():
    """Mock MCP context with sampling capability."""
    mock_context = MagicMock()
    mock_context.session = MagicMock()
    mock_context.session.create_message = AsyncMock()
    mock_context.session.create_message.return_value = MagicMock(
        content=[MagicMock(text="Mocked LLM response")]
    )
    return mock_context


@pytest.fixture
def mock_no_sampling_context():
    """Mock MCP context without sampling capability."""
    mock_context = MagicMock()
    mock_context.session = None
    return mock_context


class MockServerSession:
    """Mock server session for testing."""

    def __init__(self, has_sampling: bool = True):
        """Initialize mock server session."""
        self.has_sampling = has_sampling

    async def create_message(self, **kwargs):
        """Mock create_message method."""
        if not self.has_sampling:
            raise RuntimeError("Context is not available outside of a request")

        # Return proper JSON response for workflow guidance
        if "workflow" in str(kwargs).lower() or "guidance" in str(kwargs).lower():
            json_response = '{"next_tool": "judge_coding_plan", "reasoning": "Need to validate the coding plan", "preparation_needed": ["Gather requirements", "Research best practices"], "guidance": "Start by analyzing the requirements and creating a comprehensive plan"}'
            # Create a mock that mimics the MCP response structure
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = json_response
            return MagicMock(content=mock_content)

        # Return proper JSON response for judge responses
        json_response = '{"approved": true, "feedback": "Mocked evaluation response"}'
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = json_response
        return MagicMock(content=mock_content)


class MockContext:
    """Mock context for testing."""

    def __init__(self, has_sampling: bool = True):
        """Initialize mock context."""
        if has_sampling:
            self.session = MockServerSession(has_sampling=True)
        else:
            self.session = None


@pytest.fixture
def mock_context_with_sampling():
    """Mock context with sampling capability."""
    return MockContext(has_sampling=True)


@pytest.fixture
def mock_context_without_sampling():
    """Mock context without sampling capability."""
    return MockContext(has_sampling=False)
