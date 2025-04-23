"""Local Llama3 model service.

This module implements *task 4.8 - Add local model fallback functionality* by
providing a :class:`LocalModelService` that enables local inference using
Llama3-8B models when the DeepSeek API is unavailable.

Key features:
* Download and manage Llama3 models from Hugging Face
* Provide the same interface as DeepSeekService for seamless fallback
* Support both text completion and chat completion
* Integrate with token usage tracking
* Optimize local performance
* Support configuration for model paths and settings
"""

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Import the base LLM service and token tracker
from .llm_service_base import (
    LLMServiceBase,
    LLMServiceError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMConnectionError,
    LLMResponseError,
)

# Try to import the token tracker
try:
    from .token_usage_tracker import TokenUsageTracker
except ImportError:
    TokenUsageTracker = None  # type: ignore

# Try to import llama-cpp-python, but make it optional to avoid breaking
# when it's not installed
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None  # type: ignore

# Try to import huggingface_hub for model downloading
try:
    from huggingface_hub import hf_hub_download, login, HfFolder
    HUGGINGFACE_HUB_AVAILABLE = True
except ImportError:
    HUGGINGFACE_HUB_AVAILABLE = False
    hf_hub_download = None  # type: ignore
    login = None  # type: ignore
    HfFolder = None  # type: ignore


__all__ = [
    "LocalModelError",
    "ModelNotFoundError",
    "ModelDownloadError",
    "ModelLoadError",
    "LocalModelService",
    "LocalModelConfig",
]


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class LocalModelError(LLMServiceError):
    """Base error for local model-related issues."""
    pass


class ModelNotFoundError(LocalModelError):
    """The requested model was not found locally or in the Hugging Face repository."""
    pass


class ModelDownloadError(LocalModelError):
    """Error occurred while downloading the model."""
    pass


