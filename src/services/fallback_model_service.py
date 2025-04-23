"""Fallback model service.

This module implements *task 4.8 - Add local model fallback functionality* by
providing a :class:`FallbackModelService` that automatically falls back to local
Llama3-8B models when the DeepSeek API is unavailable.

The service maintains the same interface as both DeepSeekService and LocalModelService,
making it a drop-in replacement for any code currently using DeepSeekService.

Key features:
* Transparent fallback between DeepSeek and local models
* Configurable fallback behavior (automatic, manual, disabled)
* Consistent error handling and logging
* Token usage tracking across both services
* Status reporting to monitor which backend is active
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Import the base LLM service
from .llm_service_base import (
    LLMServiceBase,
    LLMServiceError,
)

# Import the DeepSeekService and LocalModelService
from .deepseek_service import DeepSeekService
from .local_model_service import LocalModelService, LocalModelConfig

# Try to import the token tracker
try:
    from .token_usage_tracker import TokenUsageTracker
except ImportError:
    TokenUsageTracker = None  # type: ignore


__all__ = [
    "FallbackMode",
    "FallbackModelService",
]


class FallbackMode(Enum):
    """Fallback behavior modes."""
    
    # Automatically try DeepSeek first, then local model if DeepSeek fails
    AUTO = "auto"
    
    # Use DeepSeek exclusively, fail if it's not available
    DEEPSEEK_ONLY = "deepseek_only"
    
    # Use local model exclusively, regardless of DeepSeek availability
    LOCAL_ONLY = "local_only"
    
    # Use DeepSeek first, but only fall back to local if explicitly triggered
    MANUAL = "manual"


class FallbackModelService(LLMServiceBase):
    """Model service with automatic fallback between DeepSeek and local models."""
    
    def __init__(
        self,
        *,
        deepseek_service: Optional[DeepSeekService] = None,
        local_service: Optional[LocalModelService] = None,
        fallback_mode: Union[FallbackMode, str] = FallbackMode.AUTO,
        logger: Optional[logging.Logger] = None,
        token_tracker: Optional[TokenUsageTracker] = None,
        fallback_check_interval: int = 60,  # seconds
    ) -> None:
        """Initialize the fallback model service.
        
        Parameters
        ----------
        deepseek_service : Optional[DeepSeekService]
            Pre-configured DeepSeekService instance. If not provided, a new one
            will be created with default settings.
        local_service : Optional[LocalModelService]
            Pre-configured LocalModelService instance. If not provided, a new one
            will be created with default settings when needed.
        fallback_mode : Union[FallbackMode, str]
            The fallback behavior mode. Can be a FallbackMode enum value or a string
            with the mode name.
        logger : Optional[logging.Logger]
            Logger instance. If not provided, a default logger will be created.
        token_tracker : Optional[TokenUsageTracker]
            Token usage tracker for monitoring token consumption across services.
        fallback_check_interval : int
            Minimum time in seconds between DeepSeek availability checks.
        """
        # Call parent initializer
        super().__init__(logger=logger, token_tracker=token_tracker)
        
        # Set up token tracker for both services
        self.token_tracker = token_tracker
        
        # Initialize DeepSeek service if not provided
        self.deepseek_service = deepseek_service
        if self.deepseek_service is None:
            try:
                self.deepseek_service = DeepSeekService(
                    token_tracker=token_tracker,
                    logger=logger,
                )
                self.logger.debug("Created new DeepSeekService instance")
            except Exception as e:
                self.logger.warning(f"Failed to create DeepSeekService: {e}")
                self.deepseek_service = None
                
        # Local service will be lazily initialized when needed to avoid
        # downloading models unnecessarily
        self.local_service = local_service
        
        # Parse and set fallback mode
        if isinstance(fallback_mode, str):
            try:
                self.fallback_mode = FallbackMode(fallback_mode.lower())
            except ValueError:
                self.logger.warning(f"Invalid fallback mode '{fallback_mode}', using AUTO")
                self.fallback_mode = FallbackMode.AUTO
        else:
            self.fallback_mode = fallback_mode
            
        # Availability tracking
        self.deepseek_available = None  # None = not checked yet
        self.last_availability_check = 0
        self.fallback_check_interval = fallback_check_interval
        
        self.logger.info(
            f"FallbackModelService initialized (mode={self.fallback_mode.value}, "
            f"deepseek={'configured' if self.deepseek_service else 'not configured'}, "
            f"local={'configured' if self.local_service else 'lazy load'}, "
            f"token_tracker={'enabled' if token_tracker else 'disabled'})"
        )
        
    def _get_local_service(self) -> LocalModelService:
        """Get or initialize the local model service.
        
        Returns
        -------
        LocalModelService
            The local model service instance.
            
        Raises
        ------
        LLMServiceError
            If the local service cannot be initialized.
        """
        if self.local_service is not None:
            return self.local_service
            
        try:
            self.local_service = LocalModelService(
                token_tracker=self.token_tracker,
                logger=self.logger
            )
            self.logger.debug("Created new LocalModelService instance")
            return self.local_service
        except Exception as e:
            msg = f"Failed to initialize local model service: {e}"
            self.logger.error(msg)
            raise LLMServiceError(msg)
            
    def _check_deepseek_availability(self, force: bool = False) -> bool:
        """Check if DeepSeek service is available.
        
        Parameters
        ----------
        force : bool
            If True, check availability regardless of the last check time.
            
        Returns
        -------
        bool
            True if DeepSeek is available, False otherwise.
        """
        # Skip check if there's no DeepSeek service configured
        if self.deepseek_service is None:
            return False
            
        # Skip check if we recently checked and not forcing
        current_time = time.time()
        if (not force and 
            self.deepseek_available is not None and
            current_time - self.last_availability_check < self.fallback_check_interval):
            return self.deepseek_available
            
        try:
            # Check availability
            self.deepseek_available = self.deepseek_service.is_available()
            self.last_availability_check = current_time
            
            if self.deepseek_available:
                self.logger.debug("DeepSeek API is available")
            else:
                self.logger.warning("DeepSeek API is unavailable")
                
            return self.deepseek_available
        except Exception as e:
            self.logger.warning(f"Error checking DeepSeek availability: {e}")
            self.deepseek_available = False
            self.last_availability_check = current_time
            return False
            
    def _get_active_service(self) -> LLMServiceBase:
        """Get the currently active service based on mode and availability.
        
        Returns
        -------
        LLMServiceBase
            The service to use for the current request.
            
        Raises
        ------
        LLMServiceError
            If no service is available.
        """
        # Check which mode we're in
        if self.fallback_mode == FallbackMode.LOCAL_ONLY:
            return self._get_local_service()
            
        if self.fallback_mode == FallbackMode.DEEPSEEK_ONLY:
            if self.deepseek_service is None:
                raise LLMServiceError("DeepSeekService not configured but mode is DEEPSEEK_ONLY")
                
            if not self._check_deepseek_availability():
                raise LLMServiceError("DeepSeek API is unavailable and fallback is disabled")
                
            return self.deepseek_service
            
        # For AUTO and MANUAL modes, check DeepSeek first
        if self.deepseek_service is not None and self._check_deepseek_availability():
            return self.deepseek_service
            
        # In AUTO mode, fall back to local
        if self.fallback_mode == FallbackMode.AUTO:
            self.logger.info("Falling back to local model service")
            return self._get_local_service()
            
        # In MANUAL mode, only fall back if explicitly triggered
        raise LLMServiceError(
            "DeepSeek API is unavailable and fallback is in MANUAL mode. "
            "Use force_local_fallback() to enable fallback."
        )
        
    def completion(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion for the given prompt.
        
        Parameters
        ----------
        prompt : str
            The input prompt string.
        **kwargs : Any
            Additional parameters for the completion.
            
        Returns
        -------
        str
            The generated completion text.
            
        Raises
        ------
        LLMServiceError or subclass
            If generation fails for any reason.
        """
        service = self._get_active_service()
        
        try:
            return service.completion(prompt, **kwargs)
        except Exception as e:
            # If automatic fallback is enabled, try falling back to local
            if (self.fallback_mode == FallbackMode.AUTO and 
                service is self.deepseek_service):
                self.logger.warning(f"DeepSeek completion failed, falling back to local model: {e}")
                self.deepseek_available = False  # Mark as unavailable temporarily
                return self._get_local_service().completion(prompt, **kwargs)
            raise
            
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
        service = self._get_active_service()
        
        try:
            return service.chat_completion(messages, **kwargs)
        except Exception as e:
            # If automatic fallback is enabled, try falling back to local
            if (self.fallback_mode == FallbackMode.AUTO and 
                service is self.deepseek_service):
                self.logger.warning(f"DeepSeek chat_completion failed, falling back to local model: {e}")
                self.deepseek_available = False  # Mark as unavailable temporarily
                return self._get_local_service().chat_completion(messages, **kwargs)
            raise
            
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
        service = self._get_active_service()
        return service.estimate_token_usage(text, model)
        
    def is_available(self) -> bool:
        """Check if any model service is available.
        
        Returns
        -------
        bool
            True if at least one service is available, False otherwise.
        """
        # First check DeepSeek if it's not in LOCAL_ONLY mode
        if self.fallback_mode != FallbackMode.LOCAL_ONLY:
            if self._check_deepseek_availability():
                return True
                
        # Then check local if not in DEEPSEEK_ONLY mode
        if self.fallback_mode != FallbackMode.DEEPSEEK_ONLY:
            try:
                return self._get_local_service().is_available()
            except Exception:
                pass
                
        return False
        
    def force_local_fallback(self) -> bool:
        """Force the service to use local models.
        
        This is particularly useful in MANUAL mode to trigger fallback explicitly.
        In AUTO mode, this has minimal effect as fallback happens automatically.
        In LOCAL_ONLY mode, this does nothing.
        In DEEPSEEK_ONLY mode, this temporarily changes the mode to LOCAL_ONLY.
        
        Returns
        -------
        bool
            True if local service is available, False otherwise.
        """
        # First ensure we have a local service
        try:
            local_service = self._get_local_service()
        except Exception as e:
            self.logger.error(f"Failed to initialize local service for forced fallback: {e}")
            return False
            
        # In DEEPSEEK_ONLY mode, switch modes temporarily
        if self.fallback_mode == FallbackMode.DEEPSEEK_ONLY:
            self.logger.info("Temporarily switching from DEEPSEEK_ONLY to LOCAL_ONLY mode")
            original_mode = self.fallback_mode
            self.fallback_mode = FallbackMode.LOCAL_ONLY
            
            # Schedule a job to restore the original mode after some time
            def restore_mode():
                self.logger.info(f"Restoring fallback mode to {original_mode.value}")
                self.fallback_mode = original_mode
                
            # This would be better with a proper job scheduler, but for simplicity
            # we'll use a crude approach with a timer thread
            import threading
            timer = threading.Timer(300, restore_mode)  # 5 minutes
            timer.daemon = True
            timer.start()
            
        # For MANUAL mode, just mark DeepSeek as unavailable
        if self.fallback_mode == FallbackMode.MANUAL:
            self.deepseek_available = False
            
        # Check if local service is actually available
        return local_service.is_available()
        
    def get_active_service_info(self) -> Dict[str, Any]:
        """Get information about the currently active service.
        
        Returns
        -------
        Dict[str, Any]
            Dictionary with information about the active service.
        """
        try:
            service = self._get_active_service()
            service_name = (
                "DeepSeekService" if service is self.deepseek_service 
                else "LocalModelService"
            )
            return {
                "active_service": service_name,
                "fallback_mode": self.fallback_mode.value,
                "deepseek_available": self.deepseek_available,
                "local_configured": self.local_service is not None,
            }
        except Exception as e:
            return {
                "active_service": "none",
                "fallback_mode": self.fallback_mode.value,
                "deepseek_available": self.deepseek_available,
                "local_configured": self.local_service is not None,
                "error": str(e),
            }
        
    def set_fallback_mode(self, mode: Union[FallbackMode, str]) -> None:
        """Change the fallback mode.
        
        Parameters
        ----------
        mode : Union[FallbackMode, str]
            The new fallback mode to set.
            
        Raises
        ------
        ValueError
            If the mode string is invalid.
        """
        if isinstance(mode, str):
            try:
                self.fallback_mode = FallbackMode(mode.lower())
            except ValueError:
                valid_modes = ", ".join(m.value for m in FallbackMode)
                raise ValueError(f"Invalid fallback mode '{mode}'. Valid modes: {valid_modes}")
        else:
            self.fallback_mode = mode
            
        self.logger.info(f"Fallback mode set to {self.fallback_mode.value}")
        
        # Reset availability cache when mode changes
        self.deepseek_available = None
        self.last_availability_check = 0 