"""Public RegScope exception types."""


class RegScopeError(Exception):
    """Base class for expected RegScope errors."""


class MalformedRecordError(RegScopeError, ValueError):
    """A persisted baseline or history record cannot be decoded safely."""
