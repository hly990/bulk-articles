from __future__ import annotations

"""DeepSeek API wrapper service.

This module implements *task 4.1 – Set up DeepSeek API integration* by
providing a :class:`DeepSeekService` that encapsulates interaction with the
public DeepSeek REST API.

The goals for the first iteration are:

* Load API credentials (base URL & key) from *application settings* or
  environment variables – **never hard‑coded**.
* Offer helper methods `completion` (text completion) and `chat_completion`
  (OpenAI‑style chat interface).
* Provide basic *in‑memory* request caching to avoid duplicate calls.
* Add structured error handling covering common failure scenarios (rate
  limits, authentication issues, timeouts …).
* Surface detailed *logging* for all outbound requests & responses (truncated
  to a safe length).

Updates in task 4.7:
* Added integration with TokenUsageTracker to monitor and optimize token usage
* Added token counting from API responses
* Added support for tracking usage statistics

Updates in task 4.8:
* Refactored to inherit from LLMServiceBase
* Aligned error classes with base LLM service errors
* Ensured compatibility with other LLM services for fallback

A full UI to configure the credentials will be added in a later sub‑task. For
now, callers may pass the parameters explicitly or rely on environment
variables:

    • `DEEPSEEK_API_KEY`  – **required**
    • `DEEPSEEK_BASE_URL` – defaults to ``https://api.deepseek.com/v1``
"""

from dataclasses import dataclass
import hashlib
import json
import logging
import os
import threading
import uuid
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union, cast

import requests
from requests import Response

# Import the base LLM service and token tracker
from .llm_service_base import (
    LLMServiceBase,
    LLMServiceError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMConnectionError,
    LLMResponseError,
)

# Import the token tracker, but make it optional in case it's not available yet
try:
    from .token_usage_tracker import TokenUsageTracker
except ImportError:
    TokenUsageTracker = None  # type: ignore

__all__ = [
    "DeepSeekError",
    "AuthenticationError",
    "RateLimitError",
    "APIConnectionError",
    "APIResponseError",
    "DeepSeekService",
]


# ---------------------------------------------------------------------------
# Error hierarchy - keeping for backward compatibility
# ---------------------------------------------------------------------------


class DeepSeekError(LLMServiceError):
    """Base error raised for any DeepSeek‑related issues."""


class AuthenticationError(DeepSeekError, LLMAuthenticationError):
    """Invalid / missing credentials."""


class RateLimitError(DeepSeekError, LLMRateLimitError):
    """HTTP 429 – too many requests."""


class APIConnectionError(DeepSeekError, LLMConnectionError):
    """Network‑level issues (timeouts, DNS, TLS …)"""


