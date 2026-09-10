"""Append-only historical trend records for observed profiles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import List, Optional, Union

from ..models import BehaviorProfile


@dataclass(frozen=True)
class TrendPoint:
    function: str
    recorded_at: str
    duration_ns: int
    call_count: int
    exceptions: int
    fingerprint: str

    @classmethod
    def from_profile(
        cls, profile: BehaviorProfile, recorded_at: Optional[str] = None
    ) -> "TrendPoint":
        timestamp = recorded_at or datetime.now(timezone.utc).isoformat()
        return cls(
            function=profile.function,
            recorded_at=timestamp,
            duration_ns=profile.duration_ns,
            call_count=profile.call_count,
            exceptions=profile.exceptions,
            fingerprint=profile.fingerprint(),
        )

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "TrendPoint":
        data = json.loads(value)
        return cls(**data)


@dataclass(frozen=True)
class TrendSummary:
    function: str
    samples: int
    duration_min_ns: int
    duration_median_ns: int
    duration_max_ns: int
    exception_samples: int


class HistoryStore:
    """Store append-only trend points in one JSONL file per function."""

    def __init__(self, directory: Union[str, Path]) -> None:
        self.directory = Path(directory)

    def path_for(self, function: str) -> Path:
        digest = hashlib.sha256(function.encode("utf-8")).hexdigest()[:16]
        return self.directory / f"{digest}.jsonl"

    def record(self, profile: BehaviorProfile, recorded_at: Optional[str] = None) -> TrendPoint:
        self.directory.mkdir(parents=True, exist_ok=True)
        point = TrendPoint.from_profile(profile, recorded_at=recorded_at)
        with self.path_for(profile.function).open("a", encoding="utf-8") as handle:
            handle.write(point.to_json() + "\n")
        return point

    def load(self, function: str) -> List[TrendPoint]:
        path = self.path_for(function)
        if not path.exists():
            return []
        return [
            TrendPoint.from_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def summarize(self, function: str) -> TrendSummary:
        points = self.load(function)
        if not points:
            raise ValueError("no historical samples for function")
        durations = [point.duration_ns for point in points]
        return TrendSummary(
            function=function,
            samples=len(points),
            duration_min_ns=min(durations),
            duration_median_ns=int(median(durations)),
            duration_max_ns=max(durations),
            exception_samples=sum(point.exceptions for point in points),
        )
