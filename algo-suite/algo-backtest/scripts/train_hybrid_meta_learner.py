"""Offline F7 meta-learner training for the news-aware strategy chains -- SMOKE TEST ONLY.

Trains and persists a `TrainedMetaLearner` for `algos/hybrid/main.py` as a portable JSON
document (`chain/filters/f7_model_io.py`) embedding exactly what it was trained on.
The families trained are exactly the strategy's `meta_learner.families`: any non-empty
subset of the known families that includes `news` (`hybrid` declares all four; the
`news-only` strategy declares `[news]` alone), recorded in the model so a run under a
strategy declaring different families is refused (`f7_model_io.require_families`).
A strategy without the news family belongs to `train_baseline_meta_learner.py`.
Rows are built over the bar stream LEAN delivers, with LEAN's indicator seeding and the
live algorithm's feature function (`algo_backtest.training` over `chain.wiring`), and
news is keyed at decision time — train/serve parity of the price features and of
F4's per-bar news lookup (each to 9 decimal places) is proven in real LEAN by
`tests/features/feature_parity.feature`. Rows whose label horizon crosses a split
boundary are purged, so held-out data cannot influence the fitted model.

Adds the NEWS family: `news_event_intensity` is the real GDELT event feature
(one-day publication lag, algo-score SPEC.md 6.2), looked up at each bar's decision
time; `news_sentiment_score` is always missing pending TD-48, the same shape live.

The window runs from `--from` through `--test-end` (inclusive) and may span any number
of months, e.g. 6 in-sample months and the next 6 held out:

    --from 2015-02-02 --train-end 2015-06-30 --validation-end 2015-07-31 --test-end 2016-01-31

`train` fits the per-family models, `validation` calibrates the logistic combiner, and
`test` is never fit on -- backtest only over the test span to stay out of sample.
Any model this script produces must not be cited as a real Chapter-4 result until the
methodology's full walk-forward window is used (docs/technical-debt.md TD-51).
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    train_meta_learner,
    walk_forward_split,
)
from algo_backtest.strategies import load_strategy_chain_config
from algo_backtest.training import (
    build_training_rows,
    event_partitions,
    load_event_intensity,
    load_m1_bars,
    price_partitions,
    save_model,
)
from algo_core import layout
from algo_core.instrument import build_instrument

_DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "src/algo_backtest/algos/hybrid/f7_meta_learner.json"
)


def _families(strategy: str, declared: Sequence[str]) -> tuple[FeatureFamily, ...]:
    """The families to train, in the strategy's declared order; `news` must be among them.

    The loader has already refused an unknown family name, so every entry coerces.

    Raises:
        ValueError: the strategy declares no families, or none of them is `news`.
    """
    if not declared:
        raise ValueError(
            f"hybrid trainer requires at least one feature family, but strategy {strategy!r} "
            "declares no meta_learner.families; add the families to train (news included)"
        )
    if FeatureFamily.NEWS.value not in declared:
        raise ValueError(
            f"hybrid trainer requires the news family, but strategy {strategy!r} declares "
            f"meta_learner.families {list(declared)}; add 'news' to meta_learner.families or "
            "use the baseline trainer for price-only families"
        )
    return tuple(FeatureFamily(name) for name in declared)


def _git_revision() -> str:
    """HEAD's commit SHA, suffixed `-dirty` when tracked files have local changes.

    This is the revision of the *code that trained* the model; the model file itself is
    committed afterwards, so it lands in a later commit than the one it names.
    """
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return f"{sha}-dirty" if dirty else sha


def _parse_args() -> argparse.Namespace:
    """The CLI contract: symbol, inclusive window start, three walk-forward bounds, output."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        required=True,
        help="YYYY-MM-DD, inclusive window start",
    )
    parser.add_argument(
        "--train-end", type=date.fromisoformat, required=True, help="YYYY-MM-DD, inclusive"
    )
    parser.add_argument(
        "--validation-end", type=date.fromisoformat, required=True, help="YYYY-MM-DD, inclusive"
    )
    parser.add_argument(
        "--test-end", type=date.fromisoformat, required=True, help="YYYY-MM-DD, inclusive"
    )
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument("--strategy", default="hybrid")
    parser.add_argument("--strategies-dir", type=Path)
    args = parser.parse_args()
    if (args.strategy != "hybrid" or args.strategies_dir) and args.out == _DEFAULT_OUT:
        parser.error("external signal candidates require --out; preserve the frozen hybrid model")
    if args.start > args.train_end:
        parser.error(f"--from {args.start} is after --train-end {args.train_end}")
    return args


def main() -> None:
    """Read the window's Parquet, build rows, split, train, persist model + manifest."""
    args = _parse_args()
    config = load_strategy_chain_config(args.strategy, root=args.strategies_dir)
    if config.f7 is None:
        raise ValueError(
            f"strategy {args.strategy!r} does not list f7_meta_learner; enable it before training"
        )
    families = _families(args.strategy, config.meta_learner_families)
    if "f4_news_context" not in config.filters:
        raise ValueError(
            f"hybrid trainer requires f4_news_context for strategy {args.strategy!r}; "
            "enable the news filter or use the baseline trainer with price-only families"
        )
    data_root = layout.data_root()
    instrument = build_instrument(args.symbol)
    bars = load_m1_bars(data_root, instrument, args.start, args.test_end)
    event_intensity = load_event_intensity(data_root, args.start, args.test_end)
    rows = build_training_rows(
        bars, event_intensity, instrument=instrument, perception=config.perception,
        price_features_config=config.price_features,
        horizon_minutes=config.f7.label_horizon_minutes,
        pattern_config=config.pattern, volume_config=config.volume_strength,
    )
    split = walk_forward_split(
        rows, train_end=args.train_end, validation_end=args.validation_end, test_end=args.test_end
    )
    model = train_meta_learner(families=families, split=split)
    save_model(
        model,
        args.out,
        {
            "strategy": args.strategy,
            "strategy_config": dict(config.raw),
            "symbol": args.symbol,
            "window": {"from": args.start.isoformat(), "to": args.test_end.isoformat()},
            "split": {
                "train_end": args.train_end.isoformat(),
                "validation_end": args.validation_end.isoformat(),
                "test_end": args.test_end.isoformat(),
            },
            "rows": {
                "total": len(rows),
                "train": len(split.train),
                "validation": len(split.validation),
                "test": len(split.test),
            },
            "families": [family.value for family in families],
            "git_revision": _git_revision(),
        },
        data_root=data_root,
        inputs=[
            *price_partitions(data_root, instrument, args.start, args.test_end),
            *event_partitions(data_root, args.start, args.test_end),
        ],
        horizon_minutes=config.f7.label_horizon_minutes,
    )
    print(
        f"rows={len(rows)} train={len(split.train)} validation={len(split.validation)} "
        f"test={len(split.test)}"
    )
    print(f"model_saved={args.out}")


if __name__ == "__main__":
    main()
