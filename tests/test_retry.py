from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from jfa_talent_analysis.sources import retry
from jfa_talent_analysis.sources.retry import parse_retry_after, request_with_retry


class FakeResponse:
    def __init__(self, body: str = "ok", content_type: str = "text/html") -> None:
        self.status = 200
        self.headers = {"content-type": content_type}
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def http_error(code: int, headers: dict[str, str] | None = None) -> HTTPError:
    return HTTPError("https://example.com", code, "error", headers or {}, None)


def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []
    monkeypatch.setattr(retry.time, "sleep", delays.append)
    return delays


def test_returns_response_without_retry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(retry, "urlopen", lambda request, timeout: FakeResponse("body"))

    status, content_type, content = request_with_retry(Request("https://example.com"))

    assert (status, content_type, content) == (200, "text/html", "body")


def test_retries_transient_server_error(monkeypatch: pytest.MonkeyPatch):
    delays = no_sleep(monkeypatch)
    attempts: list[int] = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        if len(attempts) < 3:
            raise http_error(503)
        return FakeResponse()

    monkeypatch.setattr(retry, "urlopen", fake_urlopen)

    status, _, _ = request_with_retry(Request("https://example.com"), backoff_seconds=1.0)

    assert status == 200
    assert len(attempts) == 3
    assert delays == [1.0, 2.0]


def test_honors_retry_after_on_429(monkeypatch: pytest.MonkeyPatch):
    delays = no_sleep(monkeypatch)
    attempts: list[int] = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise http_error(429, {"Retry-After": "7"})
        return FakeResponse()

    monkeypatch.setattr(retry, "urlopen", fake_urlopen)

    status, _, _ = request_with_retry(Request("https://example.com"))

    assert status == 200
    assert delays == [7.0]


def test_does_not_retry_client_errors(monkeypatch: pytest.MonkeyPatch):
    no_sleep(monkeypatch)
    attempts: list[int] = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        raise http_error(404)

    monkeypatch.setattr(retry, "urlopen", fake_urlopen)

    with pytest.raises(HTTPError):
        request_with_retry(Request("https://example.com"))

    assert len(attempts) == 1


def test_raises_after_retries_exhausted(monkeypatch: pytest.MonkeyPatch):
    no_sleep(monkeypatch)
    attempts: list[int] = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        raise URLError("connection refused")

    monkeypatch.setattr(retry, "urlopen", fake_urlopen)

    with pytest.raises(URLError):
        request_with_retry(Request("https://example.com"), retries=2)

    assert len(attempts) == 3


def test_parse_retry_after_defaults_to_five_seconds():
    assert parse_retry_after("2") == 2.0
    assert parse_retry_after("") == 5.0
    assert parse_retry_after("0") == 1.0
