"""BDD for serialized signal choices and frozen-model compatibility."""

import pytest
import yaml
from algo_backtest.chain.price_features import parse_price_features_config
from algo_backtest.signal_contract import require_signal_contract
from algo_backtest.strategies import (
    load_resolved_strategy,
    load_strategy_chain_config,
    resolved_yaml,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/signal_configuration.feature")


@pytest.fixture
def signal_config():
    """Isolate the candidate and parse outcome per scenario."""
    return {}


@given("a baseline extension with TA-Lib and the volume filter enabled")
def candidate(signal_config, tmp_path):
    """Inherit economics without modifying bundled strategies or frozen models."""
    filters = list(load_strategy_chain_config("baseline").filters)
    filters.insert(-1, "volume_strength")
    directory = tmp_path / "candidate"
    directory.mkdir()
    (directory / "config.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "extends": "baseline", "filters": filters,
        "pattern": {"detector": "talib"}, "volume_strength": {"lookback": 20},
    }))
    signal_config["root"] = tmp_path


@when("the signal candidate is loaded")
def loaded(signal_config):
    """Use the production strategy loader."""
    signal_config["config"] = load_strategy_chain_config("candidate", root=signal_config["root"])


@then("the resolved signal contract has TA-Lib and 20-bar activity")
def effective(signal_config):
    """All effective settings, including defaults, are reportable."""
    config = signal_config["config"]
    assert config.pattern.detector == "talib"
    assert config.volume_strength.lookback == 20
    assert config.raw["volume_strength"]["min_relative_activity"] == 1.0


@then("its resolved YAML survives a round trip")
def round_trip(signal_config):
    """The container receives the same typed contract."""
    path = signal_config["root"] / "resolved.yaml"
    path.write_text(resolved_yaml(signal_config["config"]))
    assert load_resolved_strategy(path, name="candidate").raw == signal_config["config"].raw


@when("legacy model signal provenance is checked")
def legacy(signal_config):
    """Absent detector provenance means the historical disabled detector."""
    loaded(signal_config)
    with pytest.raises(ValueError) as exc:
        require_signal_contract({}, signal_config["config"])
    signal_config["error"] = str(exc.value)


@then("the model is rejected with a retraining instruction")
def retrain(signal_config):
    """Make the necessary action unambiguous."""
    assert "retrain" in signal_config["error"]


@when(parsers.parse("a decision timeframe of {minutes:d} minutes is parsed"))
def timeframe(signal_config, minutes):
    """Exercise the shared train/serve timeframe setting."""
    try:
        parse_price_features_config({"bar_minutes": minutes}, strategy="candidate")
        signal_config["outcome"] = "valid"
    except ValueError:
        signal_config["outcome"] = "invalid"


@then(parsers.parse("the timeframe outcome is {outcome}"))
def timeframe_outcome(signal_config, outcome):
    """Assert the declared input channel."""
    assert signal_config["outcome"] == outcome


def _change_candidate(signal_config, **changes):
    """Edit only the disposable scenario candidate."""
    path = signal_config["root"] / "candidate/config.yaml"
    raw = yaml.safe_load(path.read_text())
    raw.update(changes)
    path.write_text(yaml.safe_dump(raw))


@given("the candidate uses H4 candles with a fifteen-minute label horizon")
def subbar(signal_config):
    """Retain the inherited 15-minute label while changing the decision clock."""
    _change_candidate(signal_config, price_features={"bar_minutes": 240})


@given("the candidate uses H4 candles with DSHA perception")
def dsha_clock(signal_config):
    """DSHA currently owns its own minute-to-higher-timeframe aggregation."""
    _change_candidate(signal_config, price_features={"bar_minutes": 240},
                      meta_learner={"label_horizon_minutes": 240},
                      perception_source="double_smoothed_heikin_ashi")


@when("the invalid signal candidate is loaded")
def invalid_candidate(signal_config):
    """Validate before a model is loaded or a container starts."""
    with pytest.raises(ValueError) as exc:
        loaded(signal_config)
    signal_config["error"] = str(exc.value)


@then(parsers.parse('the signal configuration error explains "{fragment}"'))
def configuration_error(signal_config, fragment):
    """Name the incompatible configuration, not an unrelated failure."""
    assert fragment in signal_config["error"]
