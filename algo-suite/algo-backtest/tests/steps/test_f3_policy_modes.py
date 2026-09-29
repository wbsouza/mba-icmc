"""Steps for f3_policy_modes.feature — F3's explicit legacy/advisory/required_entry modes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
import yaml
from algo_backtest.chain.filters.f3_pattern import (
    F3PatternFilter,
    PatternConfig,
    parse_pattern_config,
    pattern_mapping,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.perception.candle_contract import (
    READY,
    WARMUP,
    CandleEvidence,
    ContextEvidence,
    IndicatorValue,
    PatternHit,
    SequenceEvidence,
    StochasticEvidence,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f3_policy_modes.feature")

_T0 = datetime(2024, 1, 1, tzinfo=UTC)
_TREND_FOR_POSITION = {"ABOVE": "UP", "BELOW": "DOWN", "ON": "FLAT", WARMUP: WARMUP}


@dataclass
class _F3ModeCtx:
    """Per-scenario fixture context: staged features/section, the result(s) or error seen."""

    features: dict[str, object] = field(default_factory=dict)
    section: dict[str, object] = field(default_factory=dict)
    config: PatternConfig | None = None
    result: FilterResult | None = None
    error: Exception | None = None
    pairs: list[tuple[FilterResult, FilterResult]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@pytest.fixture
def f3m_ctx() -> _F3ModeCtx:
    """A fresh per-scenario F3-modes context."""
    return _F3ModeCtx()


# --- staging --------------------------------------------------------------------------


@given(parsers.parse("a pattern section {section}"))
def pattern_section(f3m_ctx: _F3ModeCtx, section: str) -> None:
    """The raw YAML `pattern:` mapping, straight from the table (flow style)."""
    f3m_ctx.section = yaml.safe_load(section)


@given(parsers.parse('a detected candlestick pattern "{pattern}"'))
def detected_pattern(f3m_ctx: _F3ModeCtx, pattern: str) -> None:
    """Stage a state with the named legacy `candlestick_pattern` value."""
    f3m_ctx.features["candlestick_pattern"] = pattern


@given("no candlestick pattern is present")
def no_pattern(f3m_ctx: _F3ModeCtx) -> None:
    """Ensure `candlestick_pattern` is absent."""
    f3m_ctx.features.pop("candlestick_pattern", None)


@given("no candle evidence is present")
def no_candle_evidence(f3m_ctx: _F3ModeCtx) -> None:
    """Ensure `candle_evidence` is absent."""
    f3m_ctx.features.pop("candle_evidence", None)


@given(parsers.parse('the candle evidence feature is the string "{value}"'))
def malformed_evidence(f3m_ctx: _F3ModeCtx, value: str) -> None:
    """Stage a non-`CandleEvidence` value at the evidence key (a data-contract violation)."""
    f3m_ctx.features["candle_evidence"] = value


def _parse_hits(raw: str) -> tuple[PatternHit, ...]:
    """The compact `id:polarity:status` table notation, sorted into stable id order."""
    if not raw:
        return ()
    hits = []
    for chunk in raw.split(","):
        rule_id, polarity, status = chunk.split(":")
        hits.append(PatternHit(rule_id, int(polarity), "1", status))
    return tuple(sorted(hits, key=lambda hit: hit.id))


def _parse_context(raw: str) -> ContextEvidence:
    """The compact `status/t_line_position/stochastic_zone` table notation."""
    status, position, zone = raw.split("/")
    indicator = IndicatorValue(1.0, READY) if status == READY else IndicatorValue(None, WARMUP)
    return ContextEvidence(
        close_time=_T0,
        history_count=20,
        ema=indicator,
        t_line_position=position,
        stochastic=StochasticEvidence(indicator, indicator, indicator, zone),
        levels=(),
        trend=_TREND_FOR_POSITION[position],
        status=status,
    )


def _parse_confirmation(raw: str) -> SequenceEvidence | None:
    """`"none"` or a confirmed direction, as a CONFIRMED sequence at this bar."""
    if raw == "none":
        return None
    direction = int(raw)
    return SequenceEvidence("CONFIRMED", _T0, direction, _T0, "confirmed")


@given(
    parsers.re(
        r'^candle evidence with status "(?P<status>[^"]*)", hits "(?P<hits>[^"]*)", '
        r'context "(?P<context>[^"]*)" and confirmation "(?P<confirmation>[^"]*)"$'
    )
)
def stage_evidence(
    f3m_ctx: _F3ModeCtx, status: str, hits: str, context: str, confirmation: str
) -> None:
    """Stage a `CandleEvidence` built from the feature's compact table notations."""
    f3m_ctx.features["candle_evidence"] = CandleEvidence(
        pair="EURUSD",
        timeframe_minutes=60,
        close_time=_T0,
        history_count=20,
        status=status,
        hits=_parse_hits(hits),
        context=_parse_context(context),
        confirmation=_parse_confirmation(confirmation),
    )


# --- actions --------------------------------------------------------------------------


@when(parsers.parse('the pattern config is parsed for strategy "{strategy}"'))
def parse_config(f3m_ctx: _F3ModeCtx, strategy: str) -> None:
    """Parse and stage the `PatternConfig`."""
    f3m_ctx.config = parse_pattern_config(f3m_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the pattern config for strategy "{strategy}" fails'))
def parse_config_fails(f3m_ctx: _F3ModeCtx, strategy: str) -> None:
    """Parse, capturing the expected `ValueError`."""
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_pattern_config(f3m_ctx.section, strategy=strategy)
    f3m_ctx.error = exc_info.value


@when("F3 is applied with that pattern config")
def apply_with_config(f3m_ctx: _F3ModeCtx) -> None:
    """Parse the staged section, then apply F3 to the staged features."""
    config = parse_pattern_config(f3m_ctx.section, strategy="scenario")
    state = ExecutionState(timestamp=_T0, pair="EURUSD", features=dict(f3m_ctx.features))
    f3m_ctx.result = F3PatternFilter(config=config).apply(state)


@when("F3 is applied with that pattern config and the error is captured")
def apply_with_config_capturing_error(f3m_ctx: _F3ModeCtx) -> None:
    """Apply F3, keeping any `ValueError` instead of letting it propagate."""
    config = parse_pattern_config(f3m_ctx.section, strategy="scenario")
    state = ExecutionState(timestamp=_T0, pair="EURUSD", features=dict(f3m_ctx.features))
    try:
        f3m_ctx.result = F3PatternFilter(config=config).apply(state)
        f3m_ctx.error = None
    except ValueError as error:
        f3m_ctx.error = error


@when(parsers.parse('F3 is applied to each of "{patterns}" and to no pattern'))
def apply_to_each(f3m_ctx: _F3ModeCtx, patterns: str) -> None:
    """Every legacy name plus the no-pattern case, against both the parsed and default config."""
    config = parse_pattern_config(f3m_ctx.section, strategy="scenario")
    names: list[str | None] = [name.strip() for name in patterns.split(",")]
    names.append(None)
    pairs = []
    for name in names:
        features: dict[str, object] = {} if name is None else {"candlestick_pattern": name}
        parsed = F3PatternFilter(config=config).apply(
            ExecutionState(timestamp=_T0, pair="EURUSD", features=dict(features))
        )
        default = F3PatternFilter(config=PatternConfig()).apply(
            ExecutionState(timestamp=_T0, pair="EURUSD", features=dict(features))
        )
        pairs.append((parsed, default))
    f3m_ctx.pairs = pairs


_VETO_FIXTURES = {
    "warmup": ("WARMUP", "doji:0:READY,hammer:0:WARMUP", "READY/ABOVE/NEUTRAL", "none"),
    "neutral_only": ("READY", "", "READY/ABOVE/NEUTRAL", "none"),
    "conflicting": ("READY", "hammer:1:READY,hanging_man:-1:READY", "READY/ABOVE/NEUTRAL", "none"),
    "context": ("READY", "bullish_engulfing:1:READY", "READY/BELOW/NEUTRAL", "none"),
}


@when("F3 is applied to the four veto fixtures warmup, neutral_only, conflicting and context")
def apply_veto_fixtures(f3m_ctx: _F3ModeCtx) -> None:
    """One required_entry evidence fixture per veto-reason code, in that fixed order."""
    config = parse_pattern_config(f3m_ctx.section, strategy="scenario")
    reasons = []
    for status, hits, context, confirmation in _VETO_FIXTURES.values():
        evidence = CandleEvidence(
            pair="EURUSD",
            timeframe_minutes=60,
            close_time=_T0,
            history_count=20,
            status=status,
            hits=_parse_hits(hits),
            context=_parse_context(context),
            confirmation=_parse_confirmation(confirmation),
        )
        state = ExecutionState(
            timestamp=_T0, pair="EURUSD", features={"candle_evidence": evidence}
        )
        reasons.append(F3PatternFilter(config=config).apply(state).reason)
    f3m_ctx.reasons = reasons


# --- assertions -----------------------------------------------------------------------


@then(parsers.parse('the parsed pattern mode is "{mode}"'))
def assert_mode(f3m_ctx: _F3ModeCtx, mode: str) -> None:
    """The parsed `PatternConfig.mode`."""
    assert f3m_ctx.config is not None
    assert f3m_ctx.config.mode == mode


@then(parsers.parse('the parsed bullish patterns are "{names}"'))
def assert_bullish(f3m_ctx: _F3ModeCtx, names: str) -> None:
    """The parsed bullish vocabulary."""
    assert f3m_ctx.config is not None
    assert f3m_ctx.config.bullish_patterns == frozenset(n.strip() for n in names.split(","))


@then(parsers.parse('the pattern config failure names "{fragment}"'))
def assert_failure(f3m_ctx: _F3ModeCtx, fragment: str) -> None:
    """The `ValueError` names the offending field and vocabulary."""
    assert f3m_ctx.error is not None
    assert fragment in str(f3m_ctx.error)


@then(parsers.parse("the pattern mapping is {mapping}"))
def assert_mapping(f3m_ctx: _F3ModeCtx, mapping: str) -> None:
    """The resolved mapping, including the mode entry after `detector`."""
    assert f3m_ctx.config is not None
    assert pattern_mapping(f3m_ctx.config) == json.loads(mapping)


@then(parsers.parse('F3 recommends "{recommendation}" with reason mentioning "{fragment}"'))
def assert_recommends(f3m_ctx: _F3ModeCtx, recommendation: str, fragment: str) -> None:
    """The result carries the given recommendation and names the fragment."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.recommendation == Recommendation(recommendation)
    assert fragment in f3m_ctx.result.reason


@then(parsers.parse('F3 abstains with reason mentioning "{fragment}"'))
def assert_abstains(f3m_ctx: _F3ModeCtx, fragment: str) -> None:
    """The result abstains and names the fragment."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.recommendation == Recommendation.ABSTAIN
    assert fragment in f3m_ctx.result.reason


@then("F3 does not veto")
def assert_no_veto(f3m_ctx: _F3ModeCtx) -> None:
    """No veto, even on ABSTAIN (legacy and advisory)."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.veto is False


@then(parsers.parse("F3's veto is {veto}"))
def assert_veto(f3m_ctx: _F3ModeCtx, veto: str) -> None:
    """The exact veto flag."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.veto == (veto == "true")


@then(parsers.parse('F3\'s filter_name is "{name}"'))
def assert_filter_name(f3m_ctx: _F3ModeCtx, name: str) -> None:
    """`filter_name` stays `F3_pattern` in every mode."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.filter_name == name


@then(parsers.parse('F3 raises an error naming "{name}"'))
def assert_raises_naming(f3m_ctx: _F3ModeCtx, name: str) -> None:
    """The captured `ValueError` names the fragment."""
    assert isinstance(f3m_ctx.error, ValueError)
    assert name in str(f3m_ctx.error)


@then(parsers.parse('that error names "{name}"'))
def assert_error_also_names(f3m_ctx: _F3ModeCtx, name: str) -> None:
    """The same captured error also names a second fragment (the mode)."""
    assert isinstance(f3m_ctx.error, ValueError)
    assert name in str(f3m_ctx.error)


@then(
    "every FilterResult equals the result of F3PatternFilter(PatternConfig()) on the same "
    "features"
)
def assert_matches_default(f3m_ctx: _F3ModeCtx) -> None:
    """Legacy mode is byte-identical to the pre-mode filter, name for name."""
    assert f3m_ctx.pairs
    for parsed, default in f3m_ctx.pairs:
        assert parsed == default


@then(
    parsers.parse(
        'the four reasons start with four different codes "{a}", "{b}", "{c}" and "{d}"'
    )
)
def assert_four_codes(f3m_ctx: _F3ModeCtx, a: str, b: str, c: str, d: str) -> None:
    """Each fixture's reason starts with its own distinct veto-reason code."""
    assert len(f3m_ctx.reasons) == 4
    for reason, code in zip(f3m_ctx.reasons, (a, b, c, d), strict=True):
        assert reason.startswith(code)


@then(
    parsers.parse(
        'F3\'s enrichment records candle_hits "{hits}", candle_mode "{mode}" and '
        'candle_veto_reason "{reason}"'
    )
)
def assert_enrichment(f3m_ctx: _F3ModeCtx, hits: str, mode: str, reason: str) -> None:
    """The structured enrichment fields beside the free-text reason."""
    assert f3m_ctx.result is not None
    assert f3m_ctx.result.enrichment == {
        "candle_hits": hits,
        "candle_mode": mode,
        "candle_veto_reason": reason,
    }
