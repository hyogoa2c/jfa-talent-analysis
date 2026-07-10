from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def request_with_retry(
    request: Request,
    *,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> tuple[int, str | None, str]:
    """Fetch a request, retrying transient server errors and network failures.

    Retries 429 and 5xx responses plus connection-level errors with exponential
    backoff, honoring Retry-After on 429. Other HTTP errors raise immediately.
    Returns (status, content-type, body).
    """
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                return response.status, response.headers.get("content-type"), content
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS_CODES or attempt >= retries:
                raise
            if error.code == 429:
                delay = parse_retry_after(error.headers.get("Retry-After", ""))
            else:
                delay = backoff_seconds * (2**attempt)
        except (TimeoutError, URLError):
            if attempt >= retries:
                raise
            delay = backoff_seconds * (2**attempt)
        time.sleep(delay)
    raise AssertionError("unreachable")


def parse_retry_after(value: str) -> float:
    try:
        return max(float(value), 1.0)
    except ValueError:
        return 5.0