class ModelLoadError(LocalModelError):
    """Error occurred while loading or initializing the model."""
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LocalModelConfig:
    """Configuration for local model inference."""
    
    # Model information
    model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    model_basename: str = "Meta-Llama-3-8B-Instruct-Q5_K_M.gguf"
    model_revision: Optional[str] = None
    
    # Model storage path - if not specified, uses ~/.cache/llama_models
    model_dir: Optional[str] = None
    
    # HuggingFace authentication
    hf_token: Optional[str] = None
    
    # Inference options
    context_size: int = 4096
    num_threads: int = 4
    num_gpu_layers: int = 0
    num_batch: int = 512
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    
    # Additional configuration
    max_tokens: int = 512
    stop_tokens: List[str] = None
    
    def __post_init__(self):
        """Initialize optional fields after instance creation."""
        if self.model_dir is None:
            self.model_dir = os.path.expanduser("~/.cache/llama_models")
        
        if self.stop_tokens is None:
            self.stop_tokens = ["\n\n", "###", "</s>"]
            
        # Get HF token from environment if not provided
        if self.hf_token is None:
            self.hf_token = os.getenv("HUGGINGFACE_TOKEN")


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class LocalModelService(LLMServiceBase):
    """Service for local Llama3 model inference."""
    
    def __init__(
        self,
        *,
        config: Optional[LocalModelConfig] = None,
        logger: Optional[logging.Logger] = None,
        token_tracker: Optional[TokenUsageTracker] = None,
        auto_download: bool = True,
    ) -> None:
        """Initialize the local model service.
        
        Parameters
        ----------
        config : Optional[LocalModelConfig]
            Configuration for model loading and inference. If not provided,
            a default configuration will be used.
        logger : Optional[logging.Logger]
            Logger instance. If not provided, a default logger will be created.
        token_tracker : Optional[TokenUsageTracker]
            Token usage tracker for monitoring token consumption.
        auto_download : bool
            Whether to automatically download models if not available locally.
        """
        # Call parent initializer
        super().__init__(logger=logger, token_tracker=token_tracker)
        
        # Check if llama-cpp-python is available
        if not LLAMA_CPP_AVAILABLE:
            self.logger.error("llama-cpp-python is required but not installed.")
            self.logger.error("Install with: pip install llama-cpp-python")
            raise ImportError("llama-cpp-python is required but not installed.")
            
        # Check if huggingface_hub is available (only required if auto_download is True)
        if auto_download and not HUGGINGFACE_HUB_AVAILABLE:
            self.logger.error("huggingface_hub is required for auto_download but not installed.")
            self.logger.error("Install with: pip install huggingface_hub")
            raise ImportError("huggingface_hub is required for auto_download but not installed.")
            
        # Initialize configuration
        self.config = config or LocalModelConfig()
        self.auto_download = auto_download
        
        # Create model directory if it doesn't exist
        os.makedirs(self.config.model_dir, exist_ok=True)
        
        # Model will be loaded on first use
        self._model = None
        self._model_path = None
        
        self.logger.debug(
            "LocalModelService initialized (model=%s, auto_download=%s, token_tracker=%s)",
            self.config.model_id,
            self.auto_download,
            "enabled" if token_tracker else "disabled"
        )
        
    def _ensure_model_available(self) -> str:
        """Ensure the model is available, downloading it if necessary.
        
        Returns
        -------
        str
            Path to the model file.
            
        Raises
        ------
        ModelNotFoundError
            If the model is not found and cannot be downloaded.
        ModelDownloadError
            If downloading the model fails.
        """
        # Check if model exists locally
        model_path = os.path.join(self.config.model_dir, self.config.model_basename)
        if os.path.exists(model_path):
            self.logger.debug(f"Model found at {model_path}")
            return model_path
            
        # If auto_download is disabled, raise an error
        if not self.auto_download:
            raise ModelNotFoundError(
                f"Model {self.config.model_id} not found locally and auto_download is disabled."
            )
            
        # Download the model
        self.logger.info(f"Downloading model {self.config.model_id}...")
        
        try:
            # Login to HuggingFace if token is provided
            if self.config.hf_token:
                login(token=self.config.hf_token)
                
            # Download the model file
            downloaded_path = hf_hub_download(
                repo_id=self.config.model_id,
                filename=self.config.model_basename,
                revision=self.config.model_revision,
                cache_dir=self.config.model_dir,
                token=self.config.hf_token,
            )
            
            self.logger.info(f"Model downloaded to {downloaded_path}")
            return downloaded_path
            
        except Exception as e:
            self.logger.error(f"Failed to download model: {e}")
            raise ModelDownloadError(f"Failed to download model {self.config.model_id}: {e}")
            
    def _load_model(self) -> Llama:
        """Load the model into memory.
        
        Returns
        -------
        Llama
            The loaded Llama model instance.
            
        Raises
        ------
        ModelLoadError
            If loading the model fails.
        """
        if self._model is not None:
            return self._model
            
        try:
            # Ensure model is available
            model_path = self._ensure_model_available()
            self._model_path = model_path
            
            # Load the model
            self.logger.info(f"Loading model from {model_path}...")
            start_time = time.time()
            
            model = Llama(
                model_path=model_path,
                n_ctx=self.config.context_size,
                n_threads=self.config.num_threads,
                n_gpu_layers=self.config.num_gpu_layers,
                n_batch=self.config.num_batch,
            )
            
            load_time = time.time() - start_time
            self.logger.info(f"Model loaded in {load_time:.2f} seconds")
            
            self._model = model
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise ModelLoadError(f"Failed to load model: {e}")
            
    def _create_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a prompt string for Llama models.
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            List of chat messages in the format [{"role": "user", "content": "Hello"}]
            
        Returns
        -------
        str
            The formatted chat prompt string.
        """
        # Construct prompt using the Llama-3 chat template
        prompt = "<|begin_of_chat|>\n"
        
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
            else:
                # Skip unknown roles
                self.logger.warning(f"Skipping message with unknown role: {role}")
                
        # Add the final assistant prompt
        prompt += "<|assistant|>\n"
        
        return prompt
    
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
        # Extract parameters from kwargs or use config defaults
        model = kwargs.get("model", "llama3-8b")
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        temperature = kwargs.get("temperature", self.config.temperature)
        top_p = kwargs.get("top_p", self.config.top_p)
        top_k = kwargs.get("top_k", self.config.top_k)
        stop = kwargs.get("stop", self.config.stop_tokens)
        request_id = kwargs.get("request_id", str(uuid.uuid4()))
        context = kwargs.get("context", "Text completion")
        
        try:
            # Load model if needed
            model_instance = self._load_model()
            
            # Log the prompt (truncated)
            max_log_len = 200
            truncated_prompt = prompt[:max_log_len] + ("..." if len(prompt) > max_log_len else "")
            self.logger.debug(f"Completion prompt: {truncated_prompt} (request_id={request_id})")
            
            # Estimate token count for logging and tracking
            prompt_tokens_estimate = len(prompt.split())
            
            # Generate completion
            start_time = time.time()
            result = model_instance.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
            )
            
            generation_time = time.time() - start_time
            
            # Extract generated text
            completion_text = result["choices"][0]["text"]
            completion_tokens_estimate = len(completion_text.split())
            
            # Log generation metrics
            self.logger.info(
                f"Generated {completion_tokens_estimate} tokens in {generation_time:.2f}s "
                f"({completion_tokens_estimate/generation_time:.1f} tokens/s)"
            )
            
            # Track token usage if token tracker is available
            if self.token_tracker:
                self.token_tracker.track_usage(
                    prompt_tokens=prompt_tokens_estimate,
                    completion_tokens=completion_tokens_estimate,
                    model=model,
                    request_id=request_id,
                    context=context,
                )
                
            return completion_text
            
        except (ModelNotFoundError, ModelDownloadError, ModelLoadError) as e:
            # Re-raise service-specific errors
            raise e
        except Exception as e:
            self.logger.error(f"Error during completion: {e}")
            raise LocalModelError(f"Error during completion: {e}")
            
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
        # Convert chat messages to a prompt string
        prompt = self._create_chat_prompt(messages)
        
        # Use the completion method with the formatted prompt
        return self.completion(prompt, **kwargs)
        
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
        # Simple estimation based on whitespace tokenization
        # This is a rough approximation; a proper tokenizer would be more accurate
        tokens = len(text.split())
        
        return {
            "prompt_tokens": tokens,
            "total_tokens": tokens,
        }
        
    def is_available(self) -> bool:
        """Check if the local model service is available.
        
        Returns
        -------
        bool
            True if the service is available, False otherwise.
        """
        try:
            # Check if the required libraries are installed
            if not LLAMA_CPP_AVAILABLE:
                return False
                
            # Check if the model exists locally or can be downloaded
            self._ensure_model_available()
            return True
            
        except Exception as e:
            self.logger.warning(f"Local model service unavailable: {e}")
            return False 