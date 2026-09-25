#!/usr/bin/env python3
"""Find/remove invisible and format-control Unicode characters from .tex source.

These characters (zero-width spaces, bidi overrides, variation selectors, the
Unicode Tags block, stray BOMs, private-use codepoints) have no legitimate
place in LaTeX prose: a human author never intentionally types them, they can
silently break compilation or PDF text-extraction, and the same codepoint
classes are the known vector for both steganographic text-watermarking and
zero-width prompt-injection payloads hidden in pasted text.

Usage:
    python3 strip_invisible_chars.py --check <path>...   # report only, exit 1 if found
    python3 strip_invisible_chars.py --fix <path>...     # rewrite files in place

<path> may be a .tex file or a directory (scanned recursively for *.tex).
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

# Explicit ranges not reliably caught by category() alone.
_VARIATION_SELECTORS = range(0xFE00, 0xFE10)
_VARIATION_SELECTORS_SUPPLEMENT = range(0xE0100, 0xE01F0)
_UNICODE_TAGS_BLOCK = range(0xE0000, 0xE0080)
_INVISIBLE_CATEGORIES = {"Cf", "Cc", "Co", "Cs"}
_ALLOWED_CONTROL = {"\t", "\n", "\r"}
_NBSP = " "


def _is_invisible(ch: str) -> bool:
    """True if `ch` is a non-printable/format-control codepoint with no place in prose."""
    if ch in _ALLOWED_CONTROL:
        return False
    cp = ord(ch)
    if cp in _VARIATION_SELECTORS or cp in _VARIATION_SELECTORS_SUPPLEMENT:
        return True
    if cp in _UNICODE_TAGS_BLOCK:
        return True
    return unicodedata.category(ch) in _INVISIBLE_CATEGORIES


def _char_label(ch: str) -> str:
    """Human-readable `U+XXXX NAME` label for a codepoint."""
    name = unicodedata.name(ch, "<unnamed>")
    return f"U+{ord(ch):04X} {name}"


def scan_text(text: str) -> list[tuple[int, int, str]]:
    """Return (line, col, char) for every invisible char and NBSP in `text`."""
    hits: list[tuple[int, int, str]] = []
    line, col = 1, 1
    for ch in text:
        if ch == "\n":
            line += 1
            col = 1
            continue
        if _is_invisible(ch) or ch == _NBSP:
            hits.append((line, col, ch))
        col += 1
    return hits


def clean_text(text: str, *, keep_nbsp: bool) -> str:
    """Return `text` with invisible chars removed and NBSP normalized to a space."""
    out = []
    for ch in text:
        if _is_invisible(ch):
            continue
        if ch == _NBSP and not keep_nbsp:
            out.append(" ")
            continue
        out.append(ch)
    return "".join(out)


def iter_tex_files(paths: list[str]) -> list[Path]:
    """Expand CLI path args into a flat, deduplicated list of .tex files."""
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.tex")))
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f"error: path not found: {p}")
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only (default)")
    mode.add_argument("--fix", action="store_true", help="rewrite files in place")
    parser.add_argument(
        "--keep-nbsp",
        action="store_true",
        help="don't normalize non-breaking spaces to regular spaces",
    )
    parser.add_argument("paths", nargs="+", help=".tex file(s) or directory(ies)")
    args = parser.parse_args()

    files = iter_tex_files(args.paths)
    if not files:
        print("no .tex files found", file=sys.stderr)
        return 1

    total_hits = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        hits = scan_text(text)
        if not hits:
            continue
        total_hits += len(hits)
        print(f"{path}: {len(hits)} suspicious character(s)")
        for line, col, ch in hits:
            print(f"  {line}:{col}  {_char_label(ch)}")
        if args.fix:
            cleaned = clean_text(text, keep_nbsp=args.keep_nbsp)
            path.write_text(cleaned, encoding="utf-8")
            print(f"  -> cleaned, {len(text) - len(cleaned)} char(s) removed/replaced")

    if total_hits == 0:
        print(f"clean: 0 suspicious characters across {len(files)} file(s)")
        return 0

    if not args.fix:
        print(f"\n{total_hits} suspicious character(s) total — rerun with --fix to remove them")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
