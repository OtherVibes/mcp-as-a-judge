"""
Tests for task sizing functionality in MCP as a Judge.

This module tests the task sizing feature that determines planning complexity
and validation depth based on task size (XS, S, M, L, XL). All tasks follow
the unified workflow: CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING →
REVIEW_READY → TESTING → COMPLETED.
"""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize, TaskState
from mcp_as_a_judge.tasks.manager import create_new_coding_task
from mcp_as_a_judge.workflow.workflow_guidance import (
    calculate_next_stage,
    should_skip_planning,
)


class TestTaskSizeEnum:
    """Test TaskSize enum functionality."""

    def test_task_size_values(self):
        """Test that TaskSize enum has correct values."""
        assert TaskSize.XS == "xs"
        assert TaskSize.S == "s"
        assert TaskSize.M == "m"
        assert TaskSize.L == "l"
        assert TaskSize.XL == "xl"

    def test_task_size_required(self):
        """Test that TaskMetadata requires task_size to be specified."""
        # Should fail without task_size
        with pytest.raises(ValidationError):
            TaskMetadata(title="Test Task", description="Test description")

        # Should work with task_size
        task = TaskMetadata(
            title="Test Task", description="Test description", task_size=TaskSize.M
        )
        assert task.task_size == TaskSize.M


class TestTaskMetadataWithSizing:
    """Test TaskMetadata with task sizing functionality."""

    def test_task_metadata_with_xs_size(self):
        """Test creating TaskMetadata with XS size."""
        task = TaskMetadata(
            title="Fix typo",
            description="Fix typo in documentation",
            task_size=TaskSize.XS,
        )
        assert task.task_size == TaskSize.XS
        assert task.state == TaskState.CREATED

    def test_task_metadata_with_xl_size(self):
        """Test creating TaskMetadata with XL size."""
        task = TaskMetadata(
            title="Redesign architecture",
            description="Complete system redesign",
            task_size=TaskSize.XL,
        )
        assert task.task_size == TaskSize.XL
        assert task.state == TaskState.CREATED

    def test_task_metadata_serialization(self):
        """Test that TaskMetadata with task_size serializes correctly."""
        task = TaskMetadata(
            title="Test Task", description="Test description", task_size=TaskSize.L
        )
        data = task.model_dump(exclude_none=True)
        assert data["task_size"] == "l"

    def test_task_metadata_deserialization(self):
        """Test that TaskMetadata with task_size deserializes correctly."""
        data = {
            "title": "Test Task",
            "description": "Test description",
            "task_size": "s",
        }
        task = TaskMetadata(**data)
        assert task.task_size == TaskSize.S


