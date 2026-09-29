"""Shared structlog logging configuration for the suite."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import cast

import structlog
from structlog.typing import FilteringBoundLogger

_DEFAULT_LEVEL = "INFO"


def resolve_level(name: str) -> int:
    """Map a level name (case-insensitive) to its standard numeric level.

    Raises ``ValueError`` for an unrecognised name.
    """
    try:
        return logging.getLevelNamesMapping()[name.upper()]
    except KeyError as exc:
        raise ValueError(f"unknown log level: {name!r}") from exc


def configure_logging(level: str = _DEFAULT_LEVEL) -> None:
    """Configure structlog process-wide at ``level`` with a console renderer.

    Logs go to **stderr** (the Unix convention), leaving stdout for a tool's actual output
    (e.g. a CLI summary line) so logs can be streamed live while stdout is still captured/
    parsed by a caller — see scripts/download-prices.sh.
    """
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(resolve_level(level)),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a structlog logger, optionally bound to ``name``."""
    return cast(FilteringBoundLogger, structlog.get_logger(name))


def run_with_logging(app: Callable[[], object], *, logger_name: str = "cli") -> None:
    """Run a tool's CLI app, logging any unhandled error at the boundary then exiting.

    The application boundary (each tool's ``main``) wraps the CLI with this so an
    unexpected failure is logged via structlog (not dumped as a bare traceback)
    and the process exits with code 1. A normal ``SystemExit`` — typer/click exit
    codes, including the fail-fast usage exits — passes through unchanged.
    """
    try:
        app()
    except SystemExit:
        raise
    except BaseException as exc:
        get_logger(logger_name).exception("unhandled_error", error=repr(exc))
        raise SystemExit(1) from exc
