"""Validated public configuration for tracked functions."""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import Any, Union


@dataclass(frozen=True)
class TrackConfig:
    """Configuration shared by a tracked function's collectors and storage."""

    baseline_dir: Union[PathLike[str], str] = ".regscope"
    max_runs: int = 5
    sqlalchemy_engine: Any = None
    collect_http: bool = False
    collect_redis: bool = False
    collect_memory: bool = False

    def __post_init__(self) -> None:
        if self.max_runs < 1:
            raise ValueError("max_runs must be at least 1")
