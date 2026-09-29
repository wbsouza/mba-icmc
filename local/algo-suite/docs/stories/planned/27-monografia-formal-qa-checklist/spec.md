# Story 27 — Formal monograph QA checklist

Status: planned. Continuation of Story 07 (monografia document QA), closed
2026-09-28 for what it actually delivered: the §2 build-hygiene pass
(`make pt-scan`/`make verify`/`make rebuild` clean), plus ad-hoc verification
repeated throughout tonight's Chapter 4/5 work (0 undefined citations, 153
pages, clean compile confirmed after every edit — not the story's own
formal deliverable, but functionally the same check, done repeatedly).

## Problem statement

The story's §1 (content-consistency review against `01-introduction.tex`
and `03-methodology.tex`) and a written, reusable QA checklist (rather than
ad-hoc `make verify` runs) were never produced as their own artifact.

## Goals

- [ ] Review `chapters/01-introduction.tex:64` and `chapters/03-methodology.tex:257`
      against the final Chapter 4/5 content for consistency.
- [ ] Write down a reusable QA checklist (not just re-running `make verify`
      each time) so future chapter edits have a fixed procedure to follow.

## Notes

Low priority relative to Stories 25/26 — the actual build hygiene this
story cared about (clean compile, no undefined references) has already
been checked repeatedly and is currently green.
