"""Pure event-feature policies independent of storage adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from algo_score.events.grid import forward_filled_values
from algo_score.events.models import DailyValue, GdeltFeature, GprFeature

EventFeature = GdeltFeature | GprFeature


@dataclass(frozen=True)
class EventFeatureSpec:
    """Policy for turning one event source into minute feature rows."""

    kind: str
    model: type[EventFeature]
    make_row: Callable[[datetime, DailyValue | None], EventFeature]


GPR_SPEC = EventFeatureSpec(
    kind="gpr",
    model=GprFeature,
    make_row=lambda timestamp, daily: GprFeature(
        timestamp=timestamp, gpr=daily.value if daily else None
    ),
)
GDELT_SPEC = EventFeatureSpec(
    kind="gdelt",
    model=GdeltFeature,
    make_row=lambda timestamp, daily: GdeltFeature(
        timestamp=timestamp,
        event_intensity=daily.value if daily else None,
        available_at=daily.available_at if daily else None,
    ),
)
EVENT_FEATURE_SPECS = {
    GPR_SPEC.kind: GPR_SPEC,
    GDELT_SPEC.kind: GDELT_SPEC,
}


def known_kinds() -> tuple[str, ...]:
    """Return the supported event-feature kinds in stable CLI order."""
    return tuple(EVENT_FEATURE_SPECS)


def spec_for(kind: str) -> EventFeatureSpec:
    """Return the feature spec for ``kind`` or fail fast with known kinds."""
    try:
        return EVENT_FEATURE_SPECS[kind]
    except KeyError as exc:
        known = ", ".join(known_kinds())
        raise ValueError(f"unknown event kind: {kind!r}; known kinds: {known}") from exc


def feature_rows(
    spec: EventFeatureSpec, daily_values: list[DailyValue], minutes: list[datetime]
) -> list[EventFeature]:
    """Forward-fill ``daily_values`` over ``minutes`` and build feature rows."""
    forward_filled = forward_filled_values(daily_values, minutes)
    return [
        spec.make_row(minute, daily) for minute, daily in zip(minutes, forward_filled, strict=True)
    ]
