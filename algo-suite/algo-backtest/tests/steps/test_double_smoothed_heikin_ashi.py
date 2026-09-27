"""BDD acceptance for the selectable native LEAN HA perception."""

from algo_backtest.perception.config import parse_perception_config
from algo_backtest.perception.heikin_ashi import (
    OHLC,
    HeikinAshi,
    classify_direction,
    heikin_ashi_transform,
)
from algo_backtest.strategies import load_strategy_chain_config
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/double_smoothed_heikin_ashi.feature")


@given(parsers.parse("smoothed OHLC {o:g}, {h:g}, {low:g}, {c:g} with no previous HA candle"))
def _seed(ctx, o, h, low, c):
    """Smoothed ohlc {o:g}, {h:g}, {low:g}, {c:g} with no previous ha candle."""
    ctx.update(ohlc=OHLC(o, h, low, c), previous=None)


@given(parsers.parse(
    "smoothed OHLC {o:g}, {h:g}, {low:g}, {c:g} after HA open {po:g} and close {pc:g}"
))
def _previous(ctx, o, h, low, c, po, pc):
    """Smoothed ohlc {o:g}, {h:g}, {low:g}, {c:g} after ha open {po:g} and close {pc:g}."""
    ctx.update(ohlc=OHLC(o, h, low, c), previous=HeikinAshi(OHLC(po, po, pc, pc), po, pc))


@when("the Heikin-Ashi transform is applied")
def _transform(ctx):
    """The heikin-ashi transform is applied."""
    ctx["ha"] = heikin_ashi_transform(ctx["ohlc"], ctx["previous"])


@then(parsers.parse("the HA OHLC is {o:g}, {h:g}, {low:g}, {c:g}"))
def _ohlc(ctx, o, h, low, c):
    """The ha ohlc is {o:g}, {h:g}, {low:g}, {c:g}."""
    assert ctx["ha"].ohlc.values() == (o, h, low, c)


@then(parsers.parse("the reordered near and far are {near:g} and {far:g}"))
def _extrema(ctx, near, far):
    """The reordered near and far are {near:g} and {far:g}."""
    assert (ctx["ha"].near, ctx["ha"].far) == (near, far)


@given(parsers.parse("smoothed near {near:g} and smoothed far {far:g}"))
def _levels(ctx, near, far):
    """Smoothed near {near:g} and smoothed far {far:g}."""
    ctx.update(near=near, far=far)


@when("the double-smoothed Heikin-Ashi direction is classified")
def _classify(ctx):
    """The double-smoothed heikin-ashi direction is classified."""
    ctx["direction"] = classify_direction(ctx["near"], ctx["far"])


@then(parsers.parse("the classified direction is {direction:g}"))
def _direction(ctx, direction):
    """The classified direction is {direction:g}."""
    assert ctx["direction"] == direction


@given("an empty perception configuration")
def _empty(ctx):
    """An empty perception configuration."""
    ctx["raw"] = {}


@given(parsers.parse('perception_source "{source}"'))
def _source(ctx, source):
    """Perception_source "{source}"."""
    ctx["raw"] = {"perception_source": source}


@given(parsers.parse('invalid perception configuration "{case}"'))
def _invalid(ctx, case):
    """Invalid perception configuration "{case}"."""
    cases = {
        "unknown source": {"perception_source": "unknown"},
        "zero first period": {"double_smoothed_heikin_ashi": {"period1": 0}},
        "negative second period": {"double_smoothed_heikin_ashi": {"period2": -1}},
        "boolean first period": {"double_smoothed_heikin_ashi": {"period1": True}},
        "fractional second period": {"double_smoothed_heikin_ashi": {"period2": 1.5}},
        "primary-sized higher bar": {"double_smoothed_heikin_ashi": {"higher_tf_minutes": 1}},
        "unknown candidate setting": {"double_smoothed_heikin_ashi": {"period3": 6}},
    }
    ctx["raw"] = cases[case]


@when("the perception configuration is parsed")
def _parse(ctx):
    """The perception configuration is parsed."""
    try:
        ctx["config"] = parse_perception_config(ctx["raw"])
    except ValueError as exc:
        ctx["error"] = exc


@then(parsers.parse('the selected perception source is "{source}"'))
def _selected(ctx, source):
    """The selected perception source is "{source}"."""
    assert ctx["config"].source == source


@then("the smoothing periods are 6 and 2 with higher timeframe 60 minutes")
def _defaults(ctx):
    """The smoothing periods are 6 and 2 with higher timeframe 60 minutes."""
    config = ctx["config"]
    assert (config.period1, config.period2, config.higher_tf_minutes) == (6, 2, 60)


@then(parsers.parse('perception configuration fails naming "{field}"'))
def _error(ctx, field):
    """Perception configuration fails naming "{field}"."""
    assert field in str(ctx["error"])


