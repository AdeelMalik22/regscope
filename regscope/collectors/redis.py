"""Optional count-only instrumentation for redis-py commands."""

from __future__ import annotations

from functools import wraps
from threading import Lock
from typing import Any, Callable, ClassVar, Optional


class RedisCollector:
    """Count redis-py commands without recording keys, values, or arguments.

    The redis-py hook is process-global while attached. Do not attach multiple
    Redis collectors concurrently; use one collector per tracked execution.
    """

    _active_owner: ClassVar[Optional["RedisCollector"]] = None
    _ownership_lock: ClassVar[Lock] = Lock()

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._original: Optional[Callable[..., Any]] = None
        self._wrapped: Optional[Callable[..., Any]] = None
        self._count = 0
        self._lock = Lock()

    def attach(self) -> None:
        try:
            import redis
        except ImportError as error:
            raise RuntimeError(
                "Redis tracking requires the 'redis' extra: install regscope[redis]"
            ) from error
        with self._ownership_lock:
            if self._original is not None:
                raise RuntimeError("collector is already attached")
            if type(self)._active_owner is not None:
                raise RuntimeError("another Redis collector is already attached")

            original = redis.Redis.execute_command

            @wraps(original)
            def counted_command(client: Any, *args: Any, **kwargs: Any) -> Any:
                with self._lock:
                    self._count += 1
                return original(client, *args, **kwargs)

            redis.Redis.execute_command = counted_command
            self._redis = redis
            self._original = original
            self._wrapped = counted_command
            type(self)._active_owner = self

    def detach(self) -> None:
        if (
            self._redis is not None
            and self._original is not None
            and self._wrapped is not None
            and self._redis.Redis.execute_command is self._wrapped
        ):
            self._redis.Redis.execute_command = self._original
        with self._ownership_lock:
            if type(self)._active_owner is self:
                type(self)._active_owner = None
        self._redis = None
        self._original = None
        self._wrapped = None

    @property
    def command_count(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._count = 0
