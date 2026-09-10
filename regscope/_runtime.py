"""Low-level synchronous execution measurement."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple, TypeVar

from .models import BehaviorProfile


T = TypeVar("T")


def measure_sync(
    function: Callable[..., T],
    *args: Any,
    profile_sink: Optional[Callable[[BehaviorProfile], None]] = None,
    **kwargs: Any,
) -> Tuple[T, BehaviorProfile]:
    """Call ``function`` and return its result together with an observation.

    Exceptions are counted and re-raised unchanged. ``profile_sink`` receives
    the profile for both successful and exceptional calls, allowing callers to
    persist the observation without changing the function's semantics.
    """
    started = time.perf_counter_ns()
    exception_count = 0
    try:
        result = function(*args, **kwargs)
    except BaseException:
        exception_count = 1
        raise
    finally:
        duration_ns = time.perf_counter_ns() - started
        observed = BehaviorProfile(
            function=_function_name(function),
            duration_ns=duration_ns,
            exceptions=exception_count,
        )
        if profile_sink is not None:
            profile_sink(observed)

    return result, observed


def _function_name(function: Callable[..., Any]) -> str:
    module = getattr(function, "__module__", "__main__")
    qualified_name = getattr(function, "__qualname__", getattr(function, "__name__", "<callable>"))
    return f"{module}.{qualified_name}"
