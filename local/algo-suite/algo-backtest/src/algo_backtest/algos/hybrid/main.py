# AlgorithmImports forces this file's LEAN-only import style -- see engine/algorithm.py.
# All per-bar glue is shared in engine/chain_algorithm.py; all LEAN-free logic in the
# type-checked algo_backtest.chain.wiring.
from datetime import date
from pathlib import Path

from algo_backtest.chain.filters.f4_news_context import (
    NewsContextIndex,
    load_news_context_window,
)
from engine.chain_algorithm import ChainAlgorithm


class main(ChainAlgorithm):  # noqa: N801  (algorithm-type-name = "main")
    """The "hybrid" chain: baseline's F1+F2+F3+F5+F6+F7 plus F4/news.

    SMOKE TEST, not a methodology result -- baseline's caveats (docs/technical-debt.md
    TD-51) plus F4's: the GDELT event-intensity veto input is real (one-day publication
    lag, algo-score SPEC.md 6.2; residual SQLDATE caveat TD-59), per-symbol sentiment is
    best-effort/ABSTAIN pending TD-48.
    """

    strategy_name = "hybrid"
    log_tag = "HYBRID"
    model_path = Path(__file__).parent / "f7_meta_learner.json"

    def _news_index(self, symbol: str, start: date, end: date) -> NewsContextIndex:
        """Every run-window month's real GDELT event-feature (+ sentiment) Parquet."""
        root = Path(self._required("news_data_root"))
        return load_news_context_window(root, symbol, start, end)
