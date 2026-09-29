"""Validated strategy selection for the two F1 direction sources."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PerceptionConfig:
    """EMA remains the default; smoothing lengths count bars of each timeframe."""

    source: str = "ema"
    period1: int = 6
    period2: int = 2
    higher_tf_minutes: int = 60


def _period(settings: Mapping[str, object], name: str, default: int, minimum: int) -> int:
    """Reject ambiguous YAML booleans, fractional periods and invalid timeframes."""
    value = settings.get(name, default)
    if type(value) is not int or value < minimum:
        raise ValueError(
            f"double_smoothed_heikin_ashi.{name} must be an integer >= {minimum}; "
            "fix the strategy config.yaml"
        )
    return value


def parse_perception_config(raw: Mapping[str, object]) -> PerceptionConfig:
    """Resolve the optional selector and reject malformed candidate settings."""
    source = raw.get("perception_source", "ema")
    if source not in ("ema", "double_smoothed_heikin_ashi"):
        raise ValueError(
            f"unknown perception_source {source!r}; set ema or double_smoothed_heikin_ashi "
            "in the strategy config.yaml"
        )
    settings = raw.get("double_smoothed_heikin_ashi", {})
    if not isinstance(settings, Mapping):
        raise ValueError("double_smoothed_heikin_ashi must be a mapping; fix strategy config.yaml")
    unknown = set(settings) - {"period1", "period2", "higher_tf_minutes"}
    if unknown:
        raise ValueError(
            f"unknown double_smoothed_heikin_ashi settings {sorted(unknown)!r}; "
            "use period1, period2 and higher_tf_minutes in strategy config.yaml"
        )
    return PerceptionConfig(
        source=str(source),
        period1=_period(settings, "period1", 6, 1),
        period2=_period(settings, "period2", 2, 1),
        higher_tf_minutes=_period(settings, "higher_tf_minutes", 60, 2),
    )
