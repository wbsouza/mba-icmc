"""Atomic file writes — write a temp file then ``os.replace`` onto the target.

A crash mid-write never leaves a corrupt or half-written file: readers see either the old
content or the complete new content, never a partial one. Used for every durable artifact
(cache entries, run/experiment manifests, the Chapter-4 summary CSV) so thesis-facing
outputs are safe to read at any time. Atomicity holds when the temp file and the target are
on the same filesystem (the temp is created in the target's directory).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (UTF-8), creating parent dirs as needed.

    `encoding` is pinned to UTF-8 (not the locale default) so the bytes written are
    reproducible across environments — important for byte-stable artifacts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
