import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from regscope.collectors.call_graph import collect_call_graph


def test_collect_call_graph_counts_nested_calls() -> None:
    def child() -> str:
        return "done"

    def parent() -> str:
        return child()

    result, graph = collect_call_graph(parent)

    assert result == "done"
    assert next(value for name, value in graph.items() if name.endswith(".parent")) == 1
    assert next(value for name, value in graph.items() if name.endswith(".child")) == 1


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


def test_nested_collection_restores_outer_profiler() -> None:
    observed_profiles = []

    def inner() -> str:
        return "inner"

    def outer() -> str:
        result, _ = collect_call_graph(inner)
        observed_profiles.append(sys.getprofile())
        return result

    result, graph = collect_call_graph(outer)

    assert result == "inner"
    assert observed_profiles
    assert observed_profiles[0] is not None
    assert any(name.endswith(".outer") for name in graph)


def test_collection_is_independent_between_threads() -> None:
    def left() -> str:
        return "left"

    def right() -> str:
        return "right"

    with ThreadPoolExecutor(max_workers=2) as executor:
        left_future = executor.submit(collect_call_graph, left)
        right_future = executor.submit(collect_call_graph, right)
        left_result, left_graph = left_future.result()
        right_result, right_graph = right_future.result()

    assert left_result == "left"
    assert right_result == "right"
    assert any(name.endswith(".left") for name in left_graph)
    assert not any(name.endswith(".right") for name in left_graph)
    assert any(name.endswith(".right") for name in right_graph)
    assert not any(name.endswith(".left") for name in right_graph)


def test_collection_does_not_clobber_profiler_installed_during_execution() -> None:
    external_events = []

    def external_profiler(frame, event, arg):
        external_events.append(event)

    def install_external_profiler() -> None:
        sys.setprofile(external_profiler)

    collect_call_graph(install_external_profiler)

    try:
        assert sys.getprofile() is external_profiler
        assert external_events
    finally:
        sys.setprofile(None)
