import sys

import pytest

from regscope.collectors.call_graph import collect_call_graph


def test_collect_call_graph_counts_nested_calls() -> None:
    def child() -> str:
        return "done"

    def parent() -> str:
        return child()

    result, graph = collect_call_graph(parent)

    assert result == "done"
    assert graph["test_call_graph.test_collect_call_graph_counts_nested_calls.<locals>.parent"] == 1
    assert graph["test_call_graph.test_collect_call_graph_counts_nested_calls.<locals>.child"] == 1


def test_collect_call_graph_restores_existing_profiler() -> None:
    events = []

    def existing_profiler(frame, event, arg):
        events.append(event)

    sys.setprofile(existing_profiler)
    try:
        collect_call_graph(lambda: None)
        assert events
        assert sys.getprofile() is existing_profiler
    finally:
        sys.setprofile(None)


def test_collect_call_graph_restores_profiler_after_exception() -> None:
    existing_profiler = lambda frame, event, arg: None
    sys.setprofile(existing_profiler)
    try:
        with pytest.raises(RuntimeError, match="boom"):
            collect_call_graph(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert sys.getprofile() is existing_profiler
    finally:
        sys.setprofile(None)


def test_collect_call_graph_preserves_existing_local_callbacks() -> None:
    local_events = []

    def local_profiler(frame, event, arg):
        local_events.append(event)

    def existing_profiler(frame, event, arg):
        if event == "call":
            return local_profiler
        return None

    def work() -> None:
        return None

    sys.setprofile(existing_profiler)
    try:
        collect_call_graph(work)
    finally:
        sys.setprofile(None)

    assert "return" in local_events
