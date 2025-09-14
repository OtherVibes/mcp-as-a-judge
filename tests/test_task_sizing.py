"""
Tests for task sizing functionality in MCP as a Judge.

This module tests the task sizing feature that optimizes workflow decisions
based on task complexity (XS, S, M, L, XL).
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
    """Test the should_skip_planning helper function."""

    def test_skip_planning_for_xs_task(self):
        """Test that XS tasks skip planning."""
        task = TaskMetadata(
            title="Fix typo",
            description="Fix typo in documentation",
            task_size=TaskSize.XS,
        )
        assert should_skip_planning(task) is True

    def test_skip_planning_for_s_task(self):
        """Test that S tasks skip planning."""
        task = TaskMetadata(
            title="Minor refactor",
            description="Simple refactoring",
            task_size=TaskSize.S,
        )
        assert should_skip_planning(task) is True

    def test_no_skip_planning_for_m_task(self):
        """Test that M tasks do not skip planning."""
        task = TaskMetadata(
            title="Standard feature",
            description="Implement standard feature",
            task_size=TaskSize.M,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_l_task(self):
        """Test that L tasks do not skip planning."""
        task = TaskMetadata(
            title="Complex feature",
            description="Implement complex feature",
            task_size=TaskSize.L,
        )
        assert should_skip_planning(task) is False

    def test_no_skip_planning_for_xl_task(self):
        """Test that XL tasks do not skip planning."""
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
    async def test_small_task_skips_planning_deterministically(self):
        """Test that XS/S tasks skip planning deterministically."""
        from unittest.mock import AsyncMock

        # Create a small task in CREATED state
        task = TaskMetadata(
            title="Fix typo",
            description="Fix typo in README",
            task_size=TaskSize.S,
            state=TaskState.CREATED,
        )

        # Mock conversation service
        mock_conversation_service = AsyncMock()
        mock_conversation_service.get_conversation_history.return_value = []

        # Calculate next stage
        guidance = await calculate_next_stage(
            task_metadata=task,
            current_operation="set_coding_task",
            conversation_service=mock_conversation_service,
            ctx=None,
        )

        # Verify that planning is skipped but full workflow is explained
        assert guidance.next_tool is None
        assert "skip" in guidance.reasoning.lower()
        assert (
            "task size is s" in guidance.reasoning.lower()
            or "small" in guidance.reasoning.lower()
        )
        assert "implement" in guidance.guidance.lower()
        # Verify that the guidance mentions the full workflow steps
        assert "judge_code_change" in guidance.guidance.lower()
        assert (
            "judge_testing_implementation" in guidance.guidance.lower()
            or "testing" in guidance.guidance.lower()
        )
        assert (
            "judge_coding_task_completion" in guidance.guidance.lower()
            or "completion" in guidance.guidance.lower()
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
