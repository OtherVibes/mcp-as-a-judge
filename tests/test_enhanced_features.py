"""
Tests for enhanced MCP as a Judge features.

This module tests the new user requirements alignment and
elicitation functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_as_a_judge.models import JudgeResponse, WorkflowGuidance
from mcp_as_a_judge.server import (
    elicit_missing_requirements,
    get_workflow_guidance,
    judge_code_change,
    judge_coding_plan,
    raise_obstacle,
)


class TestElicitMissingRequirements:
    """Test the elicit_missing_requirements tool."""

    @pytest.mark.asyncio
    async def test_elicit_with_valid_context(self, mock_context_with_sampling):
        """Test eliciting requirements with valid context."""
        result = await elicit_missing_requirements(
            current_request="Build a Slack integration",
            identified_gaps=[
                "What specific functionality?",
                "What type of integration?",
            ],
            specific_questions=["Send or receive messages?", "Bot or webhook?"],
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, str)
        assert "REQUIREMENTS CLARIFIED" in result or "ERROR" in result

    @pytest.mark.asyncio
    async def test_elicit_without_context(self, mock_context_without_sampling):
        """Test eliciting requirements without valid context."""
        result = await elicit_missing_requirements(
            current_request="Build a Slack integration",
            identified_gaps=["What specific functionality?"],
            specific_questions=["Send or receive messages?"],
            ctx=mock_context_without_sampling,
        )

        assert "ERROR" in result
        assert "Cannot proceed without clear requirements" in result


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
        assert "OBSTACLE RESOLVED" in result or "ERROR" in result

    @pytest.mark.asyncio
    async def test_raise_obstacle_without_context(self, mock_context_without_sampling):
        """Test raising obstacle without valid context."""
        result = await raise_obstacle(
            problem="Cannot use LLM sampling",
            research="Researched alternatives",
            options=["Use Claude Desktop", "Cancel"],
            ctx=mock_context_without_sampling,
        )

        assert "ERROR" in result
        assert "Cannot resolve obstacle without user input" in result


class TestWorkflowGuidance:
    """Test the get_workflow_guidance tool."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_basic(self, mock_context_with_sampling):
        """Test basic workflow guidance functionality."""
        result = await get_workflow_guidance(
            task_description="Build a web API using FastAPI framework",
            ctx=mock_context_with_sampling,
        )

        assert isinstance(result, WorkflowGuidance)
        assert result.next_tool in [
            "judge_coding_plan",
            "judge_code_change",
            "raise_obstacle",
            "elicit_missing_requirements",
        ]
        assert isinstance(result.reasoning, str)
        assert isinstance(result.preparation_needed, list)
        assert isinstance(result.guidance, str)

    @pytest.mark.asyncio
    async def test_workflow_guidance_with_context(self, mock_context_with_sampling):
        """Test workflow guidance with additional context."""
        result = await get_workflow_guidance(
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
            "elicit_missing_requirements",
        ]


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_requirements(
        self, mock_context_with_sampling
    ):
        """Test complete workflow from guidance to code evaluation."""
        # Step 1: Get workflow guidance
        guidance_result = await get_workflow_guidance(
            task_description="Build Slack integration using MCP server",
            ctx=mock_context_with_sampling,
        )
        assert isinstance(guidance_result, WorkflowGuidance)
        assert guidance_result.next_tool in [
            "judge_coding_plan",
            "judge_code_change",
            "raise_obstacle",
            "elicit_missing_requirements",
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
