"""algo-backtest configuration: resolve the tool's effective settings, typed.

Thin wrapper over the shared `algo_core.config.resolve` (env > conf/backtest.yaml >
conf/algo.yaml > defaults). It owns the *backtest* schema — `algo-core` is a pure
library and holds no tool schema. The one setting Slice B needs is the per-market
data timezone the lean-data materializer must use; it is config-driven (never
hard-coded) and exposed to the tool as a typed `ZoneInfo`. OANDA forex is UTC by
convention (empirically confirmed against the LEAN engine; see leandata.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from algo_core import layout
from algo_core.config import Impact, ParameterSpec, resolve
from algo_core.layout import ENV_DATA_ROOT

SCHEMA = (
    ParameterSpec(name="markets.oanda.data_tz", impact=Impact.OPERATIONAL, default="UTC"),
    # Trading-impactful (Spec 04a): the brokerage fill/fee/spread model changes realized
    # PnL, so a missing value is a hard stop, never a silent default — see engine/brokerage.
    ParameterSpec(name="broker.adapter", impact=Impact.TRADING),
)
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BacktestConfig:
    """The resolved, typed algo-backtest configuration plus its provenance log."""

    data_root: Path
    oanda_data_tz: ZoneInfo
    broker_adapter: str
    provenance: tuple[str, ...]


def load_backtest_config() -> BacktestConfig:
    """Resolve + validate the algo-backtest config, with the data tz typed as ZoneInfo.

    Raises:
        ConfigError: from the loader (schema mismatch / missing trading param / etc.).
        ValueError: if the configured data timezone is not a valid IANA zone (fail fast).
    """
    result = resolve("backtest", SCHEMA, SCHEMA_VERSION)
    tz_name = str(result.values["markets.oanda.data_tz"])
    try:
        data_tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(
            f"configured markets.oanda.data_tz {tz_name!r} is not a valid IANA timezone; "
            f"set a valid zone (e.g. 'UTC') in conf/backtest.yaml or ALGO_MARKETS__OANDA__DATA_TZ"
        ) from exc
    data_root = layout.data_root()
    source = ENV_DATA_ROOT if os.environ.get(ENV_DATA_ROOT) else "convention"
    provenance = (*result.provenance, f"DATA ROOT: data_root={data_root} (from {source})")
    broker_adapter = str(result.values["broker.adapter"])
    return BacktestConfig(
        data_root=data_root,
        oanda_data_tz=data_tz,
        broker_adapter=broker_adapter,
        provenance=provenance,
    )
