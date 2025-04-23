"""Token usage tracking and optimization service.

Implements *task 4.7 (Implement token usage tracking and optimization)* by providing
a service that tracks token usage, optimizes prompts for efficiency, and provides 
usage statistics.

Key components:
- TokenUsageTracker - Main service for tracking token usage across the application
- TokenUsageStats - Data class for storing token usage statistics
- TokenOptimizer - Helper for optimizing prompts to reduce token usage
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import json


class UsagePeriod(Enum):
    """Period for grouping token usage statistics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


@dataclass
class ModelCosts:
    """Cost information for different LLM models."""
    # Cost per 1K tokens (in USD)
    prompt_cost_per_1k: float
    completion_cost_per_1k: float
    model_name: str
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost for a given number of tokens."""
        prompt_cost = (prompt_tokens / 1000) * self.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * self.completion_cost_per_1k
        return prompt_cost + completion_cost


# Common model costs (in USD per 1K tokens)
DEFAULT_MODEL_COSTS = {
    "deepseek-chat-6.7b": ModelCosts(0.0002, 0.0002, "deepseek-chat-6.7b"),  # Example cost, adjust as needed
    "deepseek-chat-72b": ModelCosts(0.004, 0.004, "deepseek-chat-72b"),
    "deepseek-coder-6.7b": ModelCosts(0.0005, 0.0005, "deepseek-coder-6.7b"),
    "deepseek-coder-33b": ModelCosts(0.002, 0.002, "deepseek-coder-33b"),
    "llama3-8b": ModelCosts(0.0, 0.0, "llama3-8b"),  # Local model, no cost
    "gpt-3.5-turbo": ModelCosts(0.0015, 0.002, "gpt-3.5-turbo"),  # For comparison
    "gpt-4": ModelCosts(0.03, 0.06, "gpt-4"),  # For comparison
}


@dataclass
class UsageRecord:
    """Individual token usage record."""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    request_id: str
    context: str = ""  # Additional context about what the tokens were used for
    user_id: str = ""  # Optional user identifier if tracking per-user


@dataclass
class TokenUsageStats:
    """Statistics about token usage."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    request_count: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    breakdown_by_model: Dict[str, Dict[str, Union[int, float]]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to a dictionary for serialization."""
        result = {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": round(self.estimated_cost, 4),
            "request_count": self.request_count,
            "breakdown_by_model": self.breakdown_by_model,
        }
        
        if self.period_start:
            result["period_start"] = self.period_start.isoformat()
        if self.period_end:
            result["period_end"] = self.period_end.isoformat()
            
        return result
    
    def __str__(self) -> str:
        """Return a formatted string representation of the stats."""
        period_info = ""
        if self.period_start and self.period_end:
            period_info = f" ({self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')})"
            
        return (
            f"Token Usage{period_info}:\n"
            f"  Requests: {self.request_count}\n"
            f"  Prompt tokens: {self.prompt_tokens:,}\n"
            f"  Completion tokens: {self.completion_tokens:,}\n"
            f"  Total tokens: {self.total_tokens:,}\n"
            f"  Estimated cost: ${self.estimated_cost:.4f}\n"
        )


class TokenBudgetExceededError(Exception):
    """Raised when a token budget limit is exceeded."""
    pass


