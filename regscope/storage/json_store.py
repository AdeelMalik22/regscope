"""Atomic JSON persistence for behavior baselines."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional

from ..models import Baseline, BehaviorProfile


class BaselineStore:
    """Store one bounded baseline file per tracked function."""

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
        baseline = self.load(profile.function)
        baseline.max_runs = self.max_runs
        baseline.add(profile)
        self.save(baseline)
        return baseline
