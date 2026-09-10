"""Optional SQLAlchemy query-count collector.

Only statement counts are recorded. SQL text, parameters, and result data are
intentionally never retained.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Callable, Optional


class SQLAlchemyCollector:
    """Count SQLAlchemy cursor executions for one engine."""

    def __init__(self) -> None:
        self._event: Optional[Any] = None
        self._engine: Optional[Any] = None
        self._count = 0
        self._lock = Lock()

    def attach(self, engine: Any) -> None:
        """Attach to an SQLAlchemy engine, importing SQLAlchemy lazily."""
        try:
            from sqlalchemy import event
        except ImportError as error:
            raise RuntimeError(
                "SQLAlchemy query tracking requires the 'db' extra: "
                "install regscope[db]"
            ) from error
        if self._engine is not None:
            raise RuntimeError("collector is already attached")
        event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
        self._event = event
        self._engine = engine

    def detach(self) -> None:
        """Remove the event listener if this collector is attached."""
        if self._engine is not None and self._event is not None:
            self._event.remove(
                self._engine, "before_cursor_execute", self._before_cursor_execute
            )
        self._engine = None
        self._event = None

    @property
    def query_count(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._count = 0

    def _before_cursor_execute(self, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            self._count += 1
