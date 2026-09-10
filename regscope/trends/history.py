"""Append-only historical trend records for observed profiles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import List, Optional, Union

from ..models import BehaviorProfile, SCHEMA_VERSION


@dataclass(frozen=True)
class TrendPoint:
    function: str
    recorded_at: str
    duration_ns: int
    call_count: int
    exceptions: int
    fingerprint: str
    schema_version: int = 1

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
        data.setdefault("schema_version", 1)
        if data["schema_version"] > SCHEMA_VERSION:
            raise ValueError(f"unsupported history schema version {data['schema_version']}")
        return cls(**data)


@dataclass(frozen=True)
class TrendSummary:
    function: str
    samples: int
    duration_min_ns: int
    duration_median_ns: int
    duration_max_ns: int
    duration_first_ns: int
    duration_latest_ns: int
    duration_delta_ns: int
    duration_change_ratio: float
    exception_samples: int
    exception_rate: float


class HistoryStore:
    """Store append-only trend points in one JSONL file per function."""

    def __init__(self, directory: Union[str, Path], max_points: Optional[int] = None) -> None:
        if max_points is not None and max_points < 1:
            raise ValueError("max_points must be at least 1")
        self.directory = Path(directory)
        self.max_points = max_points

    def path_for(self, function: str) -> Path:
        digest = hashlib.sha256(function.encode("utf-8")).hexdigest()[:16]
        return self.directory / f"{digest}.jsonl"

    def record(self, profile: BehaviorProfile, recorded_at: Optional[str] = None) -> TrendPoint:
        self.directory.mkdir(parents=True, exist_ok=True)
        point = TrendPoint.from_profile(profile, recorded_at=recorded_at)
        points = self.load(profile.function)
        points.append(point)
        if self.max_points is not None:
            points = points[-self.max_points :]
        temporary = self.path_for(profile.function).with_suffix(".tmp")
        temporary.write_text(
            "".join(item.to_json() + "\n" for item in points), encoding="utf-8"
        )
        temporary.replace(self.path_for(profile.function))
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
        first_duration = durations[0]
        latest_duration = durations[-1]
        change_ratio = (
            0.0
            if first_duration == 0 and latest_duration == 0
            else float("inf")
            if first_duration == 0
            else (latest_duration - first_duration) / first_duration
        )
        exception_samples = sum(point.exceptions for point in points)
        return TrendSummary(
            function=function,
            samples=len(points),
            duration_min_ns=min(durations),
            duration_median_ns=int(median(durations)),
            duration_max_ns=max(durations),
            duration_first_ns=first_duration,
            duration_latest_ns=latest_duration,
            duration_delta_ns=latest_duration - first_duration,
            duration_change_ratio=change_ratio,
            exception_samples=exception_samples,
            exception_rate=exception_samples / len(points),
        )
