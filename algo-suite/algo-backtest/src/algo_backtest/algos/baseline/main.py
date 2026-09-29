# AlgorithmImports forces this file's LEAN-only import style -- see engine/algorithm.py.
# All per-bar glue is shared in engine/chain_algorithm.py; all LEAN-free logic in the
# type-checked algo_backtest.chain.wiring.
from pathlib import Path

from engine.chain_algorithm import ChainAlgorithm


class main(ChainAlgorithm):  # noqa: N801  (algorithm-type-name = "main")
    """The "baseline" F1+F2+F3+F5+F6+F7 chain (no F4/news).

    SMOKE TEST, not a methodology result (docs/technical-debt.md TD-51): F3's candlestick
    pattern is never populated, F5/F6 use fixed placeholder economics, and F7's quality
    depends on the window scripts/train_baseline_meta_learner.py was run over (see
    f7_meta_learner.json's embedded provenance).
    """

    strategy_name = "baseline"
    log_tag = "BASELINE"
    model_path = Path(__file__).parent / "f7_meta_learner.json"
