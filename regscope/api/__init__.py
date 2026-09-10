"""Public RegScope APIs."""

from .decorators import track
from .config import TrackConfig

__all__ = ["TrackConfig", "track"]
