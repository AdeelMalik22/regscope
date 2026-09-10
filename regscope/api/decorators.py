"""Decorators for collecting observed function behavior."""

from __future__ import annotations

import time
from inspect import iscoroutinefunction
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from ..collectors.call_graph import collect_async_call_graph, collect_call_graph
from ..models import BehaviorProfile


T = TypeVar("T")
Function = Callable[..., T]


def track(function: Optional[Function[T]] = None) -> Any:
    """Decorate a synchronous function with runtime behavior collection."""
    if function is None:
        return lambda wrapped: track(wrapped)

    if iscoroutinefunction(function):
        return _track_async(function)

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        started = time.perf_counter_ns()
        exception_count = 0
        graph = {}
        try:
            result, graph = collect_call_graph(function, *args, **kwargs)
            return result
        except BaseException:
            exception_count = 1
            raise
        finally:
            wrapper.last_profile = BehaviorProfile(
                function=f"{function.__module__}.{function.__qualname__}",
                duration_ns=time.perf_counter_ns() - started,
                exceptions=exception_count,
                call_graph=graph,
            )

    wrapper.last_profile = None  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)


def _track_async(function: Function[T]) -> Any:
    @wraps(function)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        started = time.perf_counter_ns()
        exception_count = 0
        graph = {}
        try:
            result, graph = await collect_async_call_graph(function, *args, **kwargs)
            return result
        except BaseException:
            exception_count = 1
            raise
        finally:
            wrapper.last_profile = BehaviorProfile(
                function=f"{function.__module__}.{function.__qualname__}",
                duration_ns=time.perf_counter_ns() - started,
                exceptions=exception_count,
                call_graph=graph,
            )

    wrapper.last_profile = None  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)
