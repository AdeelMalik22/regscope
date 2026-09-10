"""Call-count collection using Python's process profiler hook."""

from __future__ import annotations

import sys
from inspect import iscoroutinefunction
from collections import Counter
from types import FrameType
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar


T = TypeVar("T")
ProfileFunction = Callable[[FrameType, str, Any], Optional[Callable[..., Any]]]


def collect_call_graph(
    function: Callable[..., T], *args: Any, **kwargs: Any
) -> Tuple[T, Dict[str, int]]:
    """Execute ``function`` while counting Python function-call events.

    Any profiler that was installed before collection is called for each
    event, and the previous profiler is restored even when execution raises.
    The returned mapping is flat and keyed by qualified function name.
    """
    counts: Counter[str] = Counter()
    previous = sys.getprofile()
    local_callbacks: Dict[int, ProfileFunction] = {}

    def profiler(frame: FrameType, event: str, arg: Any) -> None:
        if previous is not None:
            if event == "call":
                callback = previous(frame, event, arg)
                if callback is not None:
                    local_callbacks[id(frame)] = callback
            else:
                callback = local_callbacks.get(id(frame))
                if callback is not None:
                    callback(frame, event, arg)
        if event == "call":
            counts[_frame_name(frame)] += 1
        elif event == "return":
            local_callbacks.pop(id(frame), None)

    sys.setprofile(profiler)
    try:
        result = function(*args, **kwargs)
    finally:
        if sys.getprofile() is profiler:
            sys.setprofile(previous)

    return result, dict(sorted(counts.items()))


async def collect_async_call_graph(
    function: Callable[..., T], *args: Any, **kwargs: Any
) -> Tuple[T, Dict[str, int]]:
    """Async equivalent of :func:`collect_call_graph`."""
    if not iscoroutinefunction(function):
        raise TypeError("collect_async_call_graph requires an async function")

    counts: Counter[str] = Counter()
    previous = sys.getprofile()
    local_callbacks: Dict[int, ProfileFunction] = {}

    def profiler(frame: FrameType, event: str, arg: Any) -> None:
        if previous is not None:
            if event == "call":
                callback = previous(frame, event, arg)
                if callback is not None:
                    local_callbacks[id(frame)] = callback
            else:
                callback = local_callbacks.get(id(frame))
                if callback is not None:
                    callback(frame, event, arg)
        if event == "call":
            counts[_frame_name(frame)] += 1
        elif event == "return":
            local_callbacks.pop(id(frame), None)

    sys.setprofile(profiler)
    try:
        result = await function(*args, **kwargs)
    finally:
        if sys.getprofile() is profiler:
            sys.setprofile(previous)

    return result, dict(sorted(counts.items()))


def _frame_name(frame: FrameType) -> str:
    module = frame.f_globals.get("__name__", "__main__")
    qualified_name = getattr(frame.f_code, "co_qualname", frame.f_code.co_name)
    return f"{module}.{qualified_name}"
