#!/usr/bin/env python3
"""
Integration tests for ConversationHistoryService with database providers.
Tests the service layer that sits between the server and database.
"""

import asyncio
import json
from datetime import datetime

import pytest

from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db.db_config import load_config
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize, TaskState
from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history


class TestConversationHistoryServiceIntegration:
    """Test ConversationHistoryService integration with database providers."""

    @pytest.fixture
    def service(self):
        """Create a ConversationHistoryService for testing."""
        config = load_config()
        return ConversationHistoryService(config)

    @pytest.mark.asyncio
    async def test_service_save_and_retrieve_lifecycle(self, service):
        """Test complete service lifecycle: save → retrieve → format."""
        session_id = "service_test_session"

        print("\n🔄 TESTING SERVICE SAVE AND RETRIEVE LIFECYCLE")
        print("=" * 60)

        # PHASE 1: Save conversation records through service
        print("📝 PHASE 1: Saving records through service...")

        record_id1 = await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="judge_coding_plan",
            tool_input="Please review this coding plan for authentication",
            tool_output="The plan looks good. Consider adding 2FA support.",
        )

        record_id2 = await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="judge_code_change",
            tool_input="Review this JWT implementation",
            tool_output="Code change approved. Good security practices.",
        )

        print(f"   Saved record 1: {record_id1}")
        print(f"   Saved record 2: {record_id2}")

        # PHASE 2: Retrieve conversation history
        print("\n📖 PHASE 2: Retrieving conversation history...")

        conversation_history = await service.load_filtered_context_for_enrichment(
            session_id
        )
        assert len(conversation_history) == 2, (
            f"Expected 2 records, got {len(conversation_history)}"
        )

        # Verify order (newest first)
        assert conversation_history[0].source == "judge_code_change"
        assert conversation_history[1].source == "judge_coding_plan"

        print(f"✅ Retrieved {len(conversation_history)} records in correct order")

        # PHASE 3: Format as JSON array for prompt injection
        print("\n🔄 PHASE 3: Formatting as JSON array...")

        json_array = service.format_conversation_history_as_json_array(
            conversation_history
        )
        assert len(json_array) == 2, f"Expected 2 JSON records, got {len(json_array)}"

        # Verify JSON structure
        first_record = json_array[0]
        assert "source" in first_record
        assert "input" in first_record
        assert "output" in first_record
        assert "timestamp" in first_record

        # Verify content
        assert first_record["source"] == "judge_code_change"
        assert first_record["input"] == "Review this JWT implementation"

        print("✅ JSON array formatted correctly with all required fields")
        print(
            f"   Sample record: {first_record['source']} - {first_record['timestamp']}"
        )

        # PHASE 4: Test limit enforcement
        print("\n🔍 PHASE 4: Testing limit enforcement...")

        # Add more records to test limit (we already have 2, so add 25 more to exceed the 20 limit)
        for i in range(25):  # Add many records to test limit
            await service.save_tool_interaction_and_cleanup(
                session_id=session_id,
                tool_name=f"test_tool_{i}",
                tool_input=f"Test input {i}",
                tool_output=f"Test result {i}",
            )

        # Should only get max_session_records (20) records
        limited_history = await service.load_filtered_context_for_enrichment(session_id)
        expected_count = service.config.database.max_session_records
        assert len(limited_history) == expected_count, (
            f"Expected {expected_count} records, got {len(limited_history)}"
        )

        # Should be the most recent records
        sources = [r.source for r in limited_history]
        assert "test_tool_24" in sources, "Most recent record should be present"
        assert "judge_coding_plan" not in sources, "Oldest record should be cleaned up"

        print(
            f"✅ Limit enforcement working: {len(limited_history)} records (limit: {expected_count})"
        )

        print("\n🎉 SERVICE INTEGRATION TEST PASSED!")

    @pytest.mark.asyncio
    async def test_service_with_context_ids(self, service):
        """Test service handling of context IDs for conversation threading."""
        session_id = "context_test_session"

        print("\n🔄 TESTING SERVICE CONTEXT IDS HANDLING")
        print("=" * 60)

        # Save first record
        await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="workflow_guidance",
            tool_input="Help me plan a web application",
            tool_output="I recommend starting with user authentication and database design.",
        )

        # Save second record with context reference
        await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="judge_coding_plan",
            tool_input="Review this authentication plan",
            tool_output="The plan aligns well with the previous guidance.",
        )

        # Save third record with multiple context references
        await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="judge_code_change",
            tool_input="Review authentication implementation",
            tool_output="Implementation follows the approved plan correctly.",
        )

        # Retrieve and verify
        history = await service.load_filtered_context_for_enrichment(session_id)
        assert len(history) == 3

        # Verify the conversation flow makes sense
        sources = [r.source for r in reversed(history)]  # Chronological order
        expected_flow = ["workflow_guidance", "judge_coding_plan", "judge_code_change"]
        assert sources == expected_flow, f"Expected {expected_flow}, got {sources}"

        print("✅ Context IDs handled correctly - conversation flow preserved")

    @pytest.mark.asyncio
    async def test_service_empty_and_error_cases(self, service):
        """Test service behavior with empty sessions and error cases."""
        print("\n🔄 TESTING SERVICE ERROR HANDLING")
        print("=" * 60)

        # Test empty session
        empty_history = await service.load_filtered_context_for_enrichment(
            "nonexistent_session"
        )
        assert len(empty_history) == 0
        print("✅ Empty session handled correctly")

        # Test JSON formatting with empty history
        empty_json = service.format_conversation_history_as_json_array(empty_history)
        assert len(empty_json) == 0
        assert isinstance(empty_json, list)
        print("✅ Empty history JSON formatting handled correctly")

        # Test with special characters in data
        special_session = "special_chars_session"
        await service.save_tool_interaction_and_cleanup(
            session_id=special_session,
            tool_name="test_tool",
            tool_input="Input with 'quotes' and \"double quotes\" and \n newlines",
            tool_output="Result with émojis 🎉 and unicode ñ characters",
        )

        special_history = await service.load_filtered_context_for_enrichment(
            special_session
        )
        assert len(special_history) == 1

        special_json = service.format_conversation_history_as_json_array(
            special_history
        )
        assert len(special_json) == 1
        assert "🎉" in special_json[0]["output"]
        assert "quotes" in special_json[0]["input"]

        print("✅ Special characters handled correctly")

    @pytest.mark.asyncio
    async def test_task_metadata_loader_preserves_canonical_task_id(self, service):
        """Newest snapshots may omit task_id; loader must preserve session identity."""
        session_id = "canonical-task-id-session"

        full_metadata = TaskMetadata(
            task_id=session_id,
            title="Canonical Task",
            description="Ensure task_id stays stable",
            state=TaskState.PLANNING,
            task_size=TaskSize.M,
        )

        await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="set_coding_task",
            tool_input="initial task",
            tool_output=json.dumps(
                {
                    "action": "created",
                    "current_task_metadata": full_metadata.model_dump(mode="json"),
                }
            ),
        )

        trimmed_snapshot = {
            "title": full_metadata.title,
            "description": full_metadata.description,
            "state": TaskState.PLAN_PENDING_APPROVAL.value,
            "task_size": TaskSize.M.value,
            "updated_at": full_metadata.updated_at,
            "tags": [],
        }

        await service.save_tool_interaction_and_cleanup(
            session_id=session_id,
            tool_name="request_plan_approval",
            tool_input="approve plan",
            tool_output=json.dumps(
                {
                    "approved": True,
                    "current_task_metadata": trimmed_snapshot,
                }
            ),
        )

        loaded = await load_task_metadata_from_history(session_id, service)

        assert loaded is not None
        assert loaded.task_id == session_id
        assert loaded.state == TaskState.PLAN_PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_service_performance_with_large_dataset(self, service):
        """Test service performance with larger datasets."""
        session_id = "performance_test_session"

        print("\n🔄 TESTING SERVICE PERFORMANCE")
        print("=" * 60)

        # Add many records quickly
        start_time = datetime.now()

        for i in range(50):
            await service.save_tool_interaction_and_cleanup(
                session_id=session_id,
                tool_name=f"perf_tool_{i % 5}",  # Vary tool names
                tool_input=f"Performance test input {i}",
                tool_output=f"Performance test result {i}",
            )

        save_time = datetime.now() - start_time
        print(f"✅ Saved 50 records in {save_time.total_seconds():.3f} seconds")

        # Retrieve records
        start_time = datetime.now()
        history = await service.load_filtered_context_for_enrichment(session_id)
        retrieve_time = datetime.now() - start_time

        print(
            f"✅ Retrieved {len(history)} records in {retrieve_time.total_seconds():.3f} seconds"
        )

        # Format as JSON
        start_time = datetime.now()
        json_array = service.format_conversation_history_as_json_array(history)
        format_time = datetime.now() - start_time

        print(
            f"✅ Formatted {len(json_array)} records to JSON in {format_time.total_seconds():.3f} seconds"
        )

        # Verify limit was enforced (should be 20, not 50)
        expected_count = service.config.database.max_session_records
        assert len(history) == expected_count, (
            f"Expected {expected_count} records, got {len(history)}"
        )
        assert len(json_array) == expected_count, (
            f"Expected {expected_count} JSON records, got {len(json_array)}"
        )

        print(
            f"✅ Performance test completed - limit enforced: {len(history)}/{expected_count}"
        )


if __name__ == "__main__":
    # Run tests directly for development
    async def run_tests():
        config = load_config()
        service = ConversationHistoryService(config)

        test_instance = TestConversationHistoryServiceIntegration()
        await test_instance.test_service_save_and_retrieve_lifecycle(service)
        await test_instance.test_service_with_context_ids(service)
        await test_instance.test_service_empty_and_error_cases(service)
        await test_instance.test_service_performance_with_large_dataset(service)

        print("\n🎉 ALL SERVICE INTEGRATION TESTS PASSED!")

    asyncio.run(run_tests())
