"""`algo-analyze results-db`: every finished run directory into one SQLite file.

The viewer (`algo-viewer/`) opens the file in the browser with sql.js, so the schema is
flat, versioned (`schema_version`) and built purely from the run artifacts that
`algo-backtest run` + `algo-backtest statement` leave on disk — no engine re-run, nothing
fabricated. See `schema.py` for the tables, `build.py` for the orchestration.
"""

from algo_analyze.resultsdb.build import BuildReport, BuildRequest, RunsRoot, build_database

__all__ = ["BuildReport", "BuildRequest", "RunsRoot", "build_database"]