class TokenUsageTracker:
    """Service for tracking token usage across the application.
    
    This service keeps track of token usage for API requests, provides
    usage statistics, and enforces optional budget limits.
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        budget_limit: Optional[float] = None,
        token_limit: Optional[int] = None,
        logger: Optional[logging.Logger] = None,
        model_costs: Optional[Dict[str, ModelCosts]] = None,
    ):
        """Initialize the token usage tracker.
        
        Parameters
        ----------
        storage_path : str, optional
            Path to save usage data persistently
        budget_limit : float, optional
            Maximum budget (in USD) allowed
        token_limit : int, optional
            Maximum number of tokens allowed
        logger : logging.Logger, optional
            Logger for the service
        model_costs : Dict[str, ModelCosts], optional
            Cost information for different models
        """
        self.storage_path = storage_path
        self.budget_limit = budget_limit
        self.token_limit = token_limit
        self.logger = logger or logging.getLogger(__name__)
        self.model_costs = model_costs or DEFAULT_MODEL_COSTS
        
        self._usage_records: List[UsageRecord] = []
        self._lock = threading.RLock()
        
        # Try to load existing data if storage path is provided
        if storage_path:
            self._load_usage_data()
    
    def track_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        request_id: str = "",
        context: str = "",
        user_id: str = "",
        check_budget: bool = True,
    ) -> UsageRecord:
        """Track token usage for a request.
        
        Parameters
        ----------
        prompt_tokens : int
            Number of tokens in the prompt
        completion_tokens : int
            Number of tokens in the completion
        model : str
            Model used for the request
        request_id : str, optional
            Identifier for the request
        context : str, optional
            Additional context about the request
        user_id : str, optional
            User identifier if tracking per-user
        check_budget : bool, optional
            Whether to check budget limits (default True)
            
        Returns
        -------
        UsageRecord
            Record of the tracked usage
            
        Raises
        ------
        TokenBudgetExceededError
            If budget limit is exceeded and check_budget is True
        """
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost
        model_cost = self.model_costs.get(model)
        if not model_cost:
            self.logger.warning(f"Unknown model: {model}, using default cost calculation")
            # Default to a low estimation if model not found
            model_cost = ModelCosts(0.0002, 0.0002, model)
            
        estimated_cost = model_cost.calculate_cost(prompt_tokens, completion_tokens)
        
        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            request_id=request_id,
            context=context,
            user_id=user_id
        )
        
        with self._lock:
            # Check budget limits if enabled
            if check_budget:
                current_stats = self.get_usage_stats(period=UsagePeriod.MONTH)
                
                # Check budget limit
                if self.budget_limit and (current_stats.estimated_cost + estimated_cost) > self.budget_limit:
                    raise TokenBudgetExceededError(
                        f"Budget limit of ${self.budget_limit:.2f} would be exceeded "
                        f"(current: ${current_stats.estimated_cost:.2f}, new: ${estimated_cost:.2f})"
                    )
                    
                # Check token limit
                if self.token_limit and (current_stats.total_tokens + total_tokens) > self.token_limit:
                    raise TokenBudgetExceededError(
                        f"Token limit of {self.token_limit:,} would be exceeded "
                        f"(current: {current_stats.total_tokens:,}, new: {total_tokens:,})"
                    )
            
            # Store the record
            self._usage_records.append(record)
            
            # Save data if storage path is provided
            if self.storage_path:
                self._save_usage_data()
                
        return record
    
    def estimate_token_count(self, text: str) -> int:
        """Estimate the number of tokens in a text.
        
        This is a simple estimation based on whitespace tokens.
        For more accurate results, use a proper tokenizer.
        
        Parameters
        ----------
        text : str
            Text to estimate token count for
            
        Returns
        -------
        int
            Estimated token count
        """
        # Simple estimation: ~4 characters per token on average
        # This is a very rough estimate and should be replaced with a proper tokenizer
        return max(1, len(text) // 4)
    
    def get_usage_stats(self, 
                        period: UsagePeriod = UsagePeriod.ALL_TIME,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        user_id: Optional[str] = None) -> TokenUsageStats:
        """Get token usage statistics for a specific period.
        
        Parameters
        ----------
        period : UsagePeriod
            Time period for statistics
        start_date : datetime, optional
            Custom start date (overrides period)
        end_date : datetime, optional
            Custom end date (overrides period)
        user_id : str, optional
            Filter by user ID
            
        Returns
        -------
        TokenUsageStats
            Usage statistics for the specified period
        """
        # Determine date range based on period or custom dates
        if start_date is None and end_date is None:
            # Calculate dates based on period
            end_date = datetime.now()
            
            if period == UsagePeriod.HOUR:
                start_date = end_date - timedelta(hours=1)
            elif period == UsagePeriod.DAY:
                start_date = end_date - timedelta(days=1)
            elif period == UsagePeriod.WEEK:
                start_date = end_date - timedelta(weeks=1)
            elif period == UsagePeriod.MONTH:
                start_date = end_date - timedelta(days=30)
            else:  # ALL_TIME
                start_date = datetime.min
        
        # If only one is provided, set the other
        if start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.now()
            
        stats = TokenUsageStats(period_start=start_date, period_end=end_date)
        model_breakdown: Dict[str, Dict[str, Union[int, float]]] = {}
        
        with self._lock:
            for record in self._usage_records:
                # Skip if outside date range
                if record.timestamp < start_date or record.timestamp > end_date:
                    continue
                    
                # Skip if user_id filter is applied and doesn't match
                if user_id and record.user_id != user_id:
                    continue
                
                # Update main stats
                stats.prompt_tokens += record.prompt_tokens
                stats.completion_tokens += record.completion_tokens
                stats.total_tokens += record.total_tokens
                stats.estimated_cost += record.estimated_cost
                stats.request_count += 1
                
                # Update model breakdown
                if record.model not in model_breakdown:
                    model_breakdown[record.model] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost": 0.0,
                        "request_count": 0
                    }
                
                model_data = model_breakdown[record.model]
                model_data["prompt_tokens"] = int(model_data["prompt_tokens"]) + record.prompt_tokens
                model_data["completion_tokens"] = int(model_data["completion_tokens"]) + record.completion_tokens
                model_data["total_tokens"] = int(model_data["total_tokens"]) + record.total_tokens
                model_data["estimated_cost"] = float(model_data["estimated_cost"]) + record.estimated_cost
                model_data["request_count"] = int(model_data["request_count"]) + 1
        
        # Set model breakdown in stats
        stats.breakdown_by_model = model_breakdown
        return stats
    
    def get_remaining_budget(self) -> float:
        """Get the remaining budget in USD.
        
        Returns
        -------
        float
            Remaining budget, or float('inf') if no budget limit is set
        """
        if not self.budget_limit:
            return float('inf')
            
        current_usage = self.get_usage_stats(period=UsagePeriod.MONTH)
        return max(0, self.budget_limit - current_usage.estimated_cost)
    
    def get_remaining_tokens(self) -> int:
        """Get the remaining token allowance.
        
        Returns
        -------
        int
            Remaining tokens, or float('inf') if no token limit is set
        """
        if not self.token_limit:
            return float('inf')
            
        current_usage = self.get_usage_stats(period=UsagePeriod.MONTH)
        return max(0, self.token_limit - current_usage.total_tokens)
    
    def _save_usage_data(self) -> None:
        """Save usage data to disk."""
        if not self.storage_path:
            return
            
        try:
            # Convert records to dictionaries
            records_data = []
            for record in self._usage_records:
                records_data.append({
                    "timestamp": record.timestamp.isoformat(),
                    "model": record.model,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "total_tokens": record.total_tokens,
                    "estimated_cost": record.estimated_cost,
                    "request_id": record.request_id,
                    "context": record.context,
                    "user_id": record.user_id
                })
            
            with open(self.storage_path, 'w') as f:
                json.dump({"records": records_data}, f, indent=2)
                
            self.logger.debug(f"Saved {len(records_data)} usage records to {self.storage_path}")
        except Exception as e:
            self.logger.error(f"Failed to save usage data: {e}")
    
    def _load_usage_data(self) -> None:
        """Load usage data from disk."""
        if not self.storage_path:
            return
            
        try:
            import os
            if not os.path.exists(self.storage_path):
                self.logger.info(f"Usage data file {self.storage_path} does not exist yet")
                return
                
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                
            records = []
            for record_data in data.get("records", []):
                records.append(UsageRecord(
                    timestamp=datetime.fromisoformat(record_data["timestamp"]),
                    model=record_data["model"],
                    prompt_tokens=record_data["prompt_tokens"],
                    completion_tokens=record_data["completion_tokens"],
                    total_tokens=record_data["total_tokens"],
                    estimated_cost=record_data["estimated_cost"],
                    request_id=record_data["request_id"],
                    context=record_data.get("context", ""),
                    user_id=record_data.get("user_id", "")
                ))
            
            self._usage_records = records
            self.logger.info(f"Loaded {len(records)} usage records from {self.storage_path}")
        except Exception as e:
            self.logger.error(f"Failed to load usage data: {e}")
            # Start with empty records
            self._usage_records = []
    
    def reset_usage_data(self) -> None:
        """Reset all usage data."""
        with self._lock:
            self._usage_records = []
            if self.storage_path:
                self._save_usage_data()
    
    def __str__(self) -> str:
        """Return a string representation of current usage."""
        stats = self.get_usage_stats()
        
        result = [str(stats)]
        
        # Add budget information if available
        if self.budget_limit:
            remaining = self.get_remaining_budget()
            result.append(f"Budget: ${self.budget_limit:.2f}")
            result.append(f"Remaining: ${remaining:.2f}")
            result.append(f"Used: {(self.budget_limit - remaining) / self.budget_limit:.1%}")
            
        # Add token limit information if available
        if self.token_limit:
            remaining = self.get_remaining_tokens()
            result.append(f"Token limit: {self.token_limit:,}")
            result.append(f"Remaining: {remaining:,}")
            result.append(f"Used: {(self.token_limit - remaining) / self.token_limit:.1%}")
            
        return "\n".join(result)


class TokenOptimizer:
    """Helper for optimizing prompts to reduce token usage."""
    
    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int, tracker: TokenUsageTracker) -> str:
        """Truncate text to stay within token limit.
        
        Parameters
        ----------
        text : str
            Text to truncate
        max_tokens : int
            Maximum number of tokens allowed
        tracker : TokenUsageTracker
            Token tracker for estimating token count
            
        Returns
        -------
        str
            Truncated text
        """
        estimated_tokens = tracker.estimate_token_count(text)
        
        if estimated_tokens <= max_tokens:
            return text
            
        # Simple truncation based on character count
        # This is a very rough approach and should be improved
        ratio = max_tokens / estimated_tokens
        char_limit = int(len(text) * ratio * 0.95)  # Add 5% safety margin
        
        truncated = text[:char_limit]
        
        # Try to truncate at a sentence or paragraph boundary
        for separator in ["\n\n", "\n", ". ", "! ", "? "]:
            last_sep = truncated.rfind(separator)
            if last_sep > len(truncated) * 0.5:  # Only use if we keep at least half
                return truncated[:last_sep + len(separator)]
        
        return truncated
    
    @staticmethod
    def optimize_prompt(prompt: str, instructions: str) -> str:
        """Optimize a prompt by applying various strategies.
        
        Parameters
        ----------
        prompt : str
            Original prompt
        instructions : str
            Instructions that must be preserved
            
        Returns
        -------
        str
            Optimized prompt
        """
        # This is a placeholder for more advanced optimization techniques
        # For now, we'll just do some basic cleanup
        
        # Remove redundant whitespace
        optimized = " ".join(prompt.split())
        
        # Ensure instructions are included
        if instructions and instructions not in optimized:
            optimized = f"{instructions}\n\n{optimized}"
            
        return optimized 