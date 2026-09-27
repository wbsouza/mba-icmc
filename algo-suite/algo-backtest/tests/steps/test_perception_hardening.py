"""Boundary assertions strengthened by the perception mutation campaign."""

import json

from algo_backtest.perception.config import parse_perception_config
from algo_backtest.perception.heikin_ashi import validate_period
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/perception_hardening.feature")


@given(parsers.parse("a smoothing period represented by {value}"))
def _period(ctx, value):
    ctx["period"] = json.loads(value)


@when("the smoothing period is validated")
def _validate(ctx):
    try:
        validate_period(ctx["period"], "period1")
        ctx["validation"] = "accepts"
    except ValueError as exc:
        assert "period1" in str(exc)
        ctx["validation"] = "rejects"


@then(parsers.parse("smoothing validation {outcome}"))
def _validation(ctx, outcome):
    assert ctx["validation"] == outcome


@given(parsers.parse("perception settings represented by {settings}"))
def _settings(ctx, settings):
    ctx["settings"] = json.loads(settings)


@when("those candidate settings are parsed")
def _parse(ctx):
    try:
        value = parse_perception_config({"double_smoothed_heikin_ashi": ctx["settings"]})
        ctx["parsed"] = f"{value.period1},{value.period2},{value.higher_tf_minutes}"
    except ValueError as exc:
        assert "double_smoothed_heikin_ashi" in str(exc)
        ctx["parsed"] = "rejects"


@then(parsers.parse("the candidate parse result is {result}"))
def _result(ctx, result):
    assert ctx["parsed"] == result


@given("the native strategy source wiring probe")
def _native_wiring(ctx, native_dsha_probe):
    ctx["wiring_logs"] = native_dsha_probe


@when("EMA and candidate source configurations are exercised")
@then("candidate readiness gates the chain and replaces only both trend directions")
def _wiring(ctx):
    assert "DSHA|SOURCE_WIRING" in ctx["wiring_logs"]


@given("a direct higher timeframe of one minute")
def _one_minute(ctx):
    ctx["higher_minutes"] = 1


@when("the multi-timeframe perception is constructed")
def _construct(ctx):
    from algo_backtest.perception.multi_timeframe import MultiTimeframeHeikinAshi

    try:
        MultiTimeframeHeikinAshi(higher_tf_minutes=ctx["higher_minutes"])
    except ValueError as exc:
        ctx["construction_error"] = str(exc)


@then("construction rejects the timeframe before loading native indicators")
def _construction_error(ctx):
    assert "higher_tf_minutes must be at least 2" in ctx["construction_error"]
