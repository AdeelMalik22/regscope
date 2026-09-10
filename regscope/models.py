"""Structured records produced by RegScope collectors."""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


SCHEMA_VERSION = 1


def _validate_schema(version: int) -> None:
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema version {version}; maximum supported is {SCHEMA_VERSION}"
        )


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class BehaviorProfile:
    """One observed execution of a tracked function."""

    function: str
    duration_ns: int
    call_count: int = 0
    exceptions: int = 0
    call_graph: Dict[str, int] = field(default_factory=dict)
    metrics: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible structured representation."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize this profile deterministically."""
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        """Return a derived SHA-256 checksum of the structured profile."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BehaviorProfile":
        """Build a profile from a decoded JSON object."""
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        _validate_schema(schema_version)
        return cls(
            function=str(data["function"]),
            duration_ns=int(data["duration_ns"]),
            call_count=int(data.get("call_count", 0)),
            exceptions=int(data.get("exceptions", 0)),
            call_graph={str(k): int(v) for k, v in data.get("call_graph", {}).items()},
            metrics={str(k): int(v) for k, v in data.get("metrics", {}).items()},
            metadata=dict(data.get("metadata", {})),
            schema_version=schema_version,
        )

    @classmethod
    def from_json(cls, value: str) -> "BehaviorProfile":
        return cls.from_dict(json.loads(value))


@dataclass
class Baseline:
    """A bounded collection of observed profiles for one tracked function."""

    function: str
    runs: List[BehaviorProfile] = field(default_factory=list)
    max_runs: int = 5
    schema_version: int = SCHEMA_VERSION

    def add(self, profile: BehaviorProfile) -> None:
        if profile.function != self.function:
            raise ValueError("profile function does not match baseline function")
        if self.max_runs < 1:
            raise ValueError("max_runs must be at least 1")
        self.runs.append(profile)
        del self.runs[:-self.max_runs]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "runs": [profile.to_dict() for profile in self.runs],
            "max_runs": self.max_runs,
            "schema_version": self.schema_version,
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Baseline":
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        _validate_schema(schema_version)
        return cls(
            function=str(data["function"]),
            runs=[BehaviorProfile.from_dict(item) for item in data.get("runs", [])],
            max_runs=int(data.get("max_runs", 5)),
            schema_version=schema_version,
        )

    @classmethod
    def from_json(cls, value: str) -> "Baseline":
        return cls.from_dict(json.loads(value))
