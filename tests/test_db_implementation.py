#!/usr/bin/env python3
"""
Simple test script to verify the SQLite-based in-memory database implementation.
"""

import asyncio

from src.mcp_as_a_judge.db.providers.sqlite import SQLiteProvider


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
        output="The plan looks good with minor improvements needed"
    )
    print(f"Saved record: {record_id1}")
    
    record_id2 = await db.save_conversation(
        session_id="session_123",
        source="judge_code_change",
        input_data="Review this code change",
        output="Code change approved"
    )
    print(f"Saved record: {record_id2}")

    # Test getting session conversations
    print("\n3. Testing get_session_conversations...")
    session_records = await db.get_session_conversations("session_123")
    print(f"Found {len(session_records)} records for session")
    for i, rec in enumerate(session_records):
        print(f"  {i+1}. {rec.source} - {rec.timestamp}")
    
    # Test getting recent conversation IDs
    print("\n4. Testing get_recent_conversations...")
    recent_ids = await db.get_session_conversations("session_123", limit=5)
    print(f"Recent conversation IDs: {recent_ids}")
    
    # Test statistics
    print("\n5. Testing get_stats...")
    stats = db.get_stats()
    print(f"Database stats: {stats}")
    
    # Test deletion
    print("\n6. Testing delete_conversation...")
    deleted = await db.clear_session(record_id1)
    print(f"Deleted record {record_id1}: {deleted}")
    
    # Verify deletion
    remaining_records = await db.get_session_conversations("session_123")
    print(f"Remaining records: {len(remaining_records)}")
    
    # Test clear session
    print("\n7. Testing clear_session...")
    cleared_count = await db.clear_session("session_123")
    print(f"Cleared {cleared_count} records from session")
    
    # Final stats
    final_stats = db.get_stats()
    print(f"Final stats: {final_stats}")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_database_operations())
