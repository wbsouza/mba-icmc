"""algo-backtest: LEAN-driven backtesting.

Materializes canonical Parquet into the durable lean-data execution store
(read-through), runs the LightGBM sub-models + logistic meta-learner and the
deterministic filter chain on LEAN. See ../../SPEC.md.
"""

__version__ = "0.0.0"
