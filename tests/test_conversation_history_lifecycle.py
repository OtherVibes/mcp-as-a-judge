#!/usr/bin/env python3
"""
Comprehensive tests for conversation history lifecycle: save → retrieve → cleanup.
Tests the complete flow of conversation records through the system.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from mcp_as_a_judge.db.providers.sqlite_provider import SQLiteProvider


class TestConversationHistoryLifecycle:
    """Test the complete lifecycle of conversation history records."""

    @pytest.mark.asyncio
    async def test_save_retrieve_fifo_cleanup_lifecycle(self):
        """Test complete lifecycle: save → retrieve → FIFO cleanup."""
        # Create provider with small limit for testing
        db = SQLiteProvider(max_session_records=3)
        session_id = "lifecycle_test_session"

        print("\n🔄 TESTING COMPLETE CONVERSATION HISTORY LIFECYCLE")
        print("=" * 60)

        # PHASE 1: Save initial records (within limit)
        print("📝 PHASE 1: Saving initial records...")
        record_ids = []
        for i in range(3):
            record_id = await db.save_conversation(
                session_id=session_id,
                source=f"tool_{i}",
                input_data=f"Input for tool {i}",
                output=f"Output from tool {i}",
            )
            record_ids.append(record_id)
            print(f"   Saved record {i}: {record_id}")

        # Verify all records are saved
        records = await db.get_session_conversations(session_id)
        assert len(records) == 3, f"Expected 3 records, got {len(records)}"
        print(f"✅ Phase 1: {len(records)} records saved successfully")

        # PHASE 2: Retrieve and verify order
        print("\n📖 PHASE 2: Retrieving and verifying order...")
        records = await db.get_session_conversations(session_id)

        # Records should be in reverse chronological order (newest first)
        sources = [r.source for r in records]
        expected_sources = ["tool_2", "tool_1", "tool_0"]  # Newest first
        assert sources == expected_sources, f"Expected {expected_sources}, got {sources}"

        # Verify timestamps are in descending order
        timestamps = [r.timestamp for r in records]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], "Records should be ordered newest first"

        print(f"✅ Phase 2: Records retrieved in correct order: {sources}")

        # PHASE 3: Trigger FIFO cleanup by adding more records
        print("\n🧹 PHASE 3: Triggering FIFO cleanup...")

        # Add 2 more records (should trigger cleanup of oldest)
        for i in range(3, 5):
            record_id = await db.save_conversation(
                session_id=session_id,
                source=f"tool_{i}",
                input_data=f"Input for tool {i}",
                output=f"Output from tool {i}",
            )
            print(f"   Added record {i}: {record_id}")

        # Verify FIFO cleanup worked
        records = await db.get_session_conversations(session_id)
        assert len(records) == 3, f"Expected 3 records after cleanup, got {len(records)}"

        # Should have the 3 most recent records
        sources = [r.source for r in records]
        expected_sources = ["tool_4", "tool_3", "tool_2"]  # Most recent 3
        assert sources == expected_sources, f"Expected {expected_sources}, got {sources}"

        print(f"✅ Phase 3: FIFO cleanup worked correctly: {sources}")

        # PHASE 4: Verify specific record retrieval
        print("\n🔍 PHASE 4: Verifying record content...")

        # Check that oldest records were actually removed
        all_sources = [r.source for r in records]
        assert "tool_0" not in all_sources, "tool_0 should have been cleaned up"
        assert "tool_1" not in all_sources, "tool_1 should have been cleaned up"
        assert "tool_4" in all_sources, "tool_4 should be present (newest)"

        # Verify record content integrity
        newest_record = records[0]  # Should be tool_4
        assert newest_record.source == "tool_4"
        assert newest_record.input == "Input for tool 4"
        assert newest_record.output == "Output from tool 4"
        assert newest_record.session_id == session_id

        print("✅ Phase 4: Record content verified successfully")

        print("\n🎉 COMPLETE LIFECYCLE TEST PASSED!")
        print("✅ Save: Records saved correctly")
        print("✅ Retrieve: Records retrieved in correct order")
        print("✅ FIFO Cleanup: Oldest records removed when limit exceeded")
        print("✅ Content Integrity: Record data preserved correctly")

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self):
        """Test that FIFO cleanup works independently per session."""
        db = SQLiteProvider(max_session_records=2)

        print("\n🔄 TESTING MULTI-SESSION ISOLATION")
        print("=" * 60)

        # Add records to session A
        for i in range(3):
            await db.save_conversation(
                session_id="session_A",
                source=f"tool_A_{i}",
                input_data=f"Input A {i}",
                output=f"Output A {i}",
            )

        # Add records to session B
        for i in range(4):
            await db.save_conversation(
                session_id="session_B",
                source=f"tool_B_{i}",
                input_data=f"Input B {i}",
                output=f"Output B {i}",
            )

        # Verify session A has only 2 records (FIFO cleanup)
        records_a = await db.get_session_conversations("session_A")
        assert len(records_a) == 2
        sources_a = [r.source for r in records_a]
        assert sources_a == ["tool_A_2", "tool_A_1"]  # Most recent 2

        # Verify session B has only 2 records (FIFO cleanup)
        records_b = await db.get_session_conversations("session_B")
        assert len(records_b) == 2
        sources_b = [r.source for r in records_b]
        assert sources_b == ["tool_B_3", "tool_B_2"]  # Most recent 2

        print("✅ Multi-session isolation: Each session cleaned up independently")
        print(f"   Session A: {sources_a}")
        print(f"   Session B: {sources_b}")

    @pytest.mark.asyncio
    async def test_time_based_cleanup_integration(self):
        """Test integration of FIFO cleanup with time-based cleanup."""
        db = SQLiteProvider(max_session_records=5)

        print("\n🔄 TESTING TIME-BASED CLEANUP INTEGRATION")
        print("=" * 60)

        # Add some records
        for i in range(3):
            await db.save_conversation(
                session_id="time_test_session",
                source=f"tool_{i}",
                input_data=f"Input {i}",
                output=f"Output {i}",
            )

        # Verify records exist
        records_before = await db.get_session_conversations("time_test_session")
        assert len(records_before) == 3
        print(f"✅ Before cleanup: {len(records_before)} records")

        # Force time-based cleanup by mocking old cleanup time
        old_time = datetime.now(UTC) - timedelta(days=2)
        db._last_cleanup_time = old_time

        # Trigger cleanup by adding another record
        await db.save_conversation(
            session_id="time_test_session",
            source="tool_trigger",
            input_data="Trigger cleanup",
            output="Cleanup triggered",
        )

        # Records should still exist (within retention period)
        records_after = await db.get_session_conversations("time_test_session")
        assert len(records_after) == 4
        print(f"✅ After time-based cleanup: {len(records_after)} records (within retention)")

    @pytest.mark.asyncio
    async def test_lru_session_cleanup_lifecycle(self):
        """Test LRU session cleanup: keeps most recently used sessions."""
        # Create provider with small session limit for testing
        db = SQLiteProvider(max_session_records=20)

        # Override session limit for testing (normally 2000)
        db._cleanup_service.max_total_sessions = 3

        print("\n🔄 TESTING LRU SESSION CLEANUP LIFECYCLE")
        print("=" * 60)

        # PHASE 1: Create sessions with different activity patterns
        print("📝 PHASE 1: Creating sessions with different activity patterns...")

        # Session A: Created first, but will be most recently used
        await db.save_conversation("session_A", "tool1", "input1", "output1")
        print("   Session A: Created (oldest creation time)")

        # Session B: Created second
        await db.save_conversation("session_B", "tool1", "input1", "output1")
        print("   Session B: Created")

        # Session C: Created third
        await db.save_conversation("session_C", "tool1", "input1", "output1")
        print("   Session C: Created")

        # Session D: Created fourth
        await db.save_conversation("session_D", "tool1", "input1", "output1")
        print("   Session D: Created")

        # Session E: Created fifth
        await db.save_conversation("session_E", "tool1", "input1", "output1")
        print("   Session E: Created")

        # Add recent activity to Session A (making it most recently used)
        await db.save_conversation(
            session_id="session_A",
            source="tool2",
            input_data="recent_input",
            output="recent_output",
        )
        print("   Session A: Updated with recent activity (most recently used)")

        # Verify all sessions exist
        current_count = db._cleanup_service.get_session_count()
        assert current_count == 5, f"Expected 5 sessions, got {current_count}"
        print(f"✅ Phase 1: {current_count} sessions created successfully")

        # PHASE 2: Test LRU detection
        print("\n🔍 PHASE 2: Testing LRU detection...")

        # Get least recently used sessions (should be B, C - oldest last activity)
        lru_sessions = db._cleanup_service.get_least_recently_used_sessions(2)
        print(f"   LRU sessions to remove: {lru_sessions}")

        # Should be sessions B and C (oldest last activity)
        assert "session_B" in lru_sessions, "Session B should be LRU"
        assert "session_C" in lru_sessions, "Session C should be LRU"
        assert "session_A" not in lru_sessions, "Session A should NOT be LRU (recent activity)"
        print("✅ Phase 2: LRU detection working correctly")

        # PHASE 3: Trigger LRU cleanup
        print("\n🧹 PHASE 3: Triggering LRU session cleanup...")

        # Force cleanup by mocking old cleanup time
        old_time = datetime.now(UTC) - timedelta(days=2)
        db._cleanup_service.last_session_cleanup_time = old_time

        # Trigger cleanup
        deleted_count = db._cleanup_service.cleanup_excess_sessions()
        print(f"   Deleted {deleted_count} records")

        # Verify session count is now at limit
        final_count = db._cleanup_service.get_session_count()
        assert final_count == 3, f"Expected 3 sessions after cleanup, got {final_count}"
        print(f"✅ Phase 3: Session count reduced to {final_count}")

        # PHASE 4: Verify which sessions remain
        print("\n🔍 PHASE 4: Verifying remaining sessions...")

        sessions_to_check = ["session_A", "session_B", "session_C", "session_D", "session_E"]
        remaining_sessions = []
        deleted_sessions = []

        for session_id in sessions_to_check:
            records = await db.get_session_conversations(session_id)
            if records:
                remaining_sessions.append(session_id)
                last_activity = max(r.timestamp for r in records)
                print(f"   ✅ {session_id}: {len(records)} records, last activity: {last_activity}")
            else:
                deleted_sessions.append(session_id)
                print(f"   ❌ {session_id}: DELETED (was least recently used)")

        # Verify correct sessions were kept/deleted
        assert "session_A" in remaining_sessions, "Session A should remain (most recent activity)"
        assert "session_D" in remaining_sessions, "Session D should remain (recent creation)"
        assert "session_E" in remaining_sessions, "Session E should remain (most recent creation)"
        assert "session_B" in deleted_sessions, "Session B should be deleted (LRU)"
        assert "session_C" in deleted_sessions, "Session C should be deleted (LRU)"

        print("✅ Phase 4: LRU cleanup preserved active sessions correctly")

        # PHASE 5: Verify Session A has both records (original + recent activity)
        print("\n📊 PHASE 5: Verifying session record preservation...")

        session_a_records = await db.get_session_conversations("session_A")
        assert len(session_a_records) == 2, f"Session A should have 2 records, got {len(session_a_records)}"

        # Check that both records exist
        sources = [r.source for r in session_a_records]
        assert "tool1" in sources, "Session A should have original tool1 record"
        assert "tool2" in sources, "Session A should have recent tool2 record"

        print(f"   Session A has {len(session_a_records)} records: {sources}")
        print("✅ Phase 5: Session record preservation working correctly")

        print("\n🎯 LRU CLEANUP SUMMARY:")
        print("   - Sessions B, C deleted (least recently used)")
        print("   - Sessions A, D, E preserved (most recently used)")
        print("   - Session A preserved despite being oldest (recent activity)")
        print("   - LRU provides better UX than FIFO!")
        print("✅ LRU session cleanup lifecycle test PASSED!")

        print("✅ Time-based cleanup integration working correctly")

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_handling(self):
        """Test edge cases in the conversation history lifecycle."""
        db = SQLiteProvider(max_session_records=2)

        print("\n🔄 TESTING EDGE CASES")
        print("=" * 60)

        # Test empty session
        empty_records = await db.get_session_conversations("nonexistent_session")
        assert len(empty_records) == 0
        print("✅ Empty session handling: No records returned")

        # Test single record
        await db.save_conversation(
            session_id="single_record_session",
            source="single_tool",
            input_data="Single input",
            output="Single output",
        )

        single_records = await db.get_session_conversations("single_record_session")
        assert len(single_records) == 1
        assert single_records[0].source == "single_tool"
        print("✅ Single record handling: Correct retrieval")

        # Test exact limit (no cleanup needed)
        for i in range(2):
            await db.save_conversation(
                session_id="exact_limit_session",
                source=f"exact_tool_{i}",
                input_data=f"Exact input {i}",
                output=f"Exact output {i}",
            )

        exact_records = await db.get_session_conversations("exact_limit_session")
        assert len(exact_records) == 2
        print("✅ Exact limit handling: No unnecessary cleanup")

        # Test large input/output data
        large_input = "Large input data " * 100  # ~1700 characters
        large_output = "Large output data " * 100  # ~1800 characters

        await db.save_conversation(
            session_id="large_data_session",
            source="large_tool",
            input_data=large_input,
            output=large_output,
        )

        large_records = await db.get_session_conversations("large_data_session")
        assert len(large_records) == 1
        assert len(large_records[0].input) > 1000
        assert len(large_records[0].output) > 1000
        print("✅ Large data handling: Correct storage and retrieval")

        print("✅ All edge cases handled correctly")


if __name__ == "__main__":
    # Run tests directly for development
    async def run_tests():
        test_instance = TestConversationHistoryLifecycle()
        await test_instance.test_save_retrieve_fifo_cleanup_lifecycle()
        await test_instance.test_multiple_sessions_isolation()
        await test_instance.test_time_based_cleanup_integration()
        await test_instance.test_lru_session_cleanup_lifecycle()
        await test_instance.test_edge_cases_and_error_handling()
        print("\n🎉 ALL CONVERSATION HISTORY LIFECYCLE TESTS PASSED!")

    asyncio.run(run_tests())
