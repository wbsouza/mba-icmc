"""Real LEAN types, smoothing and consolidation; deterministic data-free probe."""
from datetime import datetime, timedelta
from math import isclose

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
        self._native_contract()
        self._closed_higher_bars()
        from source_wiring import verify_source_wiring
        verify_source_wiring(self._bar(0))
        self.debug("DSHA|SOURCE_WIRING")
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
        self.debug("DSHA|DONE")

    def _bar(self, minute, o=10, h=14, low=8, c=12):
        """Build a real completed LEAN minute candle."""
        return TradeBar(datetime(2014, 5, 7) + timedelta(minutes=minute),
                        self._symbol, o, h, low, c, 0, timedelta(minutes=1))

    @staticmethod
    def _refuses(call):
        """Require premature output reads to fail explicitly."""
        try:
            call()
        except ValueError:
            return
        raise AssertionError("Unready directional output was exposed")

    def _native_contract(self):
        """Check seven-bar readiness, exact smoothing, events and reset replay."""
        indicator = DoubleSmoothedHeikinAshiTrend(6, 2)
        assert isinstance(indicator, PythonIndicator)
        assert indicator.warm_up_period == 7
        events = []
        indicator.updated += lambda sender, point: events.append((point.end_time, float(point.value)))
        for minute in range(6):
            assert not indicator.update(self._bar(minute))
        assert not indicator.is_ready
        self._refuses(lambda: indicator.direction)
        self._refuses(lambda: indicator.smoothed_values)
        self.debug("DSHA|SIX_UNREADY")
        seventh = self._bar(6, 14, 18, 12, 16)
        assert indicator.update(seventh)
        assert indicator.is_ready and indicator.direction == -1
        self.debug("DSHA|SEVEN_READY")
        assert indicator.time == seventh.end_time == indicator.current.end_time
        assert indicator.value == float(indicator.current.value) == indicator.direction
        assert events[-1] == (seventh.end_time, indicator.direction)
        assert len(events) == indicator.samples == 7
        self.debug("DSHA|CONTRACT")
        # Wilder first ready candle=(10,14,8,12), HA=(11,14,8,11).
        # Next Wilder=(32/3,44/3,26/3,38/3), HA=(11,44/3,26/3,35/3).
        # Reordered (near,far) flips from (14,8) to (26/3,44/3).
        expected = (94 / 9, 112 / 9, 11, 103 / 9)
        assert all(isclose(a, b, abs_tol=1e-10)
                   for a, b in zip(indicator.smoothed_values, expected)), indicator.smoothed_values
        self.debug("DSHA|VALUES")
        indicator.reset()
        assert not indicator.is_ready and indicator.samples == 0
        assert indicator.value == float(indicator.current.value) == 0
        assert indicator.time == datetime.min
        self._refuses(lambda: indicator.direction)
        fresh = DoubleSmoothedHeikinAshiTrend(6, 2)
        for minute in range(7):
            bar = self._bar(minute, 20, 25, 17, 23)
            assert indicator.update(bar) == fresh.update(bar) == (minute == 6)
        assert indicator.smoothed_values == fresh.smoothed_values
        assert indicator.direction == fresh.direction
        self.debug("DSHA|RESET")

    def _closed_higher_bars(self):
        """Require higher direction to change only when its bucket closes."""
        candidate = MultiTimeframeHeikinAshi(1, 1, 5)
        for minute in range(4):
            candidate.update(self._bar(minute, 10, 14, 8, 12))
        assert not candidate.is_ready
        self._refuses(candidate.features)
        self.debug("DSHA|MTF_UNREADY")
        candidate.update(self._bar(4, 10, 14, 8, 12))
        assert candidate.is_ready
        first = candidate.features()
        assert first == {"trend_direction": 1.0, "higher_tf_trend_direction": 1.0}, first
        self.debug("DSHA|MTF_READY")
        for minute in range(5, 9):
            candidate.update(self._bar(minute, 20, 25, 18, 24))
            assert candidate.features()["higher_tf_trend_direction"] == 1
        candidate.update(self._bar(9, 20, 25, 18, 24))
        assert candidate.features()["higher_tf_trend_direction"] == -1
        self.debug("DSHA|MTF_CLOSED_ONLY")

    def _hourly_readiness(self):
        """Require seven fully closed hourly bars under default periods."""
        candidate = MultiTimeframeHeikinAshi()
        for minute in range(419):
            candidate.update(self._bar(minute))
        assert not candidate.is_ready
        self._refuses(candidate.features)
        self.debug("DSHA|HOURLY_UNREADY")
        candidate.update(self._bar(419))
        assert candidate.is_ready
        assert set(candidate.features()) == {"trend_direction", "higher_tf_trend_direction"}
        self.debug("DSHA|HOURLY_READY")

    def _native_tie(self):
        """Verify the historical tie-down rule through real native smoothing."""
        indicator = DoubleSmoothedHeikinAshiTrend(1, 1)
        assert indicator.update(self._bar(0, 10, 10, 10, 10))
        assert indicator.smoothed_values == (10, 10, 10, 10)
        assert indicator.direction == -1
        self.debug("DSHA|NATIVE_TIE")

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
        assert candidate.features() == {
            "trend_direction": -1.0, "higher_tf_trend_direction": -1.0,
        }
        self.debug("DSHA|MIDPOINT")
