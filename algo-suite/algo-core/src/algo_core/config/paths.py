"""Convention over configuration, container-friendly.

The suite runs with **no config files at all**: every setting has a convention
default (``data_root`` = ``algo-suite/data/``, all sub-paths derived from it,
INFO logging, ...). A file under ``conf/`` exists *only* to override a default.

Resolution order (highest wins): environment > ``conf/<tool>.yaml`` >
``conf/algo.yaml`` > convention defaults. Environment always wins so a Docker
container overrides anything without rebuilding an image or editing a mounted
file.

Conventions:
- Override dir is ``conf/`` at the workspace root, relocatable via
  ``ALGO_CONF_DIR`` (a container mounts one dir: ``-v ./conf:/conf:ro`` with
  ``ALGO_CONF_DIR=/conf``). Files are convention-named: ``algo.yaml`` (global),
  ``<tool>.yaml`` (per tool), ``backtest/<strategy>.yaml`` (strategy defs).
- Env prefix ``ALGO_``; nested keys via ``__`` (``ALGO_DATA_ROOT``,
  ``ALGO_LOG_LEVEL``, ``ALGO_DOWNLOAD__SOURCES``).
- ``data_root`` is one path, meant to be a mounted volume in containers
  (``-e ALGO_DATA_ROOT=/data -v /nas/tcc:/data``).

This module fixes the contract and the path conventions only. The layered
resolution that reads ``conf/algo.yaml`` + ``conf/<tool>.yaml`` and applies
environment overrides (env > tool > global > defaults) is deferred until a tool
first needs to load a config file, at which point its dependency (e.g.
pydantic-settings) is added with it (../../SPEC.md).
"""

from __future__ import annotations

import os
from pathlib import Path

from algo_core import layout

ENV_CONF_DIR = "ALGO_CONF_DIR"
GLOBAL_CONFIG_NAME = "algo.yaml"


def conf_dir() -> Path:
    """Override directory: ``ALGO_CONF_DIR`` if set, else ``conf/`` at the root.

    The directory need not exist; absent means pure convention.
    """
    env = os.environ.get(ENV_CONF_DIR)
    if env:
        return Path(env).expanduser()
    return layout.data_root().parent / "conf"


def global_config_path() -> Path:
    """Path to the optional global overrides file (``conf/algo.yaml``)."""
    return conf_dir() / GLOBAL_CONFIG_NAME


def tool_config_path(tool: str) -> Path:
    """Path to a tool's optional overrides file (``conf/<tool>.yaml``).

    ``tool`` is the short name without the ``algo-`` prefix (e.g. ``download``).
    """
    return conf_dir() / f"{tool}.yaml"
