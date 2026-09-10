"""Optional count-only HTTP instrumentation for requests."""

from __future__ import annotations

from functools import wraps
from threading import Lock
from typing import Any, Callable, ClassVar, Optional


class HTTPCollector:
    """Count outgoing ``requests`` calls without recording request data.

    The requests hook is process-global while attached. Do not attach multiple
    HTTP collectors concurrently; use one collector per tracked execution.
    """

    _active_owner: ClassVar[Optional["HTTPCollector"]] = None
    _ownership_lock: ClassVar[Lock] = Lock()

    def __init__(self) -> None:
        self._requests: Optional[Any] = None
        self._original: Optional[Callable[..., Any]] = None
        self._wrapped: Optional[Callable[..., Any]] = None
        self._count = 0
        self._lock = Lock()

    def attach(self) -> None:
        try:
            import requests
        except ImportError as error:
            raise RuntimeError(
                "HTTP tracking requires the 'http' extra: install regscope[http]"
            ) from error
        with self._ownership_lock:
            if self._original is not None:
                raise RuntimeError("collector is already attached")
            if type(self)._active_owner is not None:
                raise RuntimeError("another HTTP collector is already attached")

            original = requests.sessions.Session.request

            @wraps(original)
            def counted_request(session: Any, *args: Any, **kwargs: Any) -> Any:
                with self._lock:
                    self._count += 1
                return original(session, *args, **kwargs)

            requests.sessions.Session.request = counted_request
            self._requests = requests
            self._original = original
            self._wrapped = counted_request
            type(self)._active_owner = self

    def detach(self) -> None:
        if (
            self._requests is not None
            and self._original is not None
            and self._wrapped is not None
            and self._requests.sessions.Session.request is self._wrapped
        ):
            self._requests.sessions.Session.request = self._original
        with self._ownership_lock:
            if type(self)._active_owner is self:
                type(self)._active_owner = None
        self._requests = None
        self._original = None
        self._wrapped = None

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._count = 0
