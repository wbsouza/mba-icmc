-- One-time full-window materialization of GDELT Events into our own BigQuery schema.
--
-- WHY run this at all: querying the public gdelt-bq.gdeltv2.events table directly, repeatedly,
-- for every local batch we'd ever need, means re-scanning/re-billing a huge public table on
-- every run/retry -- expensive and slow. Copying the window we need into our own small table
-- ONCE means every later read (the per-batch local-Parquet materializer, the day-join, any
-- future ad-hoc question) is a cheap query against OUR table instead.
--
-- WHY CREATE TABLE, not CREATE OR REPLACE: this must run exactly once, ever, for a given
-- window. `_ensure_full_table` (bigquery_ctas_export_gdelt_events.py) checks whether this
-- table already exists before ever issuing this query -- if it does, it's reused
-- unconditionally, so accidentally running this file twice is a harmless no-op error
-- ("already exists"), not a silent re-scan of the public source, not a corrupted/duplicated
-- destination table.
--
-- WHY SELECT * (not a curated column subset): explicit decision this session -- "we might
-- discover later something important in their data but if we just import what we need later
-- we have no chance unless we reimport from scratch." Pulling everything once means any later
-- "give me exactly column X" is a free query against this table, not another multi-minute
-- scan of the public source.
--
-- WHY this window (2015-02-01 .. 2024-12-31): matches the thesis's coverage-rule lower bound
-- (2015-02-19, GDELT 2.0's launch date) and the same 10-year window already used elsewhere in
-- this project's spec history (see spec.md's Assumptions table).
--
-- Source: gdelt-bq.gdeltv2.events -- Google's public BigQuery dataset mirror of the GDELT
-- Project's Events table. GDELT publishes this data as free/open for any use (see
-- gdeltproject.org); `gdelt-bq` is a public GCP project anyone can query, not something we own
-- or control -- our own `mba-ai-509708.gdelt.events` below is our private, billed COPY of a
-- slice of it, not the origin.
-- Destination: mba-ai-509708.gdelt.events (ours, private, billed to this project)
-- SQLDATE is 8-digit YYYYMMDD (verified against the live schema, not assumed)
-- See spec.md's Reproducibility section for the full pipeline this feeds into.

CREATE TABLE `mba-ai-509708.gdelt.events` AS
SELECT *
FROM `gdelt-bq.gdeltv2.events`
WHERE SQLDATE BETWEEN 20150201 AND 20241231
