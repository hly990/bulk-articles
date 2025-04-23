"""Abstract base class for LLM services.

This module defines a common interface for language model services,
enabling interchangeable use of different backends (DeepSeek API,
local Llama models, etc.) with consistent interfaces, error handling,
and token tracking.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Union

# Import the token tracker
try:
    from .token_usage_tracker import TokenUsageTracker
except ImportError:
    TokenUsageTracker = None  # type: ignore


class LLMServiceError(RuntimeError):
    """Base error for all LLM service-related issues."""
    pass


class LLMAuthenticationError(LLMServiceError):
    """Invalid or missing credentials."""
    pass


class LLMRateLimitError(LLMServiceError):
    """Too many requests or resource limits exceeded."""
    pass


class LLMConnectionError(LLMServiceError):
    """Network or connectivity issues."""
    pass


class LLMResponseError(LLMServiceError):
    """Unexpected or malformed response."""
    pass


class LLMServiceBase(ABC):
    """Abstract base class for language model services.
    
    This class defines the common interface that all LLM services must implement,
    ensuring compatibility between different LLM backends (API-based, local models, etc.).
    """
    
    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        token_tracker: Optional[TokenUsageTracker] = None,
    ) -> None:
        """Initialize the LLM service.
        
        Parameters
        ----------
        logger : Optional[logging.Logger]
            Logger instance for service-level logging. If not provided, a default logger
            will be created based on the class name.
        token_tracker : Optional[TokenUsageTracker]
            Token usage tracker for monitoring and optimizing token consumption.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.token_tracker = token_tracker
        
    @abstractmethod
    def completion(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion for the given prompt.
        
        Parameters
        ----------
        prompt : str
            The input prompt string.
        **kwargs : Any
            Additional parameters for the completion (model, temperature, etc.).
            
        Returns
        -------
        str
            The generated completion text.
            
        Raises
        ------
        LLMServiceError or subclass
            If generation fails for any reason.
        """
        pass
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a response for the given chat messages.
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            Chat messages in the format [{'role': 'user', 'content': 'Hi'}].
        **kwargs : Any
            Additional parameters for the chat completion.
            
        Returns
        -------
        str
            The assistant's response content.
            
        Raises
        ------
        LLMServiceError or subclass
            If generation fails for any reason.
        """
        pass
    
    @abstractmethod
    def estimate_token_usage(self, text: str, model: str = None) -> Dict[str, int]:
        """Estimate the number of tokens in the given text.
        
        Parameters
        ----------
        text : str
            The text to estimate token count for.
        model : str, optional
            The model to use for estimation.
            
        Returns
        -------
        Dict[str, int]
            A dictionary with token count information.
        """
        pass
    
    def is_available(self) -> bool:
        """Check if the service is currently available.
        
        This method should perform a lightweight check to determine if the
        service can be used. Implementations might check for API connectivity,
        model availability, etc.
        
        Returns
        -------
        bool
            True if the service is available, False otherwise.
        """
        try:
            # Default implementation tries a minimal completion
            self.completion("test", max_tokens=1)
            return True
        except Exception as e:
            self.logger.warning(f"Service unavailable: {e}")
            return False 