"""Decorators for collecting observed function behavior."""

from __future__ import annotations

import time
from inspect import iscoroutinefunction
from functools import wraps
from os import PathLike
from typing import Any, Callable, Optional, TypeVar, Union, cast

from ..collectors.call_graph import collect_async_call_graph, collect_call_graph
from ..core.comparison import compare
from ..models import BehaviorProfile
from ..storage import BaselineStore
from .config import TrackConfig


T = TypeVar("T")
Function = Callable[..., T]


def track(
    function: Optional[Function[T]] = None,
    *,
    baseline_dir: Union[PathLike[str], str] = ".regscope",
    max_runs: int = 5,
) -> Any:
    """Decorate a function with runtime collection and baseline persistence."""
    config = TrackConfig(baseline_dir=baseline_dir, max_runs=max_runs)
    if function is None:
        return lambda wrapped: track(
            wrapped,
            baseline_dir=config.baseline_dir,
            max_runs=config.max_runs,
        )

    if iscoroutinefunction(function):
        return _track_async(function, config)

    store = BaselineStore(config.baseline_dir, max_runs=config.max_runs)

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
            wrapper.last_comparison = compare(
                wrapper.last_profile, store.load(wrapper.last_profile.function)
            )
            store.append(wrapper.last_profile)

    wrapper.last_profile = None  # type: ignore[attr-defined]
    wrapper.last_comparison = None  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)


def _track_async(
    function: Function[T], config: TrackConfig
) -> Any:
    store = BaselineStore(config.baseline_dir, max_runs=config.max_runs)

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
            wrapper.last_comparison = compare(
                wrapper.last_profile, store.load(wrapper.last_profile.function)
            )
            store.append(wrapper.last_profile)

    wrapper.last_profile = None  # type: ignore[attr-defined]
    wrapper.last_comparison = None  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)
