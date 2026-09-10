"""Optional count-only HTTP instrumentation for requests."""

from __future__ import annotations

from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional


class HTTPCollector:
    """Count outgoing ``requests`` calls without recording request data.

    The requests hook is process-global while attached. Do not attach multiple
    HTTP collectors concurrently; use one collector per tracked execution.
    """

    def __init__(self) -> None:
        self._requests: Optional[Any] = None
        self._original: Optional[Callable[..., Any]] = None
        self._count = 0
        self._lock = Lock()

    def attach(self) -> None:
        try:
            import requests
        except ImportError as error:
            raise RuntimeError(
                "HTTP tracking requires the 'http' extra: install regscope[http]"
            ) from error
        if self._original is not None:
            raise RuntimeError("collector is already attached")

        original = requests.sessions.Session.request

        @wraps(original)
        def counted_request(session: Any, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
            with self._lock:
                self._count += 1
            return original(session, method, url, *args, **kwargs)

        requests.sessions.Session.request = counted_request
        self._requests = requests
        self._original = original

    def detach(self) -> None:
        if self._requests is not None and self._original is not None:
            self._requests.sessions.Session.request = self._original
        self._requests = None
        self._original = None

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._count = 0