@given("the packaged baseline and baseline-dsha strategy configurations")
def _packaged(ctx):
    """The packaged baseline and baseline-dsha strategy configurations."""
    ctx["strategy_names"] = ("baseline", "baseline-dsha")


@when("the inherited strategy configurations are resolved")
def _resolve(ctx):
    """The inherited strategy configurations are resolved."""
    ctx["strategies"] = [load_strategy_chain_config(name) for name in ctx["strategy_names"]]


@then("baseline keeps EMA and baseline-dsha selects double-smoothed Heikin-Ashi")
def _ablation_sources(ctx):
    """Baseline keeps ema and baseline-dsha selects double-smoothed heikin-ashi."""
    baseline, candidate = ctx["strategies"]
    assert parse_perception_config(baseline.raw).source == "ema"
    assert parse_perception_config(candidate.raw).source == "double_smoothed_heikin_ashi"


@then("the model artifact and remaining filter configuration are identical")
def _ablation_only(ctx):
    """The model artifact and remaining filter configuration are identical."""
    baseline, candidate = ctx["strategies"]
    ignored = {"extends", "perception_source", "double_smoothed_heikin_ashi"}
    assert {k: v for k, v in baseline.raw.items() if k not in ignored} == {
        k: v for k, v in candidate.raw.items() if k not in ignored
    }
    assert baseline.filters == candidate.filters


@given("a native double-smoothed Heikin-Ashi indicator with periods 6 and 2")
@given("native primary and higher-timeframe Heikin-Ashi perception")
def _native(ctx, native_dsha_probe):
    """A native double-smoothed heikin-ashi indicator with periods 6 and 2."""
    ctx["native_logs"] = native_dsha_probe


@when("six completed primary bars have been supplied")
@then("the indicator reports not ready and refuses to expose direction")
def _not_ready(ctx):
    """Six completed primary bars have been supplied."""
    assert "DSHA|SIX_UNREADY" in ctx["native_logs"]


@when("the seventh completed primary bar is supplied")
@then("the indicator is ready with a classified direction")
def _ready(ctx):
    """The seventh completed primary bar is supplied."""
    assert "DSHA|SEVEN_READY" in ctx["native_logs"]


@when("the primary indicator is ready but the higher indicator is not")
@then("no multi-timeframe directional features are exposed")
def _mtf_unready(ctx):
    """The primary indicator is ready but the higher indicator is not."""
    assert "DSHA|MTF_UNREADY" in ctx["native_logs"]


@when("enough higher-timeframe bars close to make both indicators ready")
@then("both F1 directional features are exposed")
def _mtf_ready(ctx):
    """Enough higher-timeframe bars close to make both indicators ready."""
    assert "DSHA|MTF_READY" in ctx["native_logs"]


@then("an unfinished higher-timeframe bar does not change higher-timeframe direction")
def _mtf_closed(ctx):
    """An unfinished higher-timeframe bar does not change higher-timeframe direction."""
    assert "DSHA|MTF_CLOSED_ONLY" in ctx["native_logs"]


@when("the native indicator receives completed TradeBars")
@then("its current value and timestamp match the published update event")
@then("its warm-up period is seven bars")
def _contract(ctx):
    """The native indicator receives completed tradebars."""
    assert "DSHA|CONTRACT" in ctx["native_logs"]


@then("native Wilder and LWMA produce the expected smoothed values")
def _native_values(ctx):
    """Native wilder and lwma produce the expected smoothed values."""
    assert "DSHA|VALUES" in ctx["native_logs"]


@when("a ready native indicator is reset")
@then("it becomes unready and a replay matches a fresh indicator")
def _reset(ctx):
    """A ready native indicator is reset."""
    assert "DSHA|RESET" in ctx["native_logs"]


@when("default perception receives 419 completed minute bars")
@then("the default hourly direction remains unavailable")
def _hourly_unready(ctx):
    """Default perception receives 419 completed minute bars."""
    assert "DSHA|HOURLY_UNREADY" in ctx["native_logs"]


@when("the 420th minute closes the seventh hourly bar")
@then("the default hourly direction becomes available")
def _hourly_ready(ctx):
    """The 420th minute closes the seventh hourly bar."""
    assert "DSHA|HOURLY_READY" in ctx["native_logs"]


@when("a native indicator receives a fully flat candle after warm-up")
@then("the native direction is down on equal smoothed extrema")
def _native_tie(ctx):
    """A native indicator receives a fully flat candle after warm-up."""
    assert "DSHA|NATIVE_TIE" in ctx["native_logs"]


@when("completed quote bars have asymmetric bid and ask candles")
@then("both directions follow the midpoint candle")
def _midpoint(ctx):
    """Completed quote bars have asymmetric bid and ask candles."""
    assert "DSHA|MIDPOINT" in ctx["native_logs"]
