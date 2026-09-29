"""Optional non-directional quote-activity veto, independent of F7's feature families."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation


@dataclass(frozen=True)
class VolumeConfig:
    """Previous closed bars in the baseline and minimum acceptable activity ratio."""

    lookback: int = 20
    min_relative_activity: float = 1.0

    def __post_init__(self) -> None:
        """Reject malformed, nonfinite or nonpositive volume parameters."""
        if type(self.lookback) is not int or self.lookback < 1:
            raise ValueError("volume_strength.lookback must be a positive integer; fix config")
        value = self.min_relative_activity
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("volume_strength.min_relative_activity must be numeric; fix config")
        if not isfinite(value) or value <= 0:
            raise ValueError(
                "volume_strength.min_relative_activity must be finite and > 0; fix config"
            )


def parse_volume_config(raw: Mapping[str, Any], *, strategy: str) -> VolumeConfig:
    """Validate the optional filter's explicit section and reject unknown settings."""
    unknown = raw.keys() - asdict(VolumeConfig()).keys()
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: unknown volume_strength keys {sorted(unknown)}; fix config"
        )
    return VolumeConfig(**raw)


@dataclass
class VolumeStrengthFilter:
    """Veto low or unavailable activity; high activity is not a BUY or SELL recommendation."""

    config: VolumeConfig

    def apply(self, state: ExecutionState) -> FilterResult:
        """Record the strength and its tick-count basis; fail on malformed present evidence."""
        value = state.features.get("relative_tick_activity")
        metadata = {
            "basis": "quote_tick_count",
            "relative_activity": value,
            "threshold": self.config.min_relative_activity,
        }
        if value is None:
            return FilterResult(
                "volume_strength",
                Recommendation.ABSTAIN,
                "tick activity unavailable (warm-up or zero baseline)",
                veto=True,
                metadata=metadata,
            )
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("relative_tick_activity must be numeric; repair signal production")
        if not isfinite(value) or value < 0:
            raise ValueError(
                "relative_tick_activity must be finite and nonnegative; repair signal production"
            )
        return FilterResult(
            "volume_strength",
            Recommendation.ABSTAIN,
            f"relative tick activity {value:.6g}",
            veto=value < self.config.min_relative_activity,
            metadata=metadata,
        )
