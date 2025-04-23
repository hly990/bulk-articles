#!/usr/bin/env python
"""Demo script to demonstrate the token usage tracking functionality."""

import os
import sys
import logging
from datetime import datetime, timedelta
import random
import json

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.token_usage_tracker import (
    TokenUsageTracker,
    UsagePeriod,
    TokenBudgetExceededError,
    TokenOptimizer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def simulate_api_calls(tracker, num_calls=5):
    """Simulate a series of API calls with token tracking."""
    models = ["deepseek-chat-6.7b", "deepseek-chat-72b", "deepseek-coder-6.7b"]
    
    for i in range(num_calls):
        # Simulate random token usage
        prompt_tokens = random.randint(100, 500)
        completion_tokens = random.randint(50, 300)
        model = random.choice(models)
        
        logger.info(f"Call {i+1}: Sending request to model '{model}' with {prompt_tokens} prompt tokens")
        
        try:
            record = tracker.track_usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model,
                request_id=f"req-{i+1}",
                context=f"Example API call {i+1}"
            )
            
            logger.info(
                f"Call {i+1}: Received response with {completion_tokens} completion tokens. "
                f"Total cost: ${record.estimated_cost:.6f}"
            )
            
        except TokenBudgetExceededError as e:
            logger.error(f"Budget exceeded: {e}")
            break


def demonstrate_token_optimization(tracker):
    """Demonstrate token optimization strategies."""
    # Sample long text for optimization
    long_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural 
    intelligence displayed by animals including humans. "Intelligence" encompasses the ability to learn, 
    reason, solve problems, perceive, and use language.
    
    AI applications include advanced web search engines, recommendation systems, speech recognition, 
    and self-driving cars. As machines become increasingly capable, tasks once requiring human intelligence 
    are being automated by computer systems.
    
    The field was founded on the assumption that human intelligence "can be so precisely described that 
    a machine can be made to simulate it." This raises philosophical arguments about the mind, consciousness, 
    and the limits of mechanization. Critics argue whether a machine can truly possess consciousness or a mind.
    
    History of AI research has followed two distinct, and sometimes competing, methods: the symbolic approach, 
    which represents "thinking" as abstract symbol manipulation, and the connectionist approach, which models 
    mental processes based on artificial neural networks.
    
    In the twenty-first century, AI techniques have experienced a resurgence following concurrent advances 
    in computer power, large amounts of data, and theoretical understanding. As of 2023, generative AI systems 
    such as large language models, diffusion models, and transformers have demonstrated impressive capabilities, 
    with tools like ChatGPT, Google Bard, and DALL-E becoming widely adopted.
    """
    
    # 1. Demonstrate token counting
    token_count = tracker.estimate_token_count(long_text)
    logger.info(f"Original text token count (estimate): {token_count}")
    
    # 2. Demonstrate truncation to token limit
    truncated = TokenOptimizer.truncate_to_token_limit(long_text, 100, tracker)
    truncated_count = tracker.estimate_token_count(truncated)
    logger.info(f"Truncated text token count: {truncated_count}")
    logger.info(f"Truncated text preview: {truncated[:100]}...")
    
    # 3. Demonstrate prompt optimization
    optimized = TokenOptimizer.optimize_prompt(
        long_text, 
        "Maintain key information about AI history and capabilities, but make it more concise."
    )
    optimized_count = tracker.estimate_token_count(optimized)
    logger.info(f"Optimized text token count: {optimized_count}")
    logger.info(f"Optimization reduced tokens by: {token_count - optimized_count} ({(token_count - optimized_count) / token_count * 100:.1f}%)")
    logger.info(f"Optimized text preview: {optimized[:100]}...")


def display_usage_stats(tracker):
    """Display token usage statistics in different formats."""
    # Get overall stats
    overall_stats = tracker.get_usage_stats()
    logger.info("\n=== Overall Usage Statistics ===")
    logger.info(str(overall_stats))
    
    # Get stats by period
    for period in [UsagePeriod.DAY, UsagePeriod.WEEK, UsagePeriod.MONTH]:
        period_stats = tracker.get_usage_stats(period=period)
        logger.info(f"\n=== Usage Statistics ({period.value}) ===")
        logger.info(str(period_stats))
    
    # Get stats by model
    logger.info("\n=== Usage Breakdown by Model ===")
    for model, stats in overall_stats.breakdown_by_model.items():
        logger.info(f"Model: {model}")
        logger.info(f"  Requests: {stats['request_count']}")
        logger.info(f"  Total tokens: {stats['total_tokens']:,}")
        logger.info(f"  Cost: ${stats['estimated_cost']:.6f}")
    
    # Get remaining budget and tokens
    logger.info("\n=== Remaining Resources ===")
    logger.info(f"Remaining budget: ${tracker.get_remaining_budget():.2f}")
    logger.info(f"Remaining tokens: {tracker.get_remaining_tokens():,}")


def main():
    """Main function to demonstrate token usage tracking."""
    # Create a directory for storage if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Initialize the token tracker with a budget limit
    tracker = TokenUsageTracker(
        storage_path="data/token_usage.json",
        budget_limit=10.0,  # $10 budget limit
        token_limit=1000000,  # 1M token limit
        logger=logger
    )
    
    logger.info("=== Token Usage Tracker Demo ===")
    
    # Reset any existing data for the demo
    tracker.reset_usage_data()
    logger.info("Reset usage data for fresh demo")
    
    # Simulate API calls with token tracking
    logger.info("\n=== Simulating API Calls ===")
    simulate_api_calls(tracker, num_calls=10)
    
    # Demonstrate token optimization
    logger.info("\n=== Token Optimization Demo ===")
    demonstrate_token_optimization(tracker)
    
    # Display usage statistics
    display_usage_stats(tracker)
    
    logger.info("\nDemo completed successfully!")


if __name__ == "__main__":
    main() 