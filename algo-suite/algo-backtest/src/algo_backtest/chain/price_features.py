"""The EMA/RSI/MACD periods behind the F1/F2 features and the F7 feature families, and
the ATR period behind F6's volatility stop distance (`atr_pips`, story 12).

They are strategy parameters — the `price_features` section of `strategies/<name>/
config.yaml` (2026-09-27 amendment, story 09) — with defaults for the values that almost
never change. Training (`training.py`) and serving (`engine/chain_algorithm.py`) read the
same object, so the two cannot drift, and the trainer records the effective values in the
model's provenance so `run --model` can refuse a model fitted on different periods.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any

_SECTION = "price_features"


@dataclass(frozen=True)
class PriceFeatureConfig:
    """Indicator periods, in minute bars. Defaults are the pilot's original constants."""

    ema_fast: int = 3
    ema_slow: int = 8
    ema_higher_tf: int = 60
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14

    def __post_init__(self) -> None:
        """Fail fast on a non-positive period or an inverted fast/slow ordering."""
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer, got {value!r}")
        if not self.ema_fast < self.ema_slow:
            raise ValueError(f"ema_fast ({self.ema_fast}) must be below ema_slow ({self.ema_slow})")
        if not self.ema_slow < self.ema_higher_tf:
            raise ValueError(
                f"ema_slow ({self.ema_slow}) must be below ema_higher_tf ({self.ema_higher_tf})"
            )
        if not self.macd_fast < self.macd_slow:
            raise ValueError(
                f"macd_fast ({self.macd_fast}) must be below macd_slow ({self.macd_slow})"
            )


_KEYS = tuple(field.name for field in fields(PriceFeatureConfig))


def parse_price_features_config(section: Mapping[str, Any], *, strategy: str) -> PriceFeatureConfig:
    """The section's periods, defaulting every key it omits (fail fast on anything else).

    Raises:
        ValueError: an unknown key, a non-positive or non-integer period, or an inverted
            fast/slow ordering — each named with the strategy.
    """
    unknown = sorted(set(section) - set(_KEYS))
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} has unknown keys {unknown!r}; known keys: "
            f"{list(_KEYS)}"
        )
    try:
        return PriceFeatureConfig(**{key: section[key] for key in _KEYS if key in section})
    except ValueError as exc:
        raise ValueError(f"strategy {strategy!r}: {_SECTION}.{exc}") from exc


def warmup_bars(config: PriceFeatureConfig) -> int:
    """Bars before every LEAN indicator the features read is ready.

    The higher-timeframe EMA needs its period, MACD needs slow + signal - 1 samples,
    Wilder's RSI needs period + 1 (its first delta needs two closes) and Wilder's ATR
    needs exactly its period (LEAN's first true range is that bar's own high - low, no
    previous close required); the live algorithm skips those bars, so training must too.
    """
    return (
        max(
            config.ema_higher_tf,
            config.macd_slow + config.macd_signal - 1,
            config.rsi_period + 1,
            config.atr_period,
        )
        - 1
    )


def price_features_mapping(config: PriceFeatureConfig) -> dict[str, int]:
    """The effective values as a plain mapping, for the resolved config and provenance."""
    return asdict(config)
