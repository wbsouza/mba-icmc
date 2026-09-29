# Task 2b (investigation) — learn LEAN's exact bar timing/timezone for oanda forex minute.
from AlgorithmImports import *


class Task2bBarCount(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2014, 5, 7)
        self.set_end_date(2014, 5, 8)
        self.set_cash(100_000)
        self._symbol = self.add_forex("EURUSD", Resolution.MINUTE, Market.OANDA, False).symbol
        self._all = 0
        self._day0507 = 0
        self._samples = []
        self._last = None
        self.debug(f"TZ = {self.time_zone}")

    def on_data(self, data: Slice):
        if self._symbol not in data.quote_bars:
            return
        b = data.quote_bars[self._symbol]
        self._all += 1
        if len(self._samples) < 4:
            self._samples.append(f"time={b.time} end={b.end_time}")
        self._last = f"time={b.time} end={b.end_time}"
        et = b.end_time
        if et.year == 2014 and et.month == 5 and et.day == 7:
            self._day0507 += 1

    def on_end_of_algorithm(self):
        self.debug(f"ALL={self._all} end_day0507={self._day0507}")
        for i, s in enumerate(self._samples):
            self.debug(f"sample[{i}] {s}")
        self.debug(f"LAST {self._last}")
