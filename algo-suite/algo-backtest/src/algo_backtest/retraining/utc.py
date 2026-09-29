"""UTC-instant helpers shared by the retraining components.

Every retraining timestamp is an explicit UTC instant: tz-aware with offset zero. Naive or
offset datetimes are rejected rather than converted, because a silently assumed zone is
exactly the kind of hidden default that moves a label across a fitting boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def require_utc(value: datetime, *, what: str) -> None:
    """Reject naive or non-UTC timestamps, naming `what` in the failure."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(
            f"retraining: {what} must be a UTC instant (tz-aware, offset 0), got {value!r}; "
            "convert the source timestamps with .astimezone(UTC) before use"
        )


def iso_utc(value: datetime) -> str:
    """A UTC instant as `YYYY-MM-DDTHH:MM:SSZ` (microseconds kept when present)."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
