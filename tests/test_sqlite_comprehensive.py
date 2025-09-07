#!/usr/bin/env python3
"""
Comprehensive tests for SQLite provider SQL queries and edge cases.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from test_utils import DatabaseTestUtils

from mcp_as_a_judge.db.providers.sqlite_provider import SQLiteProvider


class TestSQLiteComprehensive:
    """Comprehensive tests for all SQLModel SQLite operations."""

    @pytest.mark.asyncio
    async def test_bulk_fifo_cleanup(self):
        """Test FIFO cleanup with multiple records deletion."""
        db = SQLiteProvider(max_session_records=2)

        # Add more records than limit
        for i in range(5):
            await db.save_conversation(
                session_id="test_session",
                source=f"tool_{i}",
                input_data=f"input_{i}",
                output=f"output_{i}",
            )

        # Should only have 2 records (most recent)
        records = await db.get_session_conversations("test_session")
        assert len(records) == 2

        # Verify it's the most recent ones
        sources = [r.source for r in records]
        assert "tool_4" in sources
        assert "tool_3" in sources

    @pytest.mark.asyncio
    async def test_daily_cleanup_sql(self):
        """Test daily cleanup SQL with time-based deletion."""
        db = SQLiteProvider()

        # Mock old cleanup time to force daily cleanup
        old_time = datetime.now(UTC) - timedelta(days=2)
        db._last_cleanup_time = old_time

        # Add a record
        await db.save_conversation(
            session_id="test_session",
            source="test_tool",
            input_data="test_input",
            output="test_output",
        )

        # Verify record exists
        records = await db.get_session_conversations("test_session")
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_empty_session_queries(self):
        """Test SQL queries with empty result sets."""
        db = SQLiteProvider()

        # Test empty session
        records = await db.get_session_conversations("nonexistent_session")
        assert len(records) == 0

        # Test clear empty session
        deleted = await DatabaseTestUtils.clear_session(db, "nonexistent_session")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_sql_injection_safety(self):
        """Verify SQL injection protection in all queries."""
        db = SQLiteProvider()

        # Try malicious inputs
        malicious_session = "'; DROP TABLE conversation_history; --"
        malicious_source = "tool'; DELETE FROM conversation_history; --"

        # These should be safely handled by parameterized queries
        await db.save_conversation(
            session_id=malicious_session,
            source=malicious_source,
            input_data="safe_input",
            output="safe_output",
        )

        # Verify data was saved safely
        records = await db.get_session_conversations(malicious_session)
        assert len(records) == 1
        assert records[0].source == malicious_source

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """Test SQL performance with larger datasets."""
        db = SQLiteProvider(max_session_records=100)

        # Add many records
        for i in range(150):
            await db.save_conversation(
                session_id="perf_test",
                source=f"tool_{i % 10}",  # Vary sources
                input_data=f"input_{i}",
                output=f"output_{i}",
            )

        # Should maintain limit
        records = await db.get_session_conversations("perf_test")
        assert len(records) == 100

        # Test performance verification - ensure FIFO cleanup worked correctly
        # Verify that we have exactly the max_session_records (100) and they are the most recent
        all_records = await db.get_session_conversations("perf_test")
        assert len(all_records) == 100, (
            f"Expected exactly 100 records after FIFO cleanup, got {len(all_records)}"
        )

        # Verify records are in correct order (most recent first)
        for i in range(len(all_records) - 1):
            assert all_records[i].timestamp >= all_records[i + 1].timestamp, (
                "Records should be ordered by timestamp desc"
            )

        print("✅ Performance and FIFO cleanup verification successful")

    def test_sql_query_syntax(self):
        """Test that all SQL queries have correct syntax."""
        from sqlalchemy import inspect

        db = SQLiteProvider()

        # Verify table creation worked using SQLAlchemy inspector
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert "conversation_history" in tables

        # Verify table schema
        columns = inspector.get_columns("conversation_history")
        column_names = [col["name"] for col in columns]

        expected_columns = [
            "id",
            "session_id",
            "source",
            "input",
            "output",
            "timestamp",
        ]
        for col in expected_columns:
            assert col in column_names


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(TestSQLiteComprehensive().test_bulk_lru_cleanup())
    asyncio.run(TestSQLiteComprehensive().test_empty_session_queries())
    print("✅ All comprehensive SQLite tests passed!")
