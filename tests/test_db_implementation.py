#!/usr/bin/env python3
"""
Simple test script to verify the SQLite-based in-memory database implementation.
"""

import asyncio

from test_utils import DatabaseTestUtils

from mcp_as_a_judge.db.providers.sqlite_provider import SQLiteProvider


async def test_database_operations():
    """Test basic database operations."""
    print("Testing SQLite-based in-memory database...")

    # Create provider
    db = SQLiteProvider()

    # Test saving conversations
    print("\n1. Testing save_conversation...")
    record_id1 = await db.save_conversation(
        session_id="session_123",
        source="judge_coding_plan",
        input_data="Please review this coding plan",
        output="The plan looks good with minor improvements needed",
    )
    print(f"Saved record: {record_id1}")

    record_id2 = await db.save_conversation(
        session_id="session_123",
        source="judge_code_change",
        input_data="Review this code change",
        output="Code change approved",
    )
    print(f"Saved record: {record_id2}")

    # Test getting session conversations
    print("\n3. Testing get_session_conversations...")
    session_records = await db.get_session_conversations("session_123")
    print(f"Found {len(session_records)} records for session")
    for i, rec in enumerate(session_records):
        print(f"  {i + 1}. {rec.source} - {rec.timestamp}")

    # Test getting recent conversation IDs
    print("\n4. Testing get_recent_conversations...")
    recent_ids = await db.get_session_conversations("session_123", limit=5)
    print(f"Recent conversation IDs: {recent_ids}")

    # Test CRUD verification - check that records were actually saved correctly
    print("\n5. Testing CRUD verification...")
    all_records = await db.get_session_conversations("session_123")
    print(f"Retrieved {len(all_records)} records for session")
    assert len(all_records) == 2, f"Expected 2 records, got {len(all_records)}"

    # Verify record content
    assert all_records[0].source == "judge_code_change", (
        "Most recent record should be judge_code_change"
    )
    assert all_records[1].source == "judge_coding_plan", (
        "Older record should be judge_coding_plan"
    )
    assert all_records[0].input == "Review this code change", (
        "Record content should match"
    )
    print("✅ CRUD operations verified successfully")

    # Test deletion
    print("\n6. Testing delete_conversation...")
    deleted = await DatabaseTestUtils.clear_session(db, record_id1)
    print(f"Deleted record {record_id1}: {deleted}")

    # Verify deletion
    remaining_records = await db.get_session_conversations("session_123")
    print(f"Remaining records: {len(remaining_records)}")

    # Test clear session
    print("\n7. Testing clear_session...")
    cleared_count = await DatabaseTestUtils.clear_session(db, "session_123")
    print(f"Cleared {cleared_count} records from session")

    # Final verification - ensure cleanup worked
    final_records = await db.get_session_conversations("session_123")
    print(f"Final verification: {len(final_records)} records remaining")
    assert len(final_records) == 0, (
        f"Expected 0 records after cleanup, got {len(final_records)}"
    )
    print("✅ Cleanup verification successful")

    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_database_operations())