class APIResponseError(DeepSeekError, LLMResponseError):
    """Unexpected / malformed API response."""


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CacheKey:
    """A simple immutable cache key for request de‑duplication."""

    endpoint: str
    payload_hash: str

    @staticmethod
    def from_payload(endpoint: str, payload: Dict[str, Any]) -> "_CacheKey":
        # Serialise payload deterministically & hash – prevents leaking raw
        # prompts into memory representation.
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return _CacheKey(endpoint, digest)


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class DeepSeekService(LLMServiceBase):
    """Lightweight wrapper around the DeepSeek text AI API."""

    # Default endpoints relative to *base_url*
    COMPLETION_PATH = "/completion"
    CHAT_PATH = "/chat/completions"

    # Safeguard: do not log more than this many characters of any prompt /
    # response to avoid leaking potentially private user data.
    _LOG_TRUNCATE = 500

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        cache_enabled: bool = True,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        token_tracker: Optional[TokenUsageTracker] = None,
    ) -> None:
        """Initialize the DeepSeek service.
        
        Parameters
        ----------
        api_key : Optional[str]
            DeepSeek API key. If not provided, will look for DEEPSEEK_API_KEY environment variable.
        base_url : Optional[str]
            DeepSeek API base URL. If not provided, will use default or DEEPSEEK_BASE_URL env var.
        timeout : int
            Request timeout in seconds.
        cache_enabled : bool
            Whether to enable request caching.
        logger : Optional[logging.Logger]
            Logger to use. If not provided, will create one based on class name.
        session : Optional[requests.Session]
            Request session to use. If not provided, will create a new one.
        token_tracker : Optional[TokenUsageTracker]
            Token usage tracker for monitoring API usage.
        """
        # Call parent initializer
        super().__init__(logger=logger, token_tracker=token_tracker)
        
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "DeepSeek API key is required – set DEEPSEEK_API_KEY env var or pass api_key."
            )

        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or
                          "https://api.deepseek.com/v1").rstrip("/")
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self._session = session or requests.Session()
        self._lock = threading.Lock()  # protect cache in multi‑threaded env
        self._cache: MutableMapping[_CacheKey, Dict[str, Any]] = {}

        # Pre‑configure headers – can be overridden per‑request.
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        self.logger.debug("DeepSeekService initialised (base_url=%s, cache=%s, token_tracker=%s)",
                          self.base_url, self.cache_enabled, "enabled" if token_tracker else "disabled")

    # ------------------------------------------------------------------
    # Public API helpers
    # ------------------------------------------------------------------

    def completion(self, prompt: str, **kwargs: Any) -> str:
        """High‑level helper for the *text completion* endpoint.

        Parameters
        ----------
        prompt: str
            The input prompt string.
        **kwargs: Any
            Additional DeepSeek request parameters (e.g. *model*, *temperature* …).

        Returns
        -------
        str
            The generated completion text.
        """
        model = kwargs.get("model", "deepseek-chat-6.7b")
        request_id = kwargs.pop("request_id", str(uuid.uuid4()))
        context = kwargs.pop("context", "Text completion")
        
        # Estimate prompt tokens for logging/planning
        prompt_tokens_estimate = len(prompt.split()) 
        self.logger.debug(f"Estimated prompt tokens: {prompt_tokens_estimate} (request_id={request_id})")
        
        payload: Dict[str, Any] = {"prompt": prompt, **kwargs}
        data = self._post(self.COMPLETION_PATH, payload, request_id=request_id, context=context)
        
        try:
            # Extract token counts if available
            prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0) or prompt_tokens_estimate
            completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
            
            # Track token usage if token tracker is available
            if self.token_tracker:
                self.token_tracker.track_usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=model,
                    request_id=request_id,
                    context=context
                )
                
            return cast(str, data["choices"][0]["text"])
        except (KeyError, IndexError, TypeError):
            raise APIResponseError("Malformed completion response: missing 'choices[0].text'")

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """OpenAI‑style chat completion helper.

        Parameters
        ----------
        messages: List[Dict[str,str]]
            Chat messages in the usual format `[{'role': 'user', 'content': 'Hi'}]`.
        **kwargs: Any
            Extra DeepSeek params.

        Returns
        -------
        str
            The assistant response content.
        """
        model = kwargs.get("model", "deepseek-chat-6.7b")
        request_id = kwargs.pop("request_id", str(uuid.uuid4()))
        context = kwargs.pop("context", "Chat completion")
        
        # Estimate prompt tokens for logging/planning
        prompt_tokens_estimate = sum(len(m.get("content", "").split()) for m in messages)
        self.logger.debug(f"Estimated prompt tokens: {prompt_tokens_estimate} (request_id={request_id})")
        
        payload: Dict[str, Any] = {"messages": messages, **kwargs}
        data = self._post(self.CHAT_PATH, payload, request_id=request_id, context=context)
        
        try:
            # Extract token counts if available
            prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0) or prompt_tokens_estimate
            completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
            
            # Track token usage if token tracker is available
            if self.token_tracker:
                self.token_tracker.track_usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=model,
                    request_id=request_id,
                    context=context
                )
                
            return cast(str, data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            raise APIResponseError("Malformed chat response: missing 'choices[0].message.content'")

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cache(self, key: _CacheKey) -> Optional[Dict[str, Any]]:
        if not self.cache_enabled:
            return None
        with self._lock:
            return self._cache.get(key)

    def _set_cache(self, key: _CacheKey, value: Dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        with self._lock:
            self._cache[key] = value

    # ------------------------------------------------------------------
    # Internal request handler
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: Dict[str, Any], request_id: str = "", context: str = "") -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        cache_key = _CacheKey.from_payload(path, payload)

        cached = self._get_cache(cache_key)
        if cached is not None:
            self.logger.debug("Cache hit for %s", cache_key)
            return cached

        log_payload = json.dumps(payload)[: self._LOG_TRUNCATE] + ("…" if len(json.dumps(payload)) > self._LOG_TRUNCATE else "")
        self.logger.info("POST %s – payload=%s", url, log_payload)

        try:
            response = self._session.post(url, json=payload, timeout=self.timeout)
        except requests.Timeout as exc:
            raise APIConnectionError(f"Request to {url} timed out after {self.timeout}s") from exc
        except requests.RequestException as exc:
            raise APIConnectionError(f"Network error contacting {url}: {exc}") from exc

        self._raise_for_status(response)

        try:
            data = cast(Dict[str, Any], response.json())
        except ValueError as exc:  # JSON decode error
            raise APIResponseError(f"Non‑JSON response from API: {response.text[:200]}") from exc

        self._set_cache(cache_key, data)
        
        # Log token usage if available in the response
        usage = data.get("usage", {})
        if usage:
            self.logger.info(
                "API usage: prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
                usage.get("prompt_tokens", "unknown"),
                usage.get("completion_tokens", "unknown"),
                usage.get("total_tokens", "unknown")
            )

        return data

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    def _raise_for_status(self, response: Response) -> None:  # noqa: D401
        if response.status_code == 200:
            return
        body_preview = response.text[:200]
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key or unauthorized (401)")
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded (429)")
        if 400 <= response.status_code < 500:
            raise APIResponseError(f"Client error {response.status_code}: {body_preview}")
        if 500 <= response.status_code < 600:
            raise APIResponseError(f"Server error {response.status_code}: {body_preview}")
        # Should never reach here – but cover ourselves
        raise APIResponseError(f"Unexpected status {response.status_code}: {body_preview}")

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Empty the in‑memory cache."""
        with self._lock:
            self._cache.clear()

    # Convenience alias used by tests
    reset_cache = clear_cache

    def estimate_token_usage(self, text: str, model: str = "deepseek-chat-6.7b") -> Dict[str, int]:
        """Estimate the number of tokens for a given text.
        
        This is a simple estimation based on average characters per token.
        For more accurate results, use the token_tracker's estimation.
        
        Parameters
        ----------
        text: str
            Text to estimate token count for
        model: str
            Model to estimate for (some models use different tokenizers)
            
        Returns
        -------
        Dict[str, int]
            Estimated token counts {'prompt_tokens': count}
        """
        if self.token_tracker:
            count = self.token_tracker.estimate_token_count(text)
        else:
            # Simple approximation: 4 chars ~= 1 token for English text
            # This is very approximate and should be replaced with a proper tokenizer
            count = max(1, len(text) // 4)
            
        return {"prompt_tokens": count}

    def is_available(self) -> bool:
        """Check if the DeepSeek API is available.
        
        Returns
        -------
        bool
            True if the API is available, False otherwise.
        """
        try:
            # Use a minimal API call to check connectivity
            payload = {"prompt": "test", "max_tokens": 1, "model": "deepseek-chat-6.7b"}
            url = f"{self.base_url}{self.COMPLETION_PATH}"
            response = self._session.post(url, json=payload, timeout=5)  # Short timeout for fast check
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"DeepSeek API unavailable: {e}")
            return False 