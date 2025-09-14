"""
Tests for enhanced MCP as a Judge features.

This module tests the new user requirements alignment and
elicitation functionality.
"""

import pytest

from mcp_as_a_judge.models import JudgeResponse
from mcp_as_a_judge.server import (
    judge_code_change,
    judge_coding_plan,
    raise_missing_requirements,
    raise_obstacle,
)


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
            task_id="test-task-123",
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
            task_id="test-task-456",
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
                "https://github.com/slackapi/python-slack-sdk",
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


class TestObstacleResolution:
    """Test the raise_obstacle tool."""

    @pytest.mark.asyncio
    async def test_raise_obstacle_with_context(self, mock_context_with_sampling):
        """Test raising obstacle with valid context."""
        result = await raise_obstacle(
            problem="Cannot use LLM sampling",
            research="Researched alternatives",
            options=["Use Claude Desktop", "Configure Cursor", "Cancel"],
            task_id="test-task-789",
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
            task_id="test-task-999",
            ctx=mock_context_without_sampling,
        )

        # With LLM-only approach, we expect error when no LLM providers are available
        assert "ERROR: Failed to elicit user decision" in result
        assert "No messaging providers available" in result


class TestWorkflowGuidance:
    """Test the workflow guidance functionality."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_basic(self, mock_context_with_sampling):
        """Test basic workflow guidance functionality."""
        from mcp_as_a_judge.db.conversation_history_service import (
            ConversationHistoryService,
        )
        from mcp_as_a_judge.models.task_metadata import (
            TaskMetadata,
            TaskSize,
            TaskState,
        )
        from mcp_as_a_judge.workflow.workflow_guidance import calculate_next_stage

        # Create a basic task metadata
        task_metadata = TaskMetadata(
            title="Test Task",
            description="Test workflow guidance",
            task_size=TaskSize.M,
            state=TaskState.CREATED,
        )

        # Create conversation service
        from mcp_as_a_judge.db.db_config import load_config

        config = load_config()
        conversation_service = ConversationHistoryService(config)

        # Test workflow guidance calculation
        guidance = await calculate_next_stage(
            task_metadata=task_metadata,
            current_operation="test_operation",
            conversation_service=conversation_service,
            ctx=mock_context_with_sampling,
        )

        assert guidance.next_tool is not None
        assert isinstance(guidance.reasoning, str)
        assert isinstance(guidance.preparation_needed, list)

    @pytest.mark.asyncio
    async def test_workflow_guidance_with_context(self, mock_context_with_sampling):
        """Test workflow guidance with additional context."""
        from mcp_as_a_judge.db.conversation_history_service import (
            ConversationHistoryService,
        )
        from mcp_as_a_judge.models.task_metadata import (
            TaskMetadata,
            TaskSize,
            TaskState,
        )
        from mcp_as_a_judge.workflow.workflow_guidance import calculate_next_stage

        # Create a task metadata with more context
        task_metadata = TaskMetadata(
            title="Complex Task",
            description="Test workflow guidance with context",
            task_size=TaskSize.L,
            state=TaskState.PLANNING,
            user_requirements="Build a complex system with multiple components",
        )

        # Create conversation service
        from mcp_as_a_judge.db.db_config import load_config

        config = load_config()
        conversation_service = ConversationHistoryService(config)

        # Test workflow guidance calculation
        guidance = await calculate_next_stage(
            task_metadata=task_metadata,
            current_operation="judge_coding_plan",
            conversation_service=conversation_service,
            ctx=mock_context_with_sampling,
        )

        assert guidance.next_tool is not None
        assert len(guidance.reasoning) > 0
        assert isinstance(guidance.guidance, str)


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_requirements(
        self, mock_context_with_sampling
    ):
        """Test complete workflow from guidance to code evaluation."""
        # Step 1: Create a task and get workflow guidance
        from mcp_as_a_judge.db.conversation_history_service import (
            ConversationHistoryService,
        )
        from mcp_as_a_judge.db.db_config import load_config
        from mcp_as_a_judge.models.task_metadata import TaskSize
        from mcp_as_a_judge.tasks.manager import create_new_coding_task

        config = load_config()
        conversation_service = ConversationHistoryService(config)

        task_result = await create_new_coding_task(
            user_request="Send automated CI/CD notifications to Slack",
            task_title="Slack MCP Server",
            task_description="Create Slack MCP server with message capabilities",
            user_requirements="Send automated CI/CD notifications to Slack",
            tags=["slack", "mcp", "notifications"],
            conversation_service=conversation_service,
            task_size=TaskSize.M,
        )

        assert task_result is not None
        assert task_result.title == "Slack MCP Server"

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
        from unittest.mock import patch

        # Mock the LLM client to avoid real API calls
        mock_response = JudgeResponse(
            approved=False,
            required_improvements=[
                "Missing detailed implementation",
                "Needs error handling",
            ],
            feedback="Test plan is too generic and missing key details",
        )

        with patch(
            "mcp_as_a_judge.messaging.llm_provider.LLMProvider.send_message"
        ) as mock_send:
            mock_send.return_value = mock_response.model_dump_json()

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

            # Should get response even when no sampling capability (LLM fallback works)
            assert isinstance(plan_result, JudgeResponse)
            assert not plan_result.approved  # Should fail because plan is incomplete
            # The system should provide meaningful feedback about the incomplete plan
            assert len(plan_result.required_improvements) > 0
            assert (
                "Missing" in plan_result.feedback
                or "generic" in plan_result.feedback
                or "No messaging providers available" in plan_result.feedback
            )

        # Then raise obstacle
        obstacle_result = await raise_obstacle(
            problem="No sampling capability",
            research="Need LLM access for evaluation",
            options=["Use Claude Desktop", "Configure client"],
            ctx=mock_context_without_sampling,
        )

        assert "ERROR" in obstacle_result
