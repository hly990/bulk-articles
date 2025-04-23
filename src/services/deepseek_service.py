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
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union, cast

import requests
from requests import Response

__all__ = [
    "DeepSeekError",
    "AuthenticationError",
    "RateLimitError",
    "APIConnectionError",
    "APIResponseError",
    "DeepSeekService",
]


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class DeepSeekError(RuntimeError):
    """Base error raised for any DeepSeek‑related issues."""


class AuthenticationError(DeepSeekError):
    """Invalid / missing credentials."""


class RateLimitError(DeepSeekError):
    """HTTP 429 – too many requests."""


class APIConnectionError(DeepSeekError):
    """Network‑level issues (timeouts, DNS, TLS …)"""


class APIResponseError(DeepSeekError):
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


class DeepSeekService:
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
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "DeepSeek API key is required – set DEEPSEEK_API_KEY env var or pass api_key."
            )

        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or
                          "https://api.deepseek.com/v1").rstrip("/")
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.logger = logger or logging.getLogger(__name__)
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

        self.logger.debug("DeepSeekService initialised (base_url=%s, cache=%s)",
                          self.base_url, self.cache_enabled)

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
        payload: Dict[str, Any] = {"prompt": prompt, **kwargs}
        data = self._post(self.COMPLETION_PATH, payload)
        try:
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
        payload: Dict[str, Any] = {"messages": messages, **kwargs}
        data = self._post(self.CHAT_PATH, payload)
        try:
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

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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