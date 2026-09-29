"""Validate strategy/model compatibility without coupling pure perception to chain policy."""

from collections.abc import Mapping
from typing import Any

from algo_backtest.strategies import StrategyChainConfig


def require_signal_contract(provenance: Mapping[str, Any], config: StrategyChainConfig) -> None:
    """Compare detectors; pre-Story-09 scalar/null provenance denotes disabled detection.

    This is the existing frozen-model compatibility contract, not permission to serve
    enabled signals without provenance. Volume is a separate gate, not an F7 input.
    """
    trained = provenance.get("strategy_config", {})
    pattern = trained.get("pattern", {}) if isinstance(trained, dict) else {}
    if not isinstance(pattern, dict):
        raise ValueError("model pattern contract must be a mapping; retrain the model")
    actual = config.pattern.detector if config.pattern else "disabled"
    if pattern.get("detector", "disabled") != actual:
        raise ValueError(
            "model pattern detector differs from the strategy; retrain with this config"
        )
