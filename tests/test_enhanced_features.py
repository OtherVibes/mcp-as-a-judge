"""
Tests for enhanced MCP as a Judge features.

This module tests the new user requirements alignment and
elicitation functionality, plus conversation history integration.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_as_a_judge.config import Config
from mcp_as_a_judge.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db import create_database_provider
from mcp_as_a_judge.models import DatabaseConfig, JudgeResponse, WorkflowGuidance
from mcp_as_a_judge.server import (
    build_workflow,
    conversation_service,
    judge_code_change,
    judge_coding_plan,
    raise_missing_requirements,
    raise_obstacle,
)


@pytest.fixture
def test_conversation_service():
    """Create a test conversation history service with in-memory database."""
    config = Config(
        database=DatabaseConfig(
            provider="in_memory",
            url="",
            max_context_records=5,  # Small limit for testing
            context_enrichment_count=3  # Small count for testing
        ),
        enable_llm_fallback=True
    )
    db_provider = create_database_provider(config)
    return ConversationHistoryService(config, db_provider)


@pytest.fixture
def mock_context_with_session():
    """Create a mock context with session_id for conversation history testing."""
    context = MagicMock()
    context.session_id = "test_session_123"

    # Mock sampling capability
    context.session = MagicMock()
    context.session.create_message = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"approved": true, "required_improvements": [], "feedback": "Test feedback"}')]
    ))

    return context


class TestConversationHistoryIntegration:
    """Test conversation history integration with MCP judge tools."""

    @pytest.mark.asyncio
    async def test_conversation_service_initialization(self, test_conversation_service):
        """Test that conversation service initializes correctly."""
        assert test_conversation_service is not None
        assert test_conversation_service.config.database.max_context_records == 5
        assert test_conversation_service.config.database.context_enrichment_count == 3

    @pytest.mark.asyncio
    async def test_judge_coding_plan_saves_conversation_record(self, mock_context_with_session, test_conversation_service):
        """Test that judge_coding_plan saves conversation records."""
        # Replace the global conversation service temporarily
        import mcp_as_a_judge.server as server_module
        original_service = server_module.conversation_service
        server_module.conversation_service = test_conversation_service

        try:
            # Call the tool
            result = await judge_coding_plan(
                plan="Create REST API with FastAPI",
                design="Use FastAPI with SQLAlchemy",
                research="Researched FastAPI best practices",
                research_urls=[
                    "https://fastapi.tiangolo.com/",
                    "https://docs.sqlalchemy.org/",
                    "https://pydantic-docs.helpmanual.io/"
                ],
                user_requirements="Build a user management API",
                ctx=mock_context_with_session
            )

            # Verify result
            assert isinstance(result, JudgeResponse)

            # Verify conversation was saved
            session_records = await test_conversation_service.db.get_session_conversations("test_session_123")
            assert len(session_records) == 1

            record = session_records[0]
            assert record.source == "judge_coding_plan"
            assert "Create REST API with FastAPI" in record.input
            assert record.session_id == "test_session_123"

        finally:
            # Restore original service
            server_module.conversation_service = original_service

    @pytest.mark.asyncio
    async def test_build_workflow_with_conversation_context(self, mock_context_with_session, test_conversation_service):
        """Test that build_workflow uses conversation history for context."""
        # Replace the global conversation service temporarily
        import mcp_as_a_judge.server as server_module
        original_service = server_module.conversation_service
        server_module.conversation_service = test_conversation_service

        try:
            # First, add some conversation history
            await test_conversation_service.save_tool_interaction(
                session_id="test_session_123",
                tool_name="judge_coding_plan",
                tool_input='{"plan": "Previous plan", "user_requirements": "Previous requirements"}',
                tool_output='{"approved": true, "feedback": "Previous plan was good"}',
                context_ids=[]
            )

            # Now call build_workflow - it should load the previous conversation
            result = await build_workflow(
                task_description="Extend the API with authentication",
                ctx=mock_context_with_session
            )

            # Verify result
            assert isinstance(result, WorkflowGuidance)

            # Verify new conversation was saved
            session_records = await test_conversation_service.db.get_session_conversations("test_session_123")
            assert len(session_records) == 2  # Previous + new

            # Find the build_workflow record
            workflow_record = next(r for r in session_records if r.source == "build_workflow")
            assert workflow_record.context == ["test_session_123"]  # Should reference previous conversation

        finally:
            # Restore original service
            server_module.conversation_service = original_service

    @pytest.mark.asyncio
    async def test_lru_cleanup_in_conversation_history(self, mock_context_with_session, test_conversation_service):
        """Test that LRU cleanup works when max_context_records is exceeded."""
        # Replace the global conversation service temporarily
        import mcp_as_a_judge.server as server_module
        original_service = server_module.conversation_service
        server_module.conversation_service = test_conversation_service

        try:
            # Add 6 conversations (exceeds max_context_records=5)
            for i in range(6):
                await judge_coding_plan(
                    plan=f"Plan {i+1}",
                    design=f"Design {i+1}",
                    research=f"Research {i+1}",
                    research_urls=[
                        "https://example1.com/",
                        "https://example2.com/",
                        "https://example3.com/"
                    ],
                    user_requirements=f"Requirements {i+1}",
                    ctx=mock_context_with_session
                )

                # Small delay to ensure different timestamps
                import asyncio
                await asyncio.sleep(0.001)

            # Verify only 5 records remain (LRU cleanup)
            session_records = await test_conversation_service.db.get_session_conversations("test_session_123")
            assert len(session_records) == 5

            # Verify the oldest record (Plan 1) was removed and newest records remain
            plans_in_records = [record.input for record in session_records]
            assert not any("Plan 1" in plan for plan in plans_in_records)
            assert any("Plan 6" in plan for plan in plans_in_records)

        finally:
            # Restore original service
            server_module.conversation_service = original_service


class TestElicitMissingRequirements:
    """Test the raise_missing_requirements tool."""

    @pytest.mark.asyncio
    async def test_elicit_with_valid_context(self, mock_context_with_sampling):
        """Test eliciting requirements with valid context."""
        result = await raise_missing_requirements(
            current_request="Build a Slack integration",
            identified_gaps=[
                "What specific functionality?",
                "What type of integration?",
            ],
            specific_questions=["Send or receive messages?", "Bot or webhook?"],
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, str)
        # With elicitation provider, we expect either success or fallback message
        assert (
            "REQUIREMENTS CLARIFIED" in result
            or "ERROR" in result
            or "ELICITATION NOT AVAILABLE" in result
        )

    @pytest.mark.asyncio
    async def test_elicit_without_context(self, mock_context_without_sampling):
        """Test eliciting requirements without valid context."""
        result = await raise_missing_requirements(
            current_request="Build a Slack integration",
            identified_gaps=["What specific functionality?"],
            specific_questions=["Send or receive messages?"],
            ctx=mock_context_without_sampling,
        )

        # With LLM-only approach, we expect error when no LLM providers are available
        assert "ERROR: Failed to elicit requirement clarifications" in result
        assert "No messaging providers available" in result


class TestUserRequirementsAlignment:
    """Test user requirements alignment in judge tools."""

    @pytest.mark.asyncio
    async def test_judge_coding_plan_with_requirements(
        self, mock_context_with_sampling
    ):
        """Test judge_coding_plan with user_requirements parameter."""
        result = await judge_coding_plan(
            plan="Create Slack MCP server with message sending",
            design="Use slack-sdk library with FastMCP framework",
            research="Analyzed slack-sdk docs and MCP patterns",
            research_urls=[
                "https://slack.dev/python-slack-sdk/",
                "https://modelcontextprotocol.io/docs/",
            ],
            user_requirements="Send CI/CD status updates to Slack channels",
            context="CI/CD integration project",
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, JudgeResponse)
        # Should either be approved or have specific feedback about requirements
        if not result.approved:
            assert len(result.required_improvements) > 0
        assert len(result.feedback) > 0

    @pytest.mark.asyncio
    async def test_judge_code_change_with_requirements(
        self, mock_context_with_sampling
    ):
        """Test judge_code_change with user_requirements parameter."""
        code = """
def send_slack_message(channel, message):
    client = SlackClient(token=os.getenv('SLACK_TOKEN'))
    return client.chat_postMessage(channel=channel, text=message)
"""

        result = await judge_code_change(
            code_change=code,
            user_requirements="Send CI/CD status updates with different formatting",
            file_path="slack_integration.py",
            change_description="Basic Slack message sending function",
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, JudgeResponse)
        assert len(result.feedback) > 0

    @pytest.mark.asyncio
    async def test_requirements_in_evaluation_prompt(self, mock_context_with_sampling):
        """Test that user requirements are included in evaluation prompts."""
        # Mock the session to capture the prompt
        mock_session = mock_context_with_sampling.session
        mock_session.create_message = AsyncMock()
        mock_session.create_message.return_value = MagicMock(
            content=[MagicMock(text="APPROVED: Requirements well aligned")]
        )

        result = await judge_coding_plan(
            plan="Test plan",
            design="Test design",
            research="Test research",
            research_urls=[
                "https://example.com/docs",
                "https://github.com/example/repo",
                "https://stackoverflow.com/questions/example",
            ],
            user_requirements="Specific user requirements for testing",
            context="Test context",
            ctx=mock_context_with_sampling,
        )

        # The function should either call the LLM or return a response
        assert isinstance(result, JudgeResponse)
        # If sampling was called, verify the prompt contained requirements
        if mock_session.create_message.call_count > 0:
            call_args = mock_session.create_message.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert "USER REQUIREMENTS" in prompt
            assert "Specific user requirements for testing" in prompt


class TestObstacleResolution:
    """Test the raise_obstacle tool."""

    @pytest.mark.asyncio
    async def test_raise_obstacle_with_context(self, mock_context_with_sampling):
        """Test raising obstacle with valid context."""
        result = await raise_obstacle(
            problem="Cannot use LLM sampling",
            research="Researched alternatives",
            options=["Use Claude Desktop", "Configure Cursor", "Cancel"],
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, str)
        # With elicitation provider, we expect either success or fallback message
        assert (
            "OBSTACLE RESOLVED" in result
            or "ERROR" in result
            or "ELICITATION NOT AVAILABLE" in result
        )

    @pytest.mark.asyncio
    async def test_raise_obstacle_without_context(self, mock_context_without_sampling):
        """Test raising obstacle without valid context."""
        result = await raise_obstacle(
            problem="Cannot use LLM sampling",
            research="Researched alternatives",
            options=["Use Claude Desktop", "Cancel"],
            ctx=mock_context_without_sampling,
        )

        # With LLM-only approach, we expect error when no LLM providers are available
        assert "ERROR: Failed to elicit user decision" in result
        assert "No messaging providers available" in result


class TestWorkflowGuidance:
    """Test the build_workflow tool."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_basic(self, mock_context_with_sampling):
        """Test basic workflow guidance functionality."""
        result = await build_workflow(
            task_description="Build a web API using FastAPI framework",
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, WorkflowGuidance)
        assert result.next_tool in [
            "judge_coding_plan",
            "judge_code_change",
            "raise_obstacle",
            "raise_missing_requirements",
        ]
        assert isinstance(result.reasoning, str)
        assert isinstance(result.preparation_needed, list)
        assert isinstance(result.guidance, str)

    @pytest.mark.asyncio
    async def test_workflow_guidance_with_context(self, mock_context_with_sampling):
        """Test workflow guidance with additional context."""
        result = await build_workflow(
            task_description="Create authentication system with JWT tokens",
            context="E-commerce platform with high security requirements",
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, WorkflowGuidance)
        assert len(result.guidance) > 50  # Should provide substantial guidance
        assert result.next_tool in [
            "judge_coding_plan",
            "judge_code_change",
            "raise_obstacle",
            "raise_missing_requirements",
        ]


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_requirements(
        self, mock_context_with_sampling
    ):
        """Test complete workflow from guidance to code evaluation."""
        # Step 1: Get workflow guidance
        guidance_result = await build_workflow(
            task_description="Build Slack integration using MCP server",
            ctx=mock_context_with_sampling,
        )
        assert isinstance(guidance_result, WorkflowGuidance)
        assert guidance_result.next_tool in [
            "judge_coding_plan",
            "judge_code_change",
            "raise_obstacle",
            "raise_missing_requirements",
        ]

        # Step 2: Judge plan with requirements
        plan_result = await judge_coding_plan(
            plan="Create Slack MCP server with message capabilities",
            design="Use slack-sdk with FastMCP framework",
            research="Analyzed Slack API and MCP patterns",
            research_urls=[
                "https://api.slack.com/docs",
                "https://modelcontextprotocol.io/docs/",
                "https://github.com/slackapi/python-slack-sdk",
            ],
            user_requirements="Send automated CI/CD notifications to Slack",
            ctx=mock_context_with_sampling,
        )
        assert isinstance(plan_result, JudgeResponse)

        # Step 3: Judge code with requirements
        code_result = await judge_code_change(
            code_change="def send_notification(): pass",
            user_requirements="Send automated CI/CD notifications to Slack",
            ctx=mock_context_with_sampling,
        )
        assert isinstance(code_result, JudgeResponse)

    @pytest.mark.asyncio
    async def test_obstacle_handling_workflow(self, mock_context_without_sampling):
        """Test workflow when obstacles are encountered."""
        # Try to judge plan without sampling capability
        plan_result = await judge_coding_plan(
            plan="Test plan",
            design="Test design",
            research="Test research",
            research_urls=[
                "https://example.com/docs",
                "https://github.com/example",
                "https://stackoverflow.com/example",
            ],
            user_requirements="Test requirements",
            ctx=mock_context_without_sampling,
        )

        # Should get warning response but still approve for development environment
        assert isinstance(plan_result, JudgeResponse)
        assert plan_result.approved  # Now approves with warning instead of failing
        assert "⚠️" in plan_result.feedback  # Should contain warning symbol

        # Then raise obstacle
        obstacle_result = await raise_obstacle(
            problem="No sampling capability",
            research="Need LLM access for evaluation",
            options=["Use Claude Desktop", "Configure client"],
            ctx=mock_context_without_sampling,
        )

        assert "ERROR" in obstacle_result

    @pytest.mark.asyncio
    async def test_conversation_context_enrichment_workflow(self, mock_context_with_session, test_conversation_service):
        """Test that conversation history enriches subsequent tool calls."""
        # Replace the global conversation service temporarily
        import mcp_as_a_judge.server as server_module
        original_service = server_module.conversation_service
        server_module.conversation_service = test_conversation_service

        try:
            # Step 1: Initial workflow guidance
            workflow_result = await build_workflow(
                task_description="Build user authentication system",
                ctx=mock_context_with_session
            )
            assert isinstance(workflow_result, WorkflowGuidance)

            # Step 2: Judge coding plan - should have context from workflow
            plan_result = await judge_coding_plan(
                plan="Implement JWT-based authentication with bcrypt password hashing",
                design="Use FastAPI with SQLAlchemy and Pydantic models",
                research="Researched JWT libraries and security best practices",
                research_urls=[
                    "https://jwt.io/introduction/",
                    "https://fastapi.tiangolo.com/tutorial/security/",
                    "https://passlib.readthedocs.io/en/stable/"
                ],
                user_requirements="Secure user login and registration system",
                ctx=mock_context_with_session
            )
            assert isinstance(plan_result, JudgeResponse)

            # Step 3: Judge code change - should have context from both previous calls
            code_result = await judge_code_change(
                code_change="def hash_password(password: str) -> str: return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')",
                user_requirements="Secure password hashing for user authentication",
                file_path="auth/password_utils.py",
                change_description="Add secure password hashing function",
                ctx=mock_context_with_session
            )
            assert isinstance(code_result, JudgeResponse)

            # Verify all conversations were saved
            session_records = await test_conversation_service.db.get_session_conversations("test_session_123")
            assert len(session_records) == 3

            # Verify the tools are in the expected order (most recent first)
            tool_names = [record.source for record in session_records]
            assert tool_names == ["judge_code_change", "judge_coding_plan", "build_workflow"]

            # Verify context enrichment - each tool should reference previous conversations
            for i, record in enumerate(session_records):
                if i < len(session_records) - 1:  # Not the first conversation
                    assert len(record.context) > 0, f"Tool {record.source} should have context from previous conversations"

            # Verify session summary
            summary = await test_conversation_service.get_session_summary("test_session_123")
            assert summary["total_interactions"] == 3
            assert summary["tool_usage"]["build_workflow"] == 1
            assert summary["tool_usage"]["judge_coding_plan"] == 1
            assert summary["tool_usage"]["judge_code_change"] == 1

        finally:
            # Restore original service
            server_module.conversation_service = original_service
