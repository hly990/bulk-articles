# YT-Article Craft

A tool for automatically generating high-quality articles from YouTube videos.

## Features

- **Video Processing**: Download videos, extract captions, and process transcripts
- **Summarization**: Generate concise, informative summaries from video transcripts
- **Article Generation**: Create well-structured articles from video content
- **Token Usage Tracking**: Monitor and optimize token usage across the application
- **Multiple Output Formats**: Export as HTML, Markdown, and other formats

## Token Usage Tracking

The application includes a robust token usage tracking system that monitors token consumption across different API calls, models, and time periods. This feature helps optimize costs and ensure efficient resource utilization.

### Key Capabilities

- **Usage Tracking**: Track token usage across all API calls
- **Budget Controls**: Set budget limits and receive alerts when approaching limits
- **Usage Statistics**: Get detailed statistics by time period, model, or user
- **Optimization**: Implement strategies to reduce token usage while maintaining quality
- **Token Estimation**: Estimate token count before making API calls

### Example Usage

```python
from src.services import TokenUsageTracker, TokenOptimizer

# Initialize with optional budget limits
tracker = TokenUsageTracker(
    budget_limit=10.0,  # $10 budget limit
    token_limit=1000000  # 1M token limit
)

# Track token usage for API calls
tracker.track_usage(
    prompt_tokens=500,
    completion_tokens=300,
    model="deepseek-chat-72b",
    request_id="example-request",
    context="Article generation"
)

# Get usage statistics
monthly_stats = tracker.get_usage_stats(period=UsagePeriod.MONTH)
print(f"Monthly token usage: {monthly_stats.total_tokens:,}")
print(f"Estimated cost: ${monthly_stats.estimated_cost:.2f}")

# Optimize prompts to reduce token usage
optimized_text = TokenOptimizer.truncate_to_token_limit(
    long_text, 
    max_tokens=100, 
    tracker=tracker
)
```

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/yt-article-craft.git
cd yt-article-craft

# Install dependencies
pip install -r requirements.txt
```

### Usage

See the `examples` directory for sample scripts demonstrating how to use the application.

## License

This project is licensed under the MIT License - see the LICENSE file for details.