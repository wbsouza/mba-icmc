"""algo-analyze: run metrics and statistical validation.

Reads runs/<run-id>/trades.parquet for metrics and decisions.parquet for
forensics; computes deflated Sharpe, the Monte-Carlo Permutation Test and
ablation tables. See ../../SPEC.md.
"""

__version__ = "0.0.0"
