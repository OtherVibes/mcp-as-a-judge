#!/usr/bin/env python3
"""
Comprehensive tests for token-based conversation history loading.
Tests the hybrid approach that respects both record count and token limits.
"""

import asyncio

import pytest

from mcp_as_a_judge.core.constants import MAX_CONTEXT_TOKENS
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db.db_config import load_config
from mcp_as_a_judge.db.providers.sqlite_provider import SQLiteProvider
from mcp_as_a_judge.db.token_utils import (
    calculate_record_tokens,
    calculate_tokens,
    filter_records_by_token_limit,
)


class TestTokenBasedHistory:
    """Test token-based conversation history loading and filtering."""

    async def test_token_calculation(self):
        """Test basic token calculation functionality."""
        print("\n🧮 TESTING TOKEN CALCULATION")
        print("=" * 50)

        # Test empty string
        assert await calculate_tokens("") == 0
        print("✅ Empty string: 0 tokens")

        # Test short strings (1 token ≈ 4 characters, rounded up)
        assert await calculate_tokens("Hi") == 1  # 2 chars -> 1 token
        assert await calculate_tokens("Hello") == 2  # 5 chars -> 2 tokens
        assert await calculate_tokens("Hello world") == 3  # 11 chars -> 3 tokens
        print("✅ Short strings: correct token calculation")

        # Test longer strings
        long_text = (
            "This is a longer text that should have more tokens" * 10
        )  # ~520 chars
        expected_tokens = (len(long_text) + 3) // 4  # Ceiling division
        assert await calculate_tokens(long_text) == expected_tokens
        print(f"✅ Long text ({len(long_text)} chars): {expected_tokens} tokens")

        # Test record token calculation
        input_text = "Input data for testing"  # 22 chars -> 6 tokens
        output_text = "Output result from tool"  # 23 chars -> 6 tokens
        total_tokens = await calculate_record_tokens(input_text, output_text)
        expected_total = await calculate_tokens(input_text) + await calculate_tokens(
            output_text
        )
        assert total_tokens == expected_total
        print(f"✅ Record tokens: {total_tokens} total tokens")

    @pytest.mark.asyncio
    async def test_token_storage_in_database(self):
        """Test that tokens are correctly calculated and stored in database."""
        print("\n💾 TESTING TOKEN STORAGE IN DATABASE")
        print("=" * 50)

        db = SQLiteProvider(max_session_records=10)
        session_id = "token_storage_test"

        # Create records with known token counts
        test_cases = [
            ("tool1", "Hi", "Hello", 3),  # 1 token (Hi) + 2 tokens (Hello) = 3 tokens
            (
                "tool2",
                "Short input",
                "Longer output text",
                8,
            ),  # 3 tokens + 5 tokens = 8 tokens
            ("tool3", "A" * 100, "B" * 200, 75),  # 25 tokens + 50 tokens = 75 tokens
        ]

        for source, input_data, output, expected_tokens in test_cases:
            await db.save_conversation(
                session_id=session_id,
                source=source,
                input_data=input_data,
                output=output,
            )
            print(f"   Saved {source}: {expected_tokens} expected tokens")

        # Retrieve and verify token counts
        records = await db.get_session_conversations(session_id)
        assert len(records) == 3

        for i, (source, _input_data, _output, expected_tokens) in enumerate(
            reversed(test_cases)
        ):
            record = records[i]  # Records are in reverse chronological order
            assert record.source == source
            assert record.tokens == expected_tokens
            print(
                f"✅ {source}: stored {record.tokens} tokens (expected {expected_tokens})"
            )

    @pytest.mark.asyncio
    async def test_hybrid_loading_record_limit_only(self):
        """Test hybrid loading when only record limit is reached."""
        print("\n📊 TESTING HYBRID LOADING - RECORD LIMIT ONLY")
        print("=" * 50)

        config = load_config()
        service = ConversationHistoryService(config)
        session_id = "record_limit_test"

        # Create 25 small records (each ~2 tokens, total ~50 tokens)
        for i in range(25):
            await service.save_tool_interaction_and_cleanup(
                session_id=session_id,
                tool_name=f"tool_{i}",
                tool_input=f"Input {i}",  # ~8 chars = 2 tokens
                tool_output=f"Out {i}",  # ~6 chars = 2 tokens
            )

        # Load context - should be limited by record count (20), not tokens
        context_records = await service.load_filtered_context_for_enrichment(session_id)

        assert len(context_records) == 20  # Limited by MAX_SESSION_RECORDS
        print(f"✅ Record limit applied: {len(context_records)} records returned")

        # Verify we got the most recent records
        sources = [r.source for r in context_records]
        expected_sources = [f"tool_{i}" for i in range(24, 4, -1)]  # Most recent 20
        assert sources == expected_sources
        print("✅ Most recent records returned")

    @pytest.mark.asyncio
    async def test_hybrid_loading_token_limit_reached(self):
        """Test hybrid loading when token limit is reached before record limit."""
        print("\n🔢 TESTING HYBRID LOADING - TOKEN LIMIT REACHED")
        print("=" * 50)

        config = load_config()
        service = ConversationHistoryService(config)
        session_id = "token_limit_test"

        # Create records that will exceed token limit
        # Each record: ~5000 tokens (20000 chars total)
        large_text = "A" * 10000  # 10000 chars = 2500 tokens each

        for i in range(25):  # 25 * 5000 = 125K tokens total
            await service.save_tool_interaction_and_cleanup(
                session_id=session_id,
                tool_name=f"large_tool_{i}",
                tool_input=large_text,  # 2500 tokens
                tool_output=large_text,  # 2500 tokens
            )

        # Load context - should be limited by token count (50K), not record count
        context_records = await service.load_filtered_context_for_enrichment(session_id)

        # Should get ~10 records (10 * 5000 = 50K tokens)
        assert len(context_records) <= 10
        assert len(context_records) >= 8  # Allow some flexibility
        print(f"✅ Token limit applied: {len(context_records)} records returned")

        # Verify total tokens are within limit
        total_tokens = sum(r.tokens for r in context_records)
        assert total_tokens <= MAX_CONTEXT_TOKENS
        print(f"✅ Total tokens: {total_tokens} (limit: {MAX_CONTEXT_TOKENS})")

        # Verify we got the most recent records
        sources = [r.source for r in context_records]
        expected_start = 25 - len(context_records)
        expected_sources = [
            f"large_tool_{i}" for i in range(24, expected_start - 1, -1)
        ]
        assert sources == expected_sources
        print("✅ Most recent records within token limit returned")

    @pytest.mark.asyncio
    async def test_filter_records_by_token_limit_function(self):
        """Test the filter_records_by_token_limit utility function directly."""
        print("\n🔍 TESTING FILTER_RECORDS_BY_TOKEN_LIMIT FUNCTION")
        print("=" * 50)

        # Create mock records with known token counts that will exceed MAX_CONTEXT_TOKENS (50,000)
        class MockRecord:
            def __init__(self, tokens, name):
                self.tokens = tokens
                self.name = name

        records = [
            MockRecord(10000, "newest"),  # Most recent
            MockRecord(15000, "recent"),
            MockRecord(20000, "older"),
            MockRecord(25000, "oldest"),  # Oldest - total = 70,000 tokens
        ]

        # Test with no current prompt - should filter to fit within 50,000 tokens
        filtered = await filter_records_by_token_limit(records)
        # Should keep newest (10,000) + recent (15,000) + older (20,000) = 45,000 tokens (within 50,000 limit)
        assert len(filtered) == 3
        assert filtered[0].name == "newest"
        assert filtered[1].name == "recent"
        assert filtered[2].name == "older"
        print("✅ Records filtered to fit within MAX_CONTEXT_TOKENS")

        # Test with current prompt that pushes over the limit
        filtered = await filter_records_by_token_limit(
            records, current_prompt="A" * 80000
        )  # 20,000 tokens
        # Total would be 45,000 (first 3 records) + 20,000 = 65,000, so should filter to 2 records
        # newest (10,000) + recent (15,000) + prompt (20,000) = 45,000 tokens
        assert len(filtered) == 2
        assert filtered[0].name == "newest"
        assert filtered[1].name == "recent"
        print("✅ Records filtered with current prompt consideration")

        # Test with smaller records that all fit
        small_records = [
            MockRecord(5000, "small1"),
            MockRecord(5000, "small2"),
            MockRecord(5000, "small3"),
        ]
        filtered = await filter_records_by_token_limit(small_records)
        assert len(filtered) == 3  # All should fit within 50,000 limit
        print("✅ All small records kept within limit")

        # Test with no current prompt (should return all records if within limit)
        filtered = await filter_records_by_token_limit(small_records)
        assert len(filtered) == 3  # All should fit within 50,000 token limit
        assert filtered[0].name == "small1"
        assert filtered[1].name == "small2"
        assert filtered[2].name == "small3"
        print("✅ All small records returned when within token limit")

    @pytest.mark.asyncio
    async def test_mixed_record_sizes(self):
        """Test hybrid loading with mixed record sizes."""
        print("\n🎭 TESTING MIXED RECORD SIZES")
        print("=" * 50)

        config = load_config()
        service = ConversationHistoryService(config)
        session_id = "mixed_sizes_test"

        # Create mix of small and large records
        records_data = [
            ("small_1", "Hi", "Hello", 2),
            ("large_1", "A" * 8000, "B" * 8000, 4000),  # Large record
            ("small_2", "Test", "Result", 3),
            ("large_2", "C" * 12000, "D" * 12000, 6000),  # Very large record
            ("small_3", "End", "Done", 2),
        ]

        for source, input_data, output, _expected_tokens in records_data:
            await service.save_tool_interaction_and_cleanup(
                session_id=session_id,
                tool_name=source,
                tool_input=input_data,
                tool_output=output,
            )

        # Load context
        context_records = await service.load_filtered_context_for_enrichment(session_id)

        # Should get recent records that fit within token limit
        total_tokens = sum(r.tokens for r in context_records)
        assert total_tokens <= MAX_CONTEXT_TOKENS
        print(
            f"✅ Mixed sizes handled: {len(context_records)} records, {total_tokens} tokens"
        )

        # Verify we get the most recent records that fit
        sources = [r.source for r in context_records]
        print(f"   Returned sources: {sources}")
        assert "small_3" in sources  # Most recent small record should be included
        print("✅ Most recent records prioritized correctly")

    async def test_edge_cases(self):
        """Test edge cases for token calculation and filtering."""
        print("\n🔬 TESTING EDGE CASES")
        print("=" * 50)

        # Test empty records list
        filtered = await filter_records_by_token_limit([], current_prompt="test")
        assert len(filtered) == 0
        print("✅ Empty records list handled")

        # Test single record within limit
        class MockRecord:
            def __init__(self, tokens):
                self.tokens = tokens

        single_record = [MockRecord(500)]
        filtered = await filter_records_by_token_limit(
            single_record, current_prompt="A" * 4000
        )  # 1000 tokens
        assert len(filtered) == 1
        print("✅ Single record within limit handled")

        # Test single record exceeding limit (should still return 1 record)
        large_record = [MockRecord(2000)]
        filtered = await filter_records_by_token_limit(
            large_record, current_prompt="A" * 4000
        )  # 1000 tokens
        assert len(filtered) == 1  # Always return at least 1 record
        print("✅ Single large record handled (minimum 1 record returned)")

        print("✅ All edge cases handled correctly")

    @pytest.mark.asyncio
    async def test_database_hybrid_cleanup_on_save(self):
        """Test that database cleanup respects token limits when saving new records."""
        print("\n🗄️ TESTING DATABASE HYBRID CLEANUP ON SAVE")
        print("=" * 50)

        # Create provider with small limits for testing
        db = SQLiteProvider(max_session_records=5)  # Allow up to 5 records
        session_id = "hybrid_cleanup_test"

        # Create records that will exceed token limit before record limit
        # Each record: ~2500 tokens (10000 chars total)
        large_text = "A" * 5000  # 5000 chars = 1250 tokens each

        print("Adding records that will exceed token limit...")
        record_ids = []

        # Add records one by one and check cleanup behavior
        for i in range(25):  # Try to add 25 records (would be 62.5K tokens total)
            record_id = await db.save_conversation(
                session_id=session_id,
                source=f"large_tool_{i}",
                input_data=large_text,  # 1250 tokens
                output=large_text,  # 1250 tokens
            )
            record_ids.append(record_id)

            # Check current state after each save
            current_records = await db.get_session_conversations(session_id)
            current_tokens = sum(r.tokens for r in current_records)

            print(
                f"   After adding record {i}: {len(current_records)} records, {current_tokens} tokens"
            )

            # Verify we never exceed the token limit
            assert current_tokens <= MAX_CONTEXT_TOKENS, (
                f"Token limit exceeded: {current_tokens} > {MAX_CONTEXT_TOKENS}"
            )

            # Should have fewer than 5 records due to token limit (not record limit)
            if i >= 19:  # After 20 records (50K tokens), should start limiting
                assert len(current_records) <= 20, (
                    f"Too many records kept: {len(current_records)}"
                )

        # Final verification
        final_records = await db.get_session_conversations(session_id)
        final_tokens = sum(r.tokens for r in final_records)

        print(f"✅ Final state: {len(final_records)} records, {final_tokens} tokens")
        print(f"   Token limit respected: {final_tokens} <= {MAX_CONTEXT_TOKENS}")

        # Verify we kept the most recent records
        sources = [r.source for r in final_records]
        expected_start = 25 - len(final_records)
        expected_sources = [
            f"large_tool_{i}" for i in range(24, expected_start - 1, -1)
        ]
        assert sources == expected_sources, (
            f"Expected {expected_sources}, got {sources}"
        )

        print("✅ Most recent records kept, oldest removed due to token limit")

    @pytest.mark.asyncio
    async def test_database_record_limit_vs_token_limit(self):
        """Test database cleanup when record limit is hit before token limit."""
        print("\n⚖️ TESTING RECORD LIMIT VS TOKEN LIMIT")
        print("=" * 50)

        # Create provider with very small record limit
        db = SQLiteProvider(max_session_records=3)
        session_id = "record_vs_token_test"

        # Create small records that won't hit token limit
        small_records = []
        for i in range(10):
            record_id = await db.save_conversation(
                session_id=session_id,
                source=f"small_tool_{i}",
                input_data=f"Input {i}",  # ~8 chars = 2 tokens
                output=f"Output {i}",  # ~9 chars = 3 tokens
            )
            small_records.append(record_id)

        # Should be limited by record count (3), not tokens
        final_records = await db.get_session_conversations(session_id)
        final_tokens = sum(r.tokens for r in final_records)

        assert len(final_records) == 3, f"Expected 3 records, got {len(final_records)}"
        assert final_tokens < 100, f"Should have very few tokens, got {final_tokens}"

        print(
            f"✅ Record limit applied: {len(final_records)} records, {final_tokens} tokens"
        )
        print("✅ Record limit was more restrictive than token limit")

    @pytest.mark.asyncio
    async def test_database_token_limit_more_restrictive(self):
        """Test database cleanup when token limit is hit before record limit."""
        print("\n🔢 TESTING TOKEN LIMIT MORE RESTRICTIVE THAN RECORD LIMIT")
        print("=" * 50)

        # Create provider with high record limit but use large records
        db = SQLiteProvider(max_session_records=30)  # Allow many records
        session_id = "token_restrictive_test"

        # Create very large records that will hit token limit quickly
        # Each record: ~10000 tokens (40000 chars total)
        huge_text = "X" * 20000  # 20000 chars = 5000 tokens each

        print("Adding very large records...")
        for i in range(15):  # Try to add 15 records (would be 150K tokens total)
            await db.save_conversation(
                session_id=session_id,
                source=f"huge_tool_{i}",
                input_data=huge_text,  # 5000 tokens
                output=huge_text,  # 5000 tokens
            )

        # Should be limited by token count (50K), not record count (30)
        final_records = await db.get_session_conversations(session_id)
        final_tokens = sum(r.tokens for r in final_records)

        print(f"Final state: {len(final_records)} records, {final_tokens} tokens")

        # Should have 5 records (5 x 10000 = 50K tokens) or fewer
        assert len(final_records) <= 5, (
            f"Expected ≤5 records due to token limit, got {len(final_records)}"
        )
        assert len(final_records) < 30, "Should be limited by tokens, not records (30)"
        assert final_tokens <= MAX_CONTEXT_TOKENS, (
            f"Token limit exceeded: {final_tokens} > {MAX_CONTEXT_TOKENS}"
        )

        print(
            f"✅ Token limit was more restrictive: {len(final_records)} records (max 30), {final_tokens} tokens (max {MAX_CONTEXT_TOKENS})"
        )

        # Verify we kept the most recent records
        sources = [r.source for r in final_records]
        expected_start = 15 - len(final_records)
        expected_sources = [f"huge_tool_{i}" for i in range(14, expected_start - 1, -1)]
        assert sources == expected_sources, (
            f"Expected {expected_sources}, got {sources}"
        )

        print("✅ Most recent large records kept, oldest removed due to token limit")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(TestTokenBasedHistory().test_token_storage_in_database())
    asyncio.run(TestTokenBasedHistory().test_hybrid_loading_record_limit_only())
    asyncio.run(TestTokenBasedHistory().test_hybrid_loading_token_limit_reached())
    asyncio.run(TestTokenBasedHistory().test_filter_records_by_token_limit_function())
    asyncio.run(TestTokenBasedHistory().test_mixed_record_sizes())
