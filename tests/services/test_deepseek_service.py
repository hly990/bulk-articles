import json
from typing import Dict, Any, List
import pytest

# Add src folder to path for module discovery
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.deepseek_service import (
    DeepSeekService,
    AuthenticationError,
    RateLimitError,
    APIResponseError,
    APIConnectionError,
)


class _DummyResponse:
    """Minimal :class:`requests.Response` replacement for tests."""

    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload
        # Provide a *text* attribute for error preview
        self.text = json.dumps(payload)

    def json(self):  # noqa: D401 – mimic requests.Response
        return self._payload


class _StubSession:
    """Simple stub that mimics *requests.Session* expected contract."""

    def __init__(self):
        # List of tuples (url, payload) of received POSTs for inspection
        self.called: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}

        # Pre‑configured queue of responses the test can push
        self._responses: List[_DummyResponse] = []

    # pylint: disable=unused-argument
    def post(self, url: str, json: Dict[str, Any], timeout: int):  # type: ignore[override]
        if not self._responses:
            raise RuntimeError("No stubbed responses available (forgot to push one)?")
        self.called.append({"url": url, "payload": json})
        return self._responses.pop(0)

    def push(self, status_code: int, payload: Dict[str, Any]):
        self._responses.append(_DummyResponse(status_code, payload))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def stub_session():
    return _StubSession()


@pytest.fixture()
def service(stub_session):
    return DeepSeekService(api_key="dummy", session=stub_session, cache_enabled=True)


# ---------------------------------------------------------------------------
# Tests – success path
# ---------------------------------------------------------------------------


def test_completion_success(service: DeepSeekService, stub_session: _StubSession):
    # Prepare stubbed successful response
    stub_session.push(
        200,
        {
            "choices": [
                {
                    "text": "Hello world!",
                }
            ]
        },
    )

    result = service.completion("Hi")
    assert result == "Hello world!"
    assert len(stub_session.called) == 1


# ---------------------------------------------------------------------------
# Tests – caching
# ---------------------------------------------------------------------------


def test_completion_cache_hit(service: DeepSeekService, stub_session: _StubSession):
    # Push only *one* response, call twice – second call must use cache.
    payload = {
        "choices": [
            {
                "text": "Cached response",
            }
        ]
    }
    stub_session.push(200, payload)

    first = service.completion("Prompt")
    second = service.completion("Prompt")

    assert first == second == "Cached response"
    # Only one network call expected because of cache
    assert len(stub_session.called) == 1


# ---------------------------------------------------------------------------
# Tests – error handling
# ---------------------------------------------------------------------------


def test_rate_limit_error(service: DeepSeekService, stub_session: _StubSession):
    stub_session.push(429, {"error": "rate limit"})
    with pytest.raises(RateLimitError):
        service.completion("Hi")


def test_authentication_error(stub_session):
    # Instantiate service without API key to trigger error immediately
    with pytest.raises(AuthenticationError):
        DeepSeekService(api_key="", session=stub_session)


def test_unexpected_status_error(service: DeepSeekService, stub_session: _StubSession):
    stub_session.push(500, {"error": "server"})
    with pytest.raises(APIResponseError):
        service.completion("Hi")


def test_network_error(monkeypatch):
    # Make session.post raise RequestException to emulate network failure
    from requests import RequestException

    class _FailSession(_StubSession):
        def post(self, url, json, timeout):  # type: ignore[override]
            raise RequestException("boom")

    svc = DeepSeekService(api_key="dummy", session=_FailSession())

    with pytest.raises(APIConnectionError):
        svc.completion("Hi") 