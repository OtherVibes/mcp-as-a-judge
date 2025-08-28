"""
Tests for enhanced MCP as a Judge features.

This module tests the new user requirements alignment and
elicitation functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp_as_a_judge.server import (
    elicit_missing_requirements,
    judge_coding_plan,
    judge_code_change,
    raise_obstacle,
    check_swe_compliance
)
from mcp_as_a_judge.models import JudgeResponse


class TestElicitMissingRequirements:
    """Test the elicit_missing_requirements tool."""
    
    @pytest.mark.asyncio
    async def test_elicit_with_valid_context(self, mock_context_with_sampling):
        """Test eliciting requirements with valid context."""
        result = await elicit_missing_requirements(
            current_request="Build a Slack integration",
            identified_gaps=["What specific functionality?", "What type of integration?"],
            specific_questions=["Send or receive messages?", "Bot or webhook?"],
            ctx=mock_context_with_sampling
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
            ctx=mock_context_without_sampling
        )
        
        assert "ERROR" in result
        assert "Cannot proceed without clear requirements" in result


class TestUserRequirementsAlignment:
    """Test user requirements alignment in judge tools."""
    
    @pytest.mark.asyncio
    async def test_judge_coding_plan_with_requirements(self, mock_context_with_sampling):
        """Test judge_coding_plan with user_requirements parameter."""
        result = await judge_coding_plan(
            plan="Create Slack MCP server with message sending",
            design="Use slack-sdk library with FastMCP framework",
            research="Analyzed slack-sdk docs and MCP patterns",
            user_requirements="Send CI/CD status updates to Slack channels",
            context="CI/CD integration project",
            ctx=mock_context_with_sampling
        )
        
        assert isinstance(result, JudgeResponse)
        # Should either be approved or have specific feedback about requirements
        if not result.approved:
            assert len(result.required_improvements) > 0
        assert len(result.feedback) > 0
    
    @pytest.mark.asyncio
    async def test_judge_code_change_with_requirements(self, mock_context_with_sampling):
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
            ctx=mock_context_with_sampling
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
            user_requirements="Specific user requirements for testing",
            context="Test context",
            ctx=mock_context_with_sampling
        )

        # The function should either call the LLM or return a response
        assert isinstance(result, JudgeResponse)
        # If sampling was called, verify the prompt contained requirements
        if mock_session.create_message.call_count > 0:
            call_args = mock_session.create_message.call_args
            prompt = call_args[1]['messages'][0]['content']
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
            ctx=mock_context_with_sampling
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
            ctx=mock_context_without_sampling
        )
        
        assert "ERROR" in result
        assert "Cannot resolve obstacle without user input" in result


class TestComplianceCheck:
    """Test the check_swe_compliance tool."""
    
    @pytest.mark.asyncio
    async def test_compliance_check_basic(self):
        """Test basic compliance check functionality."""
        result = await check_swe_compliance(
            task_description="Build a web API using FastAPI framework"
        )

        assert isinstance(result, str)
        assert "SWE Compliance Check" in result
        assert "WORKFLOW FOR PLANNING" in result

    @pytest.mark.asyncio
    async def test_compliance_check_with_context(self):
        """Test compliance check with additional context."""
        result = await check_swe_compliance(
            task_description="Build a secure authentication system using JWT tokens with bcrypt hashing for an e-commerce platform requiring PCI compliance"
        )

        assert isinstance(result, str)
        assert len(result) > 100  # Should provide substantial guidance


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_requirements(self, mock_context_with_sampling):
        """Test complete workflow from compliance check to code evaluation."""
        # Step 1: Check compliance
        compliance_result = await check_swe_compliance(
            task_description="Build Slack integration using MCP server"
        )
        assert "SWE Compliance Check" in compliance_result
        
        # Step 2: Judge plan with requirements
        plan_result = await judge_coding_plan(
            plan="Create Slack MCP server with message capabilities",
            design="Use slack-sdk with FastMCP framework",
            research="Analyzed Slack API and MCP patterns",
            user_requirements="Send automated CI/CD notifications to Slack",
            ctx=mock_context_with_sampling
        )
        assert isinstance(plan_result, JudgeResponse)
        
        # Step 3: Judge code with requirements
        code_result = await judge_code_change(
            code_change="def send_notification(): pass",
            user_requirements="Send automated CI/CD notifications to Slack",
            ctx=mock_context_with_sampling
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
            user_requirements="Test requirements",
            ctx=mock_context_without_sampling
        )
        
        # Should get error response suggesting to use raise_obstacle
        assert isinstance(plan_result, JudgeResponse)
        assert not plan_result.approved
        assert "raise_obstacle" in plan_result.feedback
        
        # Then raise obstacle
        obstacle_result = await raise_obstacle(
            problem="No sampling capability",
            research="Need LLM access for evaluation",
            options=["Use Claude Desktop", "Configure client"],
            ctx=mock_context_without_sampling
        )
        
        assert "ERROR" in obstacle_result
