"""Decorators for collecting observed function behavior."""

from __future__ import annotations

import time
from contextvars import ContextVar
from inspect import iscoroutinefunction
from functools import wraps
from os import PathLike
from typing import Any, Callable, Optional, TypeVar, Union, cast
from threading import Lock

from ..collectors.call_graph import collect_async_call_graph, collect_call_graph
from ..core.comparison import ComparisonResult, compare
from ..models import BehaviorProfile
from ..storage import BaselineStore
from ..trends import HistoryStore
from .config import TrackConfig
from .collectors import active_collectors


T = TypeVar("T")
Function = Callable[..., T]


def track(
    function: Optional[Function[T]] = None,
    *,
    baseline_dir: Union[PathLike[str], str] = ".regscope",
    history_dir: Union[PathLike[str], str] = ".regscope",
    max_runs: int = 5,
    warmup_runs: int = 0,
    sqlalchemy_engine: Any = None,
    collect_http: bool = False,
    collect_redis: bool = False,
    collect_memory: bool = False,
) -> Any:
    """Decorate a function with runtime collection and baseline persistence."""
    config = TrackConfig(
        baseline_dir=baseline_dir,
        history_dir=history_dir,
        max_runs=max_runs,
        warmup_runs=warmup_runs,
        sqlalchemy_engine=sqlalchemy_engine,
        collect_http=collect_http,
        collect_redis=collect_redis,
        collect_memory=collect_memory,
    )
    if function is None:
        return lambda wrapped: track(
            wrapped,
            baseline_dir=config.baseline_dir,
            history_dir=config.history_dir,
            max_runs=config.max_runs,
            warmup_runs=config.warmup_runs,
            sqlalchemy_engine=config.sqlalchemy_engine,
            collect_http=config.collect_http,
            collect_redis=config.collect_redis,
            collect_memory=config.collect_memory,
        )

    if iscoroutinefunction(function):
        return _track_async(function, config)

    store = BaselineStore(config.baseline_dir, max_runs=config.max_runs)
    history = HistoryStore(config.history_dir)
    current_profile: ContextVar[Optional[BehaviorProfile]] = ContextVar(
        "regscope_current_profile", default=None
    )
    current_comparison: ContextVar[Any] = ContextVar(
        "regscope_current_comparison", default=None
    )
    warmups_remaining = config.warmup_runs
    warmup_lock = Lock()

    def consume_warmup() -> bool:
        nonlocal warmups_remaining
        with warmup_lock:
            if warmups_remaining == 0:
                return False
            warmups_remaining -= 1
            return True

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        started = time.perf_counter_ns()
        exception_count = 0
        graph = {}
        metrics = {}
        try:
            with active_collectors(config, metrics):
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
                metrics=metrics,
            )
            current_profile.set(wrapper.last_profile)
            if consume_warmup():
                wrapper.last_comparison = ComparisonResult(
                    function=wrapper.last_profile.function,
                    metrics=[],
                    status="warmup",
                )
            else:
                wrapper.last_comparison = compare(
                    wrapper.last_profile, store.load(wrapper.last_profile.function)
                )
            current_comparison.set(wrapper.last_comparison)
            if wrapper.last_comparison.status != "warmup":
                store.append(wrapper.last_profile)
                history.record(wrapper.last_profile)

    wrapper.last_profile = None  # type: ignore[attr-defined]
    wrapper.last_comparison = None  # type: ignore[attr-defined]
    wrapper.get_current_profile = current_profile.get  # type: ignore[attr-defined]
    wrapper.get_current_comparison = current_comparison.get  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)


def _track_async(
    function: Function[T], config: TrackConfig
) -> Any:
    store = BaselineStore(config.baseline_dir, max_runs=config.max_runs)
    history = HistoryStore(config.history_dir)
    current_profile: ContextVar[Optional[BehaviorProfile]] = ContextVar(
        "regscope_current_profile", default=None
    )
    current_comparison: ContextVar[Any] = ContextVar(
        "regscope_current_comparison", default=None
    )
    warmups_remaining = config.warmup_runs
    warmup_lock = Lock()

    def consume_warmup() -> bool:
        nonlocal warmups_remaining
        with warmup_lock:
            if warmups_remaining == 0:
                return False
            warmups_remaining -= 1
            return True

    @wraps(function)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        started = time.perf_counter_ns()
        exception_count = 0
        graph = {}
        metrics = {}
        try:
            with active_collectors(config, metrics):
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
                metrics=metrics,
            )
            current_profile.set(wrapper.last_profile)
            if consume_warmup():
                wrapper.last_comparison = ComparisonResult(
                    function=wrapper.last_profile.function,
                    metrics=[],
                    status="warmup",
                )
            else:
                wrapper.last_comparison = compare(
                    wrapper.last_profile, store.load(wrapper.last_profile.function)
                )
            current_comparison.set(wrapper.last_comparison)
            if wrapper.last_comparison.status != "warmup":
                store.append(wrapper.last_profile)
                history.record(wrapper.last_profile)

    wrapper.last_profile = None  # type: ignore[attr-defined]
    wrapper.last_comparison = None  # type: ignore[attr-defined]
    wrapper.get_current_profile = current_profile.get  # type: ignore[attr-defined]
    wrapper.get_current_comparison = current_comparison.get  # type: ignore[attr-defined]
    return cast(Function[T], wrapper)
