"""Optional count-only instrumentation for redis-py commands."""

from __future__ import annotations

from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional


class RedisCollector:
    """Count redis-py commands without recording keys, values, or arguments.

    The redis-py hook is process-global while attached. Do not attach multiple
    Redis collectors concurrently; use one collector per tracked execution.
    """

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._original: Optional[Callable[..., Any]] = None
        self._count = 0
        self._lock = Lock()

    def attach(self) -> None:
        try:
            import redis
        except ImportError as error:
            raise RuntimeError(
                "Redis tracking requires the 'redis' extra: install regscope[redis]"
            ) from error
        if self._original is not None:
            raise RuntimeError("collector is already attached")

        original = redis.Redis.execute_command

        @wraps(original)
        def counted_command(client: Any, *args: Any, **kwargs: Any) -> Any:
            with self._lock:
                self._count += 1
            return original(client, *args, **kwargs)

        redis.Redis.execute_command = counted_command
        self._redis = redis
        self._original = original

    def detach(self) -> None:
        if self._redis is not None and self._original is not None:
            self._redis.Redis.execute_command = self._original
        self._redis = None
        self._original = None

    @property
    def command_count(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._count = 0
