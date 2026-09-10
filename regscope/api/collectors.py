"""Optional collector lifecycle for tracked executions."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import Any, Dict, Iterator

from ..collectors import HTTPCollector, MemoryCollector, RedisCollector, SQLAlchemyCollector
from .config import TrackConfig


@contextmanager
def active_collectors(config: TrackConfig, metrics: Dict[str, int]) -> Iterator[None]:
    """Attach configured collectors and publish their metrics on exit."""
    with ExitStack() as stack:
        if config.sqlalchemy_engine is not None:
            collector = SQLAlchemyCollector()
            collector.attach(config.sqlalchemy_engine)
            stack.callback(collector.detach)
            metrics["db_queries"] = 0
            stack.callback(lambda: metrics.update(db_queries=collector.query_count))

        if config.collect_http:
            collector = HTTPCollector()
            collector.attach()
            stack.callback(collector.detach)
            metrics["http_requests"] = 0
            stack.callback(lambda: metrics.update(http_requests=collector.request_count))

        if config.collect_redis:
            collector = RedisCollector()
            collector.attach()
            stack.callback(collector.detach)
            metrics["redis_commands"] = 0
            stack.callback(lambda: metrics.update(redis_commands=collector.command_count))

        memory = None
        if config.collect_memory:
            memory = MemoryCollector()
            stack.callback(
                lambda: metrics.update(
                    memory_current_delta=memory.last_profile.current_delta,
                    memory_peak=memory.last_profile.peak,
                )
                if memory.last_profile is not None
                else None
            )
            stack.enter_context(memory.measure())

        yield