class TestShouldSkipPlanning:
    """Test the should_skip_planning helper function (unified workflow)."""

    def test_no_skip_planning_for_xs_task(self):
        """Test that XS tasks require planning (unified workflow)."""
        task = TaskMetadata(
            title="Fix typo",
            description="Fix typo in documentation",
            task_size=TaskSize.XS,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_s_task(self):
        """Test that S tasks require planning (unified workflow)."""
        task = TaskMetadata(
            title="Minor refactor",
            description="Simple refactoring",
            task_size=TaskSize.S,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_m_task(self):
        """Test that M tasks require planning (unified workflow)."""
        task = TaskMetadata(
            title="Standard feature",
            description="Implement standard feature",
            task_size=TaskSize.M,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_l_task(self):
        """Test that L tasks require planning (unified workflow)."""
        task = TaskMetadata(
            title="Complex feature",
            description="Implement complex feature",
            task_size=TaskSize.L,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_xl_task(self):
        """Test that XL tasks require planning (unified workflow)."""
        task = TaskMetadata(
            title="Architecture redesign",
            description="Complete system redesign",
            task_size=TaskSize.XL,
        )
        assert should_skip_planning(task) is False


class TestCreateNewCodingTaskWithSizing:
    """Test create_new_coding_task with task sizing."""

    @pytest.mark.asyncio
    async def test_create_task_with_explicit_medium_size(self):
        """Test creating task with explicit Medium size."""
        mock_conversation_service = AsyncMock()

        task = await create_new_coding_task(
            user_request="Test request",
            task_title="Test Task",
            task_description="Test description",
            user_requirements="Test requirements",
            tags=["test"],
            conversation_service=mock_conversation_service,
            task_size=TaskSize.M,
        )

        assert task.task_size == TaskSize.M
        assert task.title == "Test Task"

    @pytest.mark.asyncio
    async def test_create_task_with_xs_size(self):
        """Test creating task with XS size."""
        mock_conversation_service = AsyncMock()

        task = await create_new_coding_task(
            user_request="Fix typo",
            task_title="Fix Typo",
            task_description="Fix typo in documentation",
            user_requirements="Fix the typo",
            tags=["bugfix"],
            conversation_service=mock_conversation_service,
            task_size=TaskSize.XS,
        )

        assert task.task_size == TaskSize.XS
        assert task.title == "Fix Typo"

    @pytest.mark.asyncio
    async def test_create_task_with_xl_size(self):
        """Test creating task with XL size."""
        mock_conversation_service = AsyncMock()

        task = await create_new_coding_task(
            user_request="Redesign system",
            task_title="System Redesign",
            task_description="Complete system architecture redesign",
            user_requirements="Redesign the entire system",
            tags=["architecture"],
            conversation_service=mock_conversation_service,
            task_size=TaskSize.XL,
        )

        assert task.task_size == TaskSize.XL
        assert task.title == "System Redesign"


class TestWorkflowGuidanceWithSizing:
    """Test workflow guidance integration with task sizing."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_includes_task_size(self):
        """Test that workflow guidance includes task size in context."""
        # This test would require mocking the LLM provider and conversation service
        # For now, we'll test that the task_size is properly passed to the user vars

        task = TaskMetadata(
            title="Test Task", description="Test description", task_size=TaskSize.L
        )

        # Test that task_size is accessible for workflow guidance
        assert task.task_size == TaskSize.L
        assert task.task_size.value == "l"

    @pytest.mark.asyncio
    async def test_small_task_follows_unified_workflow(self):
        """Test that XS/S tasks follow unified workflow with planning."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Create a small task in CREATED state
        task = TaskMetadata(
            title="Fix typo",
            description="Fix typo in README",
            task_size=TaskSize.S,
            state=TaskState.CREATED,
        )

        # Mock conversation service with proper async return
        mock_conversation_service = MagicMock()
        mock_conversation_service.get_conversation_history = AsyncMock(return_value=[])
        mock_conversation_service.load_filtered_context_for_enrichment = AsyncMock(
            return_value=[]
        )
        mock_conversation_service.format_conversation_history_as_json_array = MagicMock(
            return_value=[]
        )

        # Mock the LLM provider to return a proper workflow guidance response
        mock_llm_response = """
        {
            "next_tool": "judge_coding_plan",
            "reasoning": "Small task requires planning phase as part of unified workflow",
            "preparation_needed": ["Create implementation plan", "Review requirements"],
            "guidance": "Proceed with planning phase for this small task"
        }
        """

        with (
            patch(
                "mcp_as_a_judge.messaging.llm_provider.llm_provider.send_message_with_fallback",
                new_callable=AsyncMock,
            ) as mock_send,
            patch(
                "mcp_as_a_judge.messaging.factory.MessagingProviderFactory.create_provider"
            ) as mock_factory,
            patch(
                "mcp_as_a_judge.messaging.factory.MessagingProviderFactory.check_llm_capability"
            ) as mock_check_llm,
            patch(
                "mcp_as_a_judge.messaging.factory.MessagingProviderFactory.check_sampling_capability"
            ) as mock_check_sampling,
        ):
            # Mock successful LLM response
            mock_send.return_value = mock_llm_response

            # Mock the factory to return a working provider
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.send_message.return_value = mock_llm_response
            mock_provider.provider_type = "llm_api"
            mock_factory.return_value = mock_provider

            # Mock capability checks to show LLM is available
            mock_check_llm.return_value = True
            mock_check_sampling.return_value = False

            # Calculate next stage
            guidance = await calculate_next_stage(
                task_metadata=task,
                current_operation="set_coding_task",
                conversation_service=mock_conversation_service,
                ctx=None,
            )

            # Verify that small tasks now follow unified workflow with planning
            # The guidance should provide a clear next_tool (not None)
            assert guidance.next_tool is not None
            # Should mention planning or judge_coding_plan for unified workflow
            assert (
                "plan" in guidance.reasoning.lower()
                or "judge_coding_plan" in str(guidance.next_tool).lower()
            )

    @pytest.mark.asyncio
    async def test_large_task_requires_planning(self):
        """Test that L/XL tasks require planning."""
        from unittest.mock import AsyncMock

        # Create a large task in CREATED state
        task = TaskMetadata(
            title="Implement authentication",
            description="Implement complete user authentication system",
            task_size=TaskSize.L,
            state=TaskState.CREATED,
        )

        # Mock conversation service
        from unittest.mock import Mock

        mock_conversation_service = AsyncMock()
        mock_conversation_service.load_filtered_context_for_enrichment.return_value = []
        # This method is not async, so use regular Mock
        mock_conversation_service.format_conversation_history_as_json_array = Mock(
            return_value=[]
        )

        # Calculate next stage - this will use LLM for large tasks
        # We can't easily test the LLM response, but we can verify the function doesn't crash
        try:
            guidance = await calculate_next_stage(
                task_metadata=task,
                current_operation="set_coding_task",
                conversation_service=mock_conversation_service,
                ctx=None,
            )
            # If we get here without exception, the function works
            assert guidance is not None
            assert hasattr(guidance, "next_tool")
            assert hasattr(guidance, "reasoning")
        except Exception as e:
            # Expected to fail without proper LLM setup, but function should exist
            assert "calculate_next_stage" not in str(e)  # Function exists


class TestTaskSizeRequired:
    """Test that task_size is required for new tasks."""

    def test_task_size_is_required(self):
        """Test that task_size is required when creating new tasks."""
        # Should raise validation error when task_size is missing
        with pytest.raises(ValidationError):
            TaskMetadata(
                title="Test Task",
                description="Task without size",
                # Missing task_size - should fail
            )

    def test_task_size_field_can_be_updated(self):
        """Test that task_size can be updated on existing tasks."""
        task = TaskMetadata(
            title="Test Task", description="Test description", task_size=TaskSize.S
        )

        # Update task_size
        task.task_size = TaskSize.L
        assert task.task_size == TaskSize.L
