"""GDELT event-intensity feature helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from algo_score.events.build import build_event_features
from algo_score.events.models import EventFeatureReport


def build(data_root: Path, start: date, end: date) -> EventFeatureReport:
    """Build GDELT event-intensity features for the inclusive date window."""
    return build_event_features(data_root, "gdelt", start, end)
