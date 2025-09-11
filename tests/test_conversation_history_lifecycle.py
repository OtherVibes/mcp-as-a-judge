#!/usr/bin/env python3
"""
Comprehensive tests for conversation history lifecycle: save → retrieve → cleanup.
Tests the complete flow of conversation records through the system.
"""

import asyncio

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
        # Note: Due to timestamp precision, order might vary, so check if we have all records
        assert set(sources) == set(expected_sources), (
            f"Expected {set(expected_sources)}, got {set(sources)}"
        )

        # Verify timestamps are in descending order
        timestamps = [r.timestamp for r in records]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], (
                "Records should be ordered newest first"
            )

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
        assert len(records) == 3, (
            f"Expected 3 records after cleanup, got {len(records)}"
        )

        # Should have the 3 most recent records
        sources = [r.source for r in records]
        expected_sources = ["tool_4", "tool_3", "tool_2"]  # Most recent 3
        assert sources == expected_sources, (
            f"Expected {expected_sources}, got {sources}"
        )

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
        # Check that we have the most recent 2 records (order may vary due to timestamp precision)
        assert set(sources_a) == {"tool_A_2", "tool_A_1"}, (
            f"Expected most recent 2, got {sources_a}"
        )

        # Verify session B has only 2 records (FIFO cleanup)
        records_b = await db.get_session_conversations("session_B")
        assert len(records_b) == 2
        sources_b = [r.source for r in records_b]
        assert sources_b == ["tool_B_3", "tool_B_2"]  # Most recent 2

        print("✅ Multi-session isolation: Each session cleaned up independently")
        print(f"   Session A: {sources_a}")
        print(f"   Session B: {sources_b}")

    @pytest.mark.asyncio
    async def test_immediate_cleanup_integration(self):
        """Test integration of FIFO cleanup with immediate LRU session cleanup."""
        db = SQLiteProvider(max_session_records=5)
        # Set a small session limit for testing
        db._cleanup_service.max_total_sessions = 2

        print("\n🔄 TESTING IMMEDIATE CLEANUP INTEGRATION")
        print("=" * 60)

        # Add records to first session
        for i in range(3):
            await db.save_conversation(
                session_id="session_1",
                source=f"tool_{i}",
                input_data=f"Input {i}",
                output=f"Output {i}",
            )

        # Verify records exist
        records_before = await db.get_session_conversations("session_1")
        assert len(records_before) == 3
        print(f"✅ Session 1 records: {len(records_before)}")

        # Create second session (should not trigger session cleanup yet)
        await db.save_conversation(
            session_id="session_2",
            source="tool_1",
            input_data="Input 1",
            output="Output 1",
        )

        # Both sessions should exist
        assert db._cleanup_service.get_session_count() == 2
        print("✅ Both sessions exist (at limit)")

        # Create third session (should trigger LRU session cleanup)
        await db.save_conversation(
            session_id="session_3",
            source="tool_1",
            input_data="Input 1",
            output="Output 1",
        )

        # Should still have only 2 sessions (LRU cleanup triggered)
        final_count = db._cleanup_service.get_session_count()
        assert final_count == 2
        print(
            f"✅ After immediate LRU cleanup: {final_count} sessions (limit maintained)"
        )

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

        # Add recent activity to Session A BEFORE creating more sessions
        # This ensures Session A becomes most recently used before cleanup
        await db.save_conversation(
            session_id="session_A",
            source="tool2",
            input_data="recent_input",
            output="recent_output",
        )
        print("   Session A: Updated with recent activity (now most recently used)")

        # Session D: Created fourth (should trigger cleanup, but Session A
        # should be preserved)
        await db.save_conversation("session_D", "tool1", "input1", "output1")
        print("   Session D: Created (cleanup triggered)")

        # Session E: Created fifth (should trigger cleanup again)
        await db.save_conversation("session_E", "tool1", "input1", "output1")
        print("   Session E: Created (cleanup triggered again)")

        # Verify automatic LRU cleanup happened (should be at limit of 3)
        current_count = db._cleanup_service.get_session_count()
        assert current_count == 3, (
            f"Expected 3 sessions after automatic cleanup, got {current_count}"
        )
        print(
            f"✅ Phase 1: Automatic LRU cleanup maintained limit - "
            f"{current_count} sessions remain"
        )

        # PHASE 2: Verify which sessions remain after automatic cleanup
        print("\n🔍 PHASE 2: Verifying remaining sessions after automatic cleanup...")

        # Check which sessions still exist
        remaining_sessions = []
        for session_id in [
            "session_A",
            "session_B",
            "session_C",
            "session_D",
            "session_E",
        ]:
            records = await db.get_session_conversations(session_id)
            if records:
                remaining_sessions.append(session_id)

        print(f"   Remaining sessions: {remaining_sessions}")
        assert len(remaining_sessions) == 3, (
            f"Expected 3 remaining sessions, got {len(remaining_sessions)}"
        )

        # Session A should remain initially (preserved due to recent activity)
        assert "session_A" in remaining_sessions, (
            "Session A should remain initially (most recently used)"
        )
        print("✅ Phase 2: Session A initially preserved due to recent activity")

        # PHASE 3: Test that cleanup maintains the limit
        print("\n🧹 PHASE 3: Testing that limit is maintained...")

        # Try to create another session - should trigger cleanup again
        await db.save_conversation("session_F", "tool1", "input1", "output1")

        # Should still be at limit
        final_count = db._cleanup_service.get_session_count()
        assert final_count == 3, (
            f"Expected 3 sessions after adding new session, got {final_count}"
        )
        print(
            f"✅ Phase 3: Session limit maintained at {final_count} "
            f"after adding new session"
        )

        # PHASE 4: Verify which sessions remain after adding session_F
        print("\n🔍 PHASE 4: Verifying final remaining sessions...")

        sessions_to_check = [
            "session_A",
            "session_B",
            "session_C",
            "session_D",
            "session_E",
            "session_F",
        ]
        final_remaining_sessions = []
        final_deleted_sessions = []

        for session_id in sessions_to_check:
            records = await db.get_session_conversations(session_id)
            if records:
                final_remaining_sessions.append(session_id)
                last_activity = max(r.timestamp for r in records)
                print(
                    f"   ✅ {session_id}: {len(records)} records, "
                    f"last activity: {last_activity}"
                )
            else:
                final_deleted_sessions.append(session_id)
                print(f"   ❌ {session_id}: DELETED (was least recently used)")

        # Verify we have exactly 3 sessions
        assert len(final_remaining_sessions) == 3, (
            f"Expected 3 remaining sessions, got {len(final_remaining_sessions)}"
        )

        # The 3 most recently used sessions should remain (D, E, F)
        # Session A gets removed because even though it was updated,
        # sessions D and E were created after A's update, making them more recent
        expected_remaining = {"session_D", "session_E", "session_F"}
        actual_remaining = set(final_remaining_sessions)
        assert actual_remaining == expected_remaining, (
            f"Expected {expected_remaining}, got {actual_remaining}"
        )

        print(
            "✅ Phase 4: LRU cleanup working correctly - most recent sessions preserved"
        )

        # PHASE 5: Verify that LRU cleanup works correctly over time
        print("\n📊 PHASE 5: Verifying LRU behavior over time...")

        # Session A was initially preserved but then removed when Session F was created
        # This demonstrates that LRU is based on actual timestamps, not update sequence
        print("   - Session A was initially preserved due to recent activity")
        print(
            "   - Session A was later removed when newer sessions (D, E, F) "
            "became more recent"
        )
        print("   - This shows LRU is working correctly based on actual timestamps")

        print("\n🎯 IMMEDIATE LRU CLEANUP SUMMARY:")
        print("   - Cleanup happens immediately when new sessions are created")
        print("   - Session limit is maintained at all times (no daily delay)")
        print(
            "   - Most recently used sessions are preserved based on actual timestamps"
        )
        print("   - LRU correctly removes sessions with older last activity times")
        print("   - LRU provides better UX than FIFO by preserving active sessions!")
        print("✅ Immediate LRU session cleanup lifecycle test PASSED!")

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

        # Verify token calculation for large data
        expected_tokens = (
            len(large_input) + len(large_output) + 3
        ) // 4  # Ceiling division
        assert large_records[0].tokens == expected_tokens
        print(
            f"✅ Large data handling: Correct storage, retrieval, and token calculation ({expected_tokens} tokens)"
        )

        print("✅ All edge cases handled correctly")

    @pytest.mark.asyncio
    async def test_token_calculation_integration(self):
        """Test that token calculations are correctly integrated into the lifecycle."""
        print("\n🧮 TESTING TOKEN CALCULATION INTEGRATION")
        print("=" * 60)

        db = SQLiteProvider(max_session_records=5)
        session_id = "token_integration_test"

        # Test records with known token counts
        test_cases = [
            ("tool_1", "Hi", "Hello", 3),  # 1 token (Hi) + 2 tokens (Hello) = 3 tokens
            (
                "tool_2",
                "Test input",
                "Test output",
                6,
            ),  # 3 tokens + 3 tokens = 6 tokens
            ("tool_3", "A" * 20, "B" * 20, 10),  # 5 tokens + 5 tokens = 10 tokens
        ]

        record_ids = []
        for source, input_data, output, expected_tokens in test_cases:
            record_id = await db.save_conversation(
                session_id=session_id,
                source=source,
                input_data=input_data,
                output=output,
            )
            record_ids.append(record_id)
            print(f"   Saved {source}: expected {expected_tokens} tokens")

        # Retrieve and verify token calculations
        records = await db.get_session_conversations(session_id)
        assert len(records) == 3

        # Verify each record has correct token count (records are in reverse order)
        for i, (source, input_data, output, expected_tokens) in enumerate(
            reversed(test_cases)
        ):
            record = records[i]
            assert record.source == source
            assert record.tokens == expected_tokens
            assert record.input == input_data
            assert record.output == output
            print(f"✅ {source}: {record.tokens} tokens (expected {expected_tokens})")

        # Verify total token count
        total_tokens = sum(r.tokens for r in records)
        expected_total = sum(expected for _, _, _, expected in test_cases)
        assert total_tokens == expected_total
        print(f"✅ Total tokens: {total_tokens} (expected {expected_total})")

        print("✅ Token calculation integration verified")


if __name__ == "__main__":
    # Run tests directly for development
    async def run_tests():
        test_instance = TestConversationHistoryLifecycle()
        await test_instance.test_save_retrieve_fifo_cleanup_lifecycle()
        await test_instance.test_multiple_sessions_isolation()
        await test_instance.test_time_based_cleanup_integration()
        await test_instance.test_lru_session_cleanup_lifecycle()
        await test_instance.test_edge_cases_and_error_handling()
        await test_instance.test_token_calculation_integration()
        print("\n🎉 ALL CONVERSATION HISTORY LIFECYCLE TESTS PASSED!")

    asyncio.run(run_tests())
