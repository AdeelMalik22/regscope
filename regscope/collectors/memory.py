"""Memory measurements using the Python standard library."""

from __future__ import annotations

import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass(frozen=True)
class MemoryProfile:
    """Traced memory values in bytes for one measured region."""

    current_delta: int
    peak: int


class MemoryCollector:
    """Measure traced current allocation changes and peak memory."""

    def __init__(self) -> None:
        self.last_profile: Optional[MemoryProfile] = None

    @contextmanager
    def measure(self) -> Iterator[None]:
        """Measure allocations made inside the context."""
        already_tracing = tracemalloc.is_tracing()
        if not already_tracing:
            tracemalloc.start()
        started_current, _ = tracemalloc.get_traced_memory()
        try:
            yield
        finally:
            current, peak = tracemalloc.get_traced_memory()
            self.last_profile = MemoryProfile(
                current_delta=current - started_current,
                peak=peak,
            )
            if not already_tracing:
                tracemalloc.stop()
