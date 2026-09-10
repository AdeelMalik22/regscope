"""Call-count collection using Python's process profiler hook."""

from __future__ import annotations

import sys
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

    def profiler(frame: FrameType, event: str, arg: Any) -> None:
        if previous is not None:
            previous(frame, event, arg)
        if event == "call":
            counts[_frame_name(frame)] += 1

    sys.setprofile(profiler)
    try:
        result = function(*args, **kwargs)
    finally:
        sys.setprofile(previous)

    return result, dict(sorted(counts.items()))


def _frame_name(frame: FrameType) -> str:
    module = frame.f_globals.get("__name__", "__main__")
    return f"{module}.{frame.f_code.co_qualname}"
