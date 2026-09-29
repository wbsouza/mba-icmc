"""Relative quote activity using the current tick count and strictly previous counts."""

from collections import deque


class RelativeTickActivity:
    """Current count / arithmetic mean of the previous N closed candles, including zeros."""

    def __init__(self, lookback: int) -> None:
        """Require a positive integer history length; no volume is invented during warm-up."""
        if type(lookback) is not int or lookback < 1:
            raise ValueError("volume lookback must be a positive integer; fix volume config")
        self._counts: deque[int] = deque(maxlen=lookback)

    def update(self, count: int) -> float | None:
        """Return unavailable until warm, or when historical activity is zero."""
        if type(count) is not int or count < 0:
            raise ValueError("tick_count must be a nonnegative integer; repair the quote source")
        total = sum(self._counts)
        strength = None
        if len(self._counts) == self._counts.maxlen and total > 0:
            strength = count * len(self._counts) / total
        self._counts.append(count)
        return strength
