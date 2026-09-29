"""Real LEAN types, smoothing and consolidation; deterministic data-free probe."""
from datetime import UTC, datetime, timedelta

import json
import sys
import trace
from pathlib import Path

from AlgorithmImports import *

_NATIVE_TRACE = trace.Trace(count=True, trace=False)
sys.settrace(_NATIVE_TRACE.globaltrace)
from algo_backtest.perception.lean_indicator import DoubleSmoothedHeikinAshiTrend
from algo_backtest.perception.multi_timeframe import MultiTimeframeHeikinAshi


class main(QCAlgorithm):
    def initialize(self):
        """Run deterministic native assertions with no market-data dependency."""
        self.set_start_date(2014, 5, 7)
        self.set_end_date(2014, 5, 8)
        self.set_cash(100000)
        self._symbol = Symbol.create("EURUSD", SecurityType.FOREX, Market.OANDA)
        self._observed = {}
        self._native_contract()
        self._closed_higher_bars()
        from source_wiring import verify_source_wiring
        self._observed["wiring"] = verify_source_wiring(self._bar(0))
        self._hourly_readiness()
        self._native_tie()
        self._quote_midpoint()
        sys.settrace(None)
        counts = _NATIVE_TRACE.results().counts
        executed = {}
        for (filename, line), count in counts.items():
            if "/algo_backtest/perception/" in filename:
                executed.setdefault(filename, []).append(line)
        Path("/Results/perception-native-lines.json").write_text(json.dumps(executed))
        Path("/Results/perception-native-observations.json").write_text(
            json.dumps(self._observed))
        self.debug("DSHA|DONE")

    def _bar(self, minute, o=10, h=14, low=8, c=12):
        """Build a real completed LEAN minute candle."""
        return TradeBar(datetime(2014, 5, 7) + timedelta(minutes=minute),
                        self._symbol, o, h, low, c, 0, timedelta(minutes=1))

    @staticmethod
    def _read(call):
        """Record a real output or its explicit readiness refusal."""
        try:
            return call()
        except ValueError:
            return "unready"

    def _native_contract(self):
        """Export measurements; host assertions own the expected contract."""
        indicator = DoubleSmoothedHeikinAshiTrend(6, 2)
        events = []
        indicator.updated += lambda sender, point: events.append(
            [point.end_time.isoformat(), float(point.value)])
        updates = [indicator.update(self._bar(minute)) for minute in range(6)]
        self._observed["six"] = {
            "updates": updates, "ready": indicator.is_ready,
            "direction": self._read(lambda: indicator.direction),
            "values": self._read(lambda: indicator.smoothed_values),
        }
        seventh = self._bar(6, 14, 18, 12, 16)
        updated = indicator.update(seventh)
        self._observed["seven"] = {
            "updated": updated, "ready": indicator.is_ready,
            "direction": self._read(lambda: indicator.direction),
            "values": self._read(lambda: indicator.smoothed_values),
            "python_indicator": isinstance(indicator, PythonIndicator),
            "warm_up_period": indicator.warm_up_period,
            "time": indicator.time.isoformat(),
            "current_time": indicator.current.end_time.isoformat(),
            "value": indicator.value, "current_value": float(indicator.current.value),
            "events": events.copy(), "samples": indicator.samples,
        }
        indicator.reset()
        self._observed["reset"] = {
            "ready": indicator.is_ready, "samples": indicator.samples,
            "value": indicator.value, "current_value": float(indicator.current.value),
            "time": indicator.time.isoformat(),
            "direction": self._read(lambda: indicator.direction),
        }
        fresh = DoubleSmoothedHeikinAshiTrend(6, 2)
        replay = []
        for minute in range(7):
            bar = self._bar(minute, 20, 25, 17, 23)
            replay.append([indicator.update(bar), fresh.update(bar)])
        self._observed["replay"] = {
            "updates": replay, "values": self._read(lambda: indicator.smoothed_values),
            "fresh_values": self._read(lambda: fresh.smoothed_values),
            "direction": self._read(lambda: indicator.direction),
            "fresh_direction": self._read(lambda: fresh.direction),
        }

    def _closed_higher_bars(self):
        """Observe both sides of consecutive five-minute bucket boundaries."""
        candidate = MultiTimeframeHeikinAshi(1, 1, 5)
        for minute in range(4):
            candidate.update(self._bar(minute, 10, 14, 8, 12))
        self._observed["mtf_unready"] = {
            "ready": candidate.is_ready, "features": self._read(candidate.features)}
        candidate.update(self._bar(4, 10, 14, 8, 12))
        self._observed["mtf_ready"] = {
            "ready": candidate.is_ready, "features": self._read(candidate.features)}
        unfinished = []
        f1_results = []
        for minute in range(5, 9):
            candidate.update(self._bar(minute, 20, 25, 18, 24))
            unfinished.append(self._read(candidate.features))
            f1_results.append(self._f1(candidate.features()))
        candidate.update(self._bar(9, 20, 25, 18, 24))
        self._observed["mtf_closed"] = {
            "unfinished": unfinished, "closed": self._read(candidate.features)}
        self._observed["f1"] = {"unfinished": f1_results, "closed": self._f1(candidate.features())}

    @staticmethod
    def _f1(directions):
        """Feed measured native directions through the real source-agnostic F1 filter."""
        from algo_backtest.chain.filters.f1_trend import F1TrendFilter
        from algo_backtest.chain.model import ExecutionState

        state = ExecutionState(timestamp=datetime(2014, 5, 7, tzinfo=UTC), pair="EURUSD",
                               features={**directions, "trend_strength": 20.0})
        result = F1TrendFilter().apply(state)
        return {"veto": result.veto, "recommendation": result.recommendation.value,
                "enrichment": result.enrichment}

    def _hourly_readiness(self):
        """Record the readiness boundary at seven fully closed hourly bars."""
        candidate = MultiTimeframeHeikinAshi()
        for minute in range(419):
            candidate.update(self._bar(minute))
        self._observed["hourly_unready"] = {
            "ready": candidate.is_ready, "features": self._read(candidate.features)}
        candidate.update(self._bar(419))
        self._observed["hourly_ready"] = {
            "ready": candidate.is_ready, "features": self._read(candidate.features)}

    def _native_tie(self):
        """Observe the historical tie-down rule through real native smoothing."""
        indicator = DoubleSmoothedHeikinAshiTrend(1, 1)
        updated = indicator.update(self._bar(0, 10, 10, 10, 10))
        self._observed["tie"] = {
            "updated": updated, "values": self._read(lambda: indicator.smoothed_values),
            "direction": self._read(lambda: indicator.direction)}

    def _quote_midpoint(self):
        """Asymmetric quote sides make bid-only and midpoint directions differ."""
        candidate = MultiTimeframeHeikinAshi(1, 1, 5)
        for minute in range(5):
            bar = QuoteBar(
                datetime(2014, 5, 7) + timedelta(minutes=minute),
                self._symbol, Bar(10, 14, 8, 12), 0, Bar(12, 40, 10, 14), 0,
                timedelta(minutes=1),
            )
            candidate.update(bar)
        self._observed["midpoint"] = self._read(candidate.features)
