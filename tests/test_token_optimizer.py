#!/usr/bin/env python
"""Tests for the TokenOptimizer service."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.token_usage_tracker import TokenOptimizer, TokenUsageTracker


class TestTokenOptimizer(unittest.TestCase):
    """Test cases for the TokenOptimizer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock token tracker for testing
        self.mock_tracker = MagicMock(spec=TokenUsageTracker)
        
        # Configure the mock to return predictable token counts
        # Will return token count equal to word count * 1.3 (rough approximation)
        def mock_estimate_token_count(text):
            return int(len(text.split()) * 1.3)
            
        self.mock_tracker.estimate_token_count.side_effect = mock_estimate_token_count

    def test_truncate_to_token_limit_no_truncation_needed(self):
        """Test when text is already within token limit."""
        text = "This is a short text that doesn't need truncation."
        max_tokens = 20
        
        # Estimate: ~10 words * 1.3 = ~13 tokens, under the limit
        result = TokenOptimizer.truncate_to_token_limit(text, max_tokens, self.mock_tracker)
        
        # Text should remain unchanged
        self.assertEqual(result, text)
        # Verify the token count was estimated
        self.mock_tracker.estimate_token_count.assert_called_once_with(text)

    def test_truncate_to_token_limit_requires_truncation(self):
        """Test truncation when text exceeds token limit."""
        # Create a longer text that will exceed the token limit
        words = ["word"] * 50  # 50 words
        text = " ".join(words)
        max_tokens = 20
        
        # Estimated tokens: ~50 words * 1.3 = ~65 tokens, exceeds the limit
        result = TokenOptimizer.truncate_to_token_limit(text, max_tokens, self.mock_tracker)
        
        # Result should be truncated
        self.assertLess(len(result), len(text))
        # Verify result is within the token limit
        self.assertLessEqual(self.mock_tracker.estimate_token_count(result), max_tokens)
        
        # Tracker should be called multiple times during the truncation process
        self.assertGreater(self.mock_tracker.estimate_token_count.call_count, 1)

    def test_truncate_to_token_limit_with_paragraph_boundaries(self):
        """Test truncation respects paragraph boundaries."""
        text = (
            "This is the first paragraph.\n\n"
            "This is the second paragraph which has more content and will likely exceed our limit.\n\n"
            "This is the third paragraph which should be removed entirely."
        )
        max_tokens = 15  # Set low to ensure truncation
        
        result = TokenOptimizer.truncate_to_token_limit(text, max_tokens, self.mock_tracker)
        
        # Result should contain the first paragraph but not the third
        self.assertIn("first paragraph", result)
        self.assertNotIn("third paragraph", result)
        
        # Verify result is within the token limit
        self.assertLessEqual(self.mock_tracker.estimate_token_count(result), max_tokens)

    def test_optimize_prompt(self):
        """Test prompt optimization with instructions."""
        prompt = "This is a detailed prompt with lots of information that needs to be optimized."
        instructions = "Keep it concise."
        
        result = TokenOptimizer.optimize_prompt(prompt, instructions)
        
        # Result should be optimized based on instructions
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        
        # Since this is more complex and might involve AI-based optimization,
        # we mainly check that it returns a string and doesn't raise exceptions

    def test_optimize_prompt_with_long_text(self):
        """Test prompt optimization with a longer text."""
        # Create a longer prompt
        words = ["information"] * 30
        prompt = "This is a detailed prompt with " + " ".join(words) + " that needs optimization."
        instructions = "Extract the key points."
        
        result = TokenOptimizer.optimize_prompt(prompt, instructions)
        
        # Result should be optimized and likely shorter
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main() 