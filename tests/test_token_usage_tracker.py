#!/usr/bin/env python
"""Tests for the token usage tracker service."""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.token_usage_tracker import (
    TokenUsageTracker,
    TokenUsageStats,
    UsagePeriod,
    UsageRecord,
    TokenBudgetExceededError,
    ModelCosts
)


class TestTokenUsageTracker(unittest.TestCase):
    """Test cases for the TokenUsageTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a tracker with a budget limit for testing
        self.tracker = TokenUsageTracker(
            budget_limit=10.0,  # $10 budget
            token_limit=100000,  # 100K token limit
        )
        # Clear any existing records
        self.tracker._usage_records = []

    def test_track_usage_basic(self):
        """Test basic token usage tracking functionality."""
        # Track some usage
        record = self.tracker.track_usage(
            prompt_tokens=100,
            completion_tokens=50,
            model="deepseek-chat-6.7b",
            request_id="test-request-1",
            context="Test context"
        )
        
        # Verify the record was created correctly
        self.assertEqual(record.prompt_tokens, 100)
        self.assertEqual(record.completion_tokens, 50)
        self.assertEqual(record.total_tokens, 150)
        self.assertEqual(record.model, "deepseek-chat-6.7b")
        self.assertEqual(record.request_id, "test-request-1")
        self.assertEqual(record.context, "Test context")
        
        # Verify the record was stored
        self.assertEqual(len(self.tracker._usage_records), 1)
        self.assertEqual(self.tracker._usage_records[0], record)

    def test_budget_limit_enforcement(self):
        """Test that budget limits are enforced."""
        # Use a model with higher cost to hit the budget limit quickly
        model = "gpt-4"
        
        # Track usage that doesn't exceed the budget
        self.tracker.track_usage(
            prompt_tokens=10000,
            completion_tokens=5000,
            model=model,
        )
        
        # Track usage that would exceed the budget
        with self.assertRaises(TokenBudgetExceededError):
            self.tracker.track_usage(
                prompt_tokens=300000,
                completion_tokens=100000,
                model=model,
            )

    def test_token_limit_enforcement(self):
        """Test that token limits are enforced."""
        # Track usage that doesn't exceed the token limit
        self.tracker.track_usage(
            prompt_tokens=10000,
            completion_tokens=5000,
            model="deepseek-chat-6.7b",
        )
        
        # Track usage that would exceed the token limit
        with self.assertRaises(TokenBudgetExceededError):
            self.tracker.track_usage(
                prompt_tokens=50000,
                completion_tokens=50000,
                model="deepseek-chat-6.7b",
            )

    def test_get_usage_stats(self):
        """Test retrieving usage statistics."""
        # Add some test records
        self.tracker.track_usage(100, 50, "deepseek-chat-6.7b", request_id="req1")
        self.tracker.track_usage(200, 100, "deepseek-chat-72b", request_id="req2")
        self.tracker.track_usage(300, 150, "deepseek-chat-6.7b", request_id="req3")
        
        # Get overall stats
        stats = self.tracker.get_usage_stats()
        
        # Verify stats
        self.assertEqual(stats.prompt_tokens, 600)
        self.assertEqual(stats.completion_tokens, 300)
        self.assertEqual(stats.total_tokens, 900)
        self.assertEqual(stats.request_count, 3)
        
        # Verify model breakdown
        self.assertEqual(len(stats.breakdown_by_model), 2)  # Two different models
        self.assertIn("deepseek-chat-6.7b", stats.breakdown_by_model)
        self.assertIn("deepseek-chat-72b", stats.breakdown_by_model)
        
        # Check model-specific stats
        deepseek_6_7b_stats = stats.breakdown_by_model["deepseek-chat-6.7b"]
        self.assertEqual(deepseek_6_7b_stats["prompt_tokens"], 400)
        self.assertEqual(deepseek_6_7b_stats["completion_tokens"], 200)
        self.assertEqual(deepseek_6_7b_stats["total_tokens"], 600)
        self.assertEqual(deepseek_6_7b_stats["request_count"], 2)

    def test_get_usage_stats_with_period(self):
        """Test retrieving usage statistics for a specific period."""
        # Create records with different timestamps
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        # Create records directly to have more control over timestamps
        self.tracker._usage_records = [
            UsageRecord(
                timestamp=yesterday,
                model="deepseek-chat-6.7b",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0,
                request_id="yesterday1"
            ),
            UsageRecord(
                timestamp=now,
                model="deepseek-chat-6.7b",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.0,
                request_id="today1"
            ),
            UsageRecord(
                timestamp=now,
                model="deepseek-chat-6.7b",
                prompt_tokens=300,
                completion_tokens=150,
                total_tokens=450,
                estimated_cost=0.0,
                request_id="today2"
            )
        ]
        
        # Get stats for today
        today_start = datetime(now.year, now.month, now.day)
        today_end = today_start + timedelta(days=1)
        
        stats = self.tracker.get_usage_stats(
            start_date=today_start,
            end_date=today_end
        )
        
        # Verify stats for today only
        self.assertEqual(stats.prompt_tokens, 500)  # 200 + 300
        self.assertEqual(stats.completion_tokens, 250)  # 100 + 150
        self.assertEqual(stats.total_tokens, 750)  # 500 + 250
        self.assertEqual(stats.request_count, 2)  # Two requests today

    def test_estimate_token_count(self):
        """Test token count estimation functionality."""
        # Basic estimation test
        text = "This is a test sentence with approximately 10 tokens."
        estimated_tokens = self.tracker.estimate_token_count(text)
        
        # We expect the estimation to be roughly 10 tokens
        # The exact number may vary based on the estimation method
        self.assertGreater(estimated_tokens, 5)
        self.assertLess(estimated_tokens, 15)

    def test_remaining_budget_and_tokens(self):
        """Test getting remaining budget and tokens."""
        # Initial remaining should be the full budget/limit
        self.assertEqual(self.tracker.get_remaining_budget(), 10.0)
        self.assertEqual(self.tracker.get_remaining_tokens(), 100000)
        
        # Track some usage
        self.tracker.track_usage(
            prompt_tokens=10000,
            completion_tokens=5000,
            model="deepseek-chat-6.7b",
        )
        
        # Check remaining is reduced
        self.assertLess(self.tracker.get_remaining_budget(), 10.0)
        self.assertEqual(self.tracker.get_remaining_tokens(), 85000)  # 100000 - 15000

    def test_reset_usage_data(self):
        """Test resetting usage data."""
        # Add some records
        self.tracker.track_usage(100, 50, "deepseek-chat-6.7b")
        self.tracker.track_usage(200, 100, "deepseek-chat-6.7b")
        
        # Verify records exist
        self.assertEqual(len(self.tracker._usage_records), 2)
        
        # Reset data
        self.tracker.reset_usage_data()
        
        # Verify records are cleared
        self.assertEqual(len(self.tracker._usage_records), 0)


if __name__ == "__main__":
    unittest.main() 