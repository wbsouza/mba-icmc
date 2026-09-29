"""F3 — candlestick pattern filter (specs.md §11.3.2, Spec 04c; Story 22, T6 modes).

Recommends BUY/SELL on a detected pattern; ABSTAIN if none on the current closed bar.
With `pattern.detector: talib`, the shared perception layer supplies causal TA-Lib
labels in training and LEAN. The default remains disabled for historical models;
changing the detector requires retraining F7, not silently reusing old provenance.

**Policy modes** (the `pattern.mode` key; default `legacy`, byte-identical to the
pre-Story-22 filter):

- ``legacy``: unchanged. Reads ``state.features["candlestick_pattern"]`` only, per
  the closed vocabulary below; never reads ``candle_evidence``; never vetoes.
- ``advisory``: reads ``state.features["candle_evidence"]`` (a
  ``perception.candle_contract.CandleEvidence``); recommends BUY/SELL when exactly
  one candidate direction is eligible, else ABSTAIN; never vetoes (CND-11).
- ``required_entry``: the same eligibility as advisory, but an ineligible bar
  ABSTAINs with ``veto=True`` and a reason whose first word is one of the distinct
  codes ``warmup``, ``neutral_only``, ``conflicting`` or ``context`` (CND-12).

A candidate direction is the polarity of every READY, non-neutral catalog hit, plus
the confirmed direction of a sequence CONFIRMED at this bar. Direction +1 is
eligible when the context is READY, the T-line position is ABOVE and the
stochastic zone is neither OVERBOUGHT nor UNDEFINED; -1 mirrors BELOW/OVERSOLD.
Exactly one satisfied candidate direction is required; zero is ``neutral_only``,
more than one is ``conflicting``, warming-up evidence or context is ``warmup``, and
a single unsatisfied candidate is ``context``. In advisory or required_entry mode a
missing or non-``CandleEvidence`` value at ``candle_evidence`` is a data-contract
violation and raises, naming the key and the mode.

**Feature-key contract** (read from `state.features`):

- ``candlestick_pattern`` (str | None, legacy mode only): `None`/absent means no
  pattern was detected this bar. A present value must be one of the recognized
  pattern names below — canonical labels mapped from TA-Lib's signed `CDL*` outputs,
  for this filter's closed vocabulary. An unrecognized name is a data-contract
  violation (upstream produced something this filter's key catalogue doesn't cover)
  and raises, per the workspace's fail-fast policy.
- ``candle_evidence`` (``CandleEvidence``, advisory/required_entry only): the shared
  Story 22 producer's per-bar evidence (populated by the integration lane).

ABSTAIN means "no opinion this bar" — legacy and advisory modes never veto.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.perception.candle_contract import POLICY_MODES as _MODES
from algo_backtest.perception.candle_contract import READY as _READY
from algo_backtest.perception.candle_contract import WARMUP as _WARMUP
from algo_backtest.perception.candle_contract import CandleEvidence, PatternHit

_SECTION = "pattern"
_BULLISH_DEFAULT = frozenset({"bullish_engulfing", "hammer", "morning_star"})
_BEARISH_DEFAULT = frozenset({"bearish_engulfing", "shooting_star", "evening_star"})
_EVIDENCE_KEY = "candle_evidence"
_BULLISH_CONFIRMATION_ID = "doji_engulfing_bullish"
_BEARISH_CONFIRMATION_ID = "doji_engulfing_bearish"


@dataclass(frozen=True)
class PatternConfig:
    """F3's vocabulary (the `pattern` section; 2026-09-27 amendment, story 09) plus its
    policy mode (2026-09-28 amendment, story 22): which detected pattern names count
    as bullish and which as bearish, and how the evidence drives a decision."""

    bullish_patterns: frozenset[str] = _BULLISH_DEFAULT
    bearish_patterns: frozenset[str] = _BEARISH_DEFAULT
    detector: str = "disabled"
    mode: str = "legacy"
    enabled_rules: frozenset[str] | None = None
    """``expanded`` detector only: restricts the shared catalog/context/sequence
    producer to this subset of ``perception.candle_contract.ADMITTED_RULES``
    (isolation sweeps -- one pattern's own backtest). ``None`` (default) keeps the
    full admitted catalog live, unchanged from before this field existed."""

    @property
    def known_patterns(self) -> frozenset[str]:
        """Every pattern name the filter accepts."""
        return self.bullish_patterns | self.bearish_patterns


_KEYS = ("bullish_patterns", "bearish_patterns", "detector", "mode", "enabled_rules")


def _names(
    section: Mapping[str, Any], key: str, default: frozenset[str], strategy: str
) -> frozenset[str]:
    """One non-empty list of pattern-name strings, or the default when the key is absent."""
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, str) or not isinstance(value, list) or not value:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.{key} must be a non-empty list of pattern "
            f"names, got {value!r}"
        )
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"strategy {strategy!r}: {_SECTION}.{key} must contain only strings")
    return frozenset(value)


def _mode(section: Mapping[str, Any], strategy: str) -> str:
    """`pattern.mode`, defaulting to legacy; one of the three registered policy modes."""
    value = section.get("mode", "legacy")
    if not isinstance(value, str) or value not in _MODES:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.mode must be one of {', '.join(_MODES)}"
        )
    return value


def parse_pattern_config(section: Mapping[str, Any], *, strategy: str) -> PatternConfig:
    """F3's vocabulary and policy mode from the `pattern` section.

    Raises:
        ValueError: an unknown key, a list that is empty or not a list of strings, a
            name present in both lists, or an unrecognized `mode`.
    """
    unknown = sorted(set(section) - set(_KEYS))
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} has unknown keys {unknown!r}; known keys: "
            f"{list(_KEYS)}"
        )
    bullish = _names(section, "bullish_patterns", _BULLISH_DEFAULT, strategy)
    bearish = _names(section, "bearish_patterns", _BEARISH_DEFAULT, strategy)
    both = sorted(bullish & bearish)
    if both:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} lists {both!r} as both bullish and bearish"
        )
    detector = section.get("detector", "disabled")
    _validate_detector(detector, bullish, bearish)
    mode = _mode(section, strategy)
    enabled_rules = None
    if "enabled_rules" in section:
        if detector != "expanded":
            raise ValueError(
                f"strategy {strategy!r}: {_SECTION}.enabled_rules requires "
                f"{_SECTION}.detector: expanded"
            )
        enabled_rules = _names(section, "enabled_rules", frozenset(), strategy)
    return PatternConfig(
        bullish_patterns=bullish, bearish_patterns=bearish, detector=detector, mode=mode,
        enabled_rules=enabled_rules,
    )


def _validate_detector(detector: str, bullish: frozenset[str], bearish: frozenset[str]) -> None:
    """Enabled TA-Lib uses the closed six-pattern vocabulary shared with F7.

    ``expanded`` (Story 22/23) drives the shared candle_catalog/context/sequence
    producer instead — advisory/required_entry read its ``candle_evidence``, not
    ``bullish_patterns``/``bearish_patterns``, so no vocabulary restriction applies.
    """
    if detector not in ("disabled", "talib", "expanded"):
        raise ValueError(
            "pattern.detector must be disabled, talib or expanded; fix the strategy config"
        )
    if detector == "talib" and (bullish != _BULLISH_DEFAULT or bearish != _BEARISH_DEFAULT):
        raise ValueError(
            "TA-Lib requires the default six-pattern vocabulary; restore pattern names"
        )


def pattern_mapping(config: PatternConfig) -> dict[str, Any]:
    """The effective vocabulary and mode as sorted lists, for the resolved config."""
    mapping: dict[str, Any] = {
        "bullish_patterns": sorted(config.bullish_patterns),
        "bearish_patterns": sorted(config.bearish_patterns),
        "detector": config.detector,
        "mode": config.mode,
    }
    if config.enabled_rules:
        mapping["enabled_rules"] = sorted(config.enabled_rules)
    return mapping


def _candle_evidence(state: ExecutionState, mode: str) -> CandleEvidence:
    """The validated `candle_evidence` feature, or raise naming the key and the mode."""
    value = state.features.get(_EVIDENCE_KEY)
    if not isinstance(value, CandleEvidence):
        raise ValueError(
            f"F3PatternFilter mode {mode!r} requires state.features[{_EVIDENCE_KEY!r}] to be a "
            f"CandleEvidence, got {value!r}; populate the shared Story 22 evidence producer"
        )
    return value


def _candidate_ids(hits: tuple[PatternHit, ...]) -> dict[int, list[str]]:
    """Every READY, non-neutral hit's id, grouped by its polarity."""
    candidates: dict[int, list[str]] = {}
    for hit in hits:
        if hit.status == _READY and hit.polarity != 0:
            candidates.setdefault(hit.polarity, []).append(hit.id)
    return candidates


def _candidates(evidence: CandleEvidence) -> dict[int, list[str]]:
    """Every candidate direction (geometry hits plus a confirmed sequence) and its ids."""
    candidates = _candidate_ids(evidence.hits)
    confirmation = evidence.confirmation
    if confirmation is not None and confirmation.state == "CONFIRMED":
        direction = confirmation.confirmed_direction
        assert direction in (1, -1)
        pseudo_id = _BULLISH_CONFIRMATION_ID if direction == 1 else _BEARISH_CONFIRMATION_ID
        candidates.setdefault(direction, []).append(pseudo_id)
    return candidates


def _context_warming(evidence: CandleEvidence) -> bool:
    """No context, or a context still gathering readiness."""
    context = evidence.context
    return context is None or context.status == _WARMUP


def _satisfied(direction: int, evidence: CandleEvidence) -> bool:
    """Whether the context supports ``direction`` (CND-11/12 eligibility rule)."""
    context = evidence.context
    assert context is not None
    zone = context.stochastic.zone
    if direction == 1:
        return context.t_line_position == "ABOVE" and zone not in ("OVERBOUGHT", "UNDEFINED")
    return context.t_line_position == "BELOW" and zone not in ("OVERSOLD", "UNDEFINED")


def _evaluate(evidence: CandleEvidence) -> tuple[Recommendation, int | None, str, list[str]]:
    """(recommendation, direction, reason code, contributing hit ids) for one bar's evidence."""
    candidates = _candidates(evidence)
    ids = sorted(hit_id for group in candidates.values() for hit_id in group)
    if evidence.status == _WARMUP or _context_warming(evidence):
        return Recommendation.ABSTAIN, None, "warmup", ids
    if not candidates:
        return Recommendation.ABSTAIN, None, "neutral_only", ids
    if len(candidates) > 1:
        return Recommendation.ABSTAIN, None, "conflicting", ids
    ((direction, _),) = candidates.items()
    if not _satisfied(direction, evidence):
        return Recommendation.ABSTAIN, None, "context", ids
    recommendation = Recommendation.BUY if direction == 1 else Recommendation.SELL
    return recommendation, direction, "eligible", ids


@dataclass
class F3PatternFilter:
    """The chain's candlestick-pattern gate: implements `Filter.apply()`."""

    config: PatternConfig

    def apply(self, state: ExecutionState) -> FilterResult:
        """Dispatch to the legacy detector or the evidence-driven policy, by `config.mode`."""
        if self.config.mode == "legacy":
            return self._apply_legacy(state)
        return self._apply_evidence(state)

    def _apply_legacy(self, state: ExecutionState) -> FilterResult:
        """ABSTAIN with no pattern this bar; otherwise recommend by pattern polarity."""
        pattern = state.features.get("candlestick_pattern")
        if pattern is None:
            return FilterResult(
                filter_name="F3_pattern",
                recommendation=Recommendation.ABSTAIN,
                reason="no pattern detected this bar",
            )
        known = self.config.known_patterns
        if pattern not in known:
            raise ValueError(
                f"F3PatternFilter does not recognize candlestick_pattern={pattern!r}; "
                f"known patterns are {sorted(known)!r} — extend the strategy's `pattern` "
                "section if the upstream detector added a new pattern name."
            )
        bullish = pattern in self.config.bullish_patterns
        recommendation = Recommendation.BUY if bullish else Recommendation.SELL
        return FilterResult(
            filter_name="F3_pattern",
            recommendation=recommendation,
            reason=f"detected candlestick pattern {pattern!r}",
        )

    def _apply_evidence(self, state: ExecutionState) -> FilterResult:
        """Advisory/required_entry: BUY/SELL when eligible, else ABSTAIN (veto per mode)."""
        mode = self.config.mode
        evidence = _candle_evidence(state, mode)
        recommendation, direction, code, ids = _evaluate(evidence)
        ids_text = ", ".join(ids) if ids else "none"
        if recommendation == Recommendation.ABSTAIN:
            reason = f"{code}: hits {ids_text} in {mode} mode"
            veto = mode == "required_entry"
            veto_reason: str | None = code
        else:
            word = "long" if direction == 1 else "short"
            reason = f"eligible {word} from hits {ids_text} in {mode} mode"
            veto = False
            veto_reason = None
        return FilterResult(
            filter_name="F3_pattern",
            recommendation=recommendation,
            reason=reason,
            veto=veto,
            enrichment={
                "candle_hits": ",".join(ids),
                "candle_mode": mode,
                "candle_veto_reason": veto_reason,
            },
        )
