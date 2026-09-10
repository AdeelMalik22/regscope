"""Atomic JSON persistence for behavior baselines."""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, Dict, Iterator, Optional

from ..models import Baseline, BehaviorProfile


class BaselineStore:
    """Store one bounded baseline file per tracked function."""

    _thread_locks: ClassVar[Dict[str, threading.RLock]] = {}
    _thread_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, directory: os.PathLike[str] | str, max_runs: int = 5) -> None:
        if max_runs < 1:
            raise ValueError("max_runs must be at least 1")
        self.directory = Path(directory)
        self.max_runs = max_runs

    def path_for(self, function: str) -> Path:
        digest = hashlib.sha256(function.encode("utf-8")).hexdigest()[:16]
        return self.directory / f"{digest}.json"

    def load(self, function: str) -> Baseline:
        path = self.path_for(function)
        if not path.exists():
            return Baseline(function=function, max_runs=self.max_runs)
        return Baseline.from_json(path.read_text(encoding="utf-8"))

    def save(self, baseline: Baseline) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.path_for(baseline.function)
        temporary: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory, delete=False
            ) as handle:
                temporary = handle.name
                handle.write(baseline.to_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
        return destination

    def append(self, profile: BehaviorProfile) -> Baseline:
        with self._append_lock(profile.function):
            baseline = self.load(profile.function)
            baseline.max_runs = self.max_runs
            baseline.add(profile)
            self.save(baseline)
            return baseline

    @contextmanager
    def _append_lock(self, function: str) -> Iterator[None]:
        path = self.path_for(function)
        with self._thread_lock(path):
            self.directory.mkdir(parents=True, exist_ok=True)
            lock_path = path.with_suffix(".lock")
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                _lock_file(lock_file)
                try:
                    yield
                finally:
                    _unlock_file(lock_file)

    @classmethod
    @contextmanager
    def _thread_lock(cls, path: Path) -> Iterator[None]:
        key = str(path)
        with cls._thread_locks_guard:
            lock = cls._thread_locks.setdefault(key, threading.RLock())
        with lock:
            yield


def _lock_file(handle: object) -> None:
    try:
        import fcntl
    except ImportError:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle: object) -> None:
    try:
        import fcntl
    except ImportError:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
