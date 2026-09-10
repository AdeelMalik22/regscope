import tracemalloc

from regscope.collectors import MemoryCollector, MemoryProfile


def test_memory_collector_reports_peak_and_delta() -> None:
    collector = MemoryCollector()

    with collector.measure():
        values = ["value"] * 1000

    assert values
    assert isinstance(collector.last_profile, MemoryProfile)
    assert collector.last_profile.peak > 0


def test_memory_collector_preserves_existing_tracer() -> None:
    tracemalloc.start()
    try:
        collector = MemoryCollector()
        with collector.measure():
            _ = [object() for _ in range(10)]
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()
