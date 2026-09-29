# Native fixture (Story 19, T11/T12 minimum-viable slice): the unmodified production
# ChainAlgorithm.initialize() loads its F7 model through the on-demand provider
# (bundle_registry/bundle_id) instead of a single model_path file. bundle_id.txt and
# bundle_registry/ are written into this algo dir's copy by the owning test before LEAN
# runs (see test_retraining_provider_engine.py); nothing here is test-run-specific.
from pathlib import Path

from engine.chain_algorithm import ChainAlgorithm


class main(ChainAlgorithm):  # noqa: N801  (algorithm-type-name = "main")
    """The "baseline" chain, F7 model pinned from a published retraining bundle."""

    strategy_name = "baseline"
    log_tag = "BUNDLEPROVIDER"
    strategy_dir = Path(__file__).parent
    bundle_registry = Path(__file__).parent / "bundle_registry"
    bundle_id = (Path(__file__).parent / "bundle_id.txt").read_text().strip()
