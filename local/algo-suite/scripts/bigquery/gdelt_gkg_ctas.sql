-- One-time full-window materialization of GDELT GKG (Global Knowledge Graph) into our own
-- BigQuery schema.
--
-- WHY run this at all: same reasoning as gdelt_events_ctas.sql -- copy the window we need out
-- of the huge public source ONCE so every later read (per-batch local Parquet, the day-join
-- against Events) is a cheap query against our own small table, never a re-scan of the public
-- source.
--
-- WHY GKG specifically, alongside Events: Events carries only numeric fields (GoldsteinScale,
-- AvgTone, ...) and a bare SOURCEURL -- no article text at all. GKG is what carries real
-- GDELT-extracted per-article content: `Quotations` (actual excerpted quotes), `Extras`
-- (often includes the article's `<PAGE_TITLE>`), `V2Themes`, and a richer `V2Tone` breakdown.
-- This closes the gap flagged this session: a trading decision justified only by a numeric
-- score, with no traceable content behind it, is not defensible in the monograph. Join this
-- table to Events on `SOURCEURL = DocumentIdentifier` (empirically verified, not assumed --
-- see spec.md) to get both the score and the evidence for it in the same place.
--
-- WHY not gdelt_ngrams (the per-minute full-text HTTP pull) instead: verified this session
-- that GDELT has no BigQuery table for it -- it's only ever available as one gzip file per
-- UTC minute over plain HTTP, ~43,200 requests/month, "infinite time" at this window's scale.
-- GKG gets real content cheaply via the same BigQuery path as Events; ngrams remains
-- unbuilt-into-this-story's-scope (see spec.md's Out of Scope table).
--
-- WHY CREATE TABLE, not CREATE OR REPLACE: identical reasoning to the Events file -- must run
-- exactly once. `_ensure_full_table` (bigquery_ctas_export_gdelt_gkg.py) checks existence
-- first; rerunning this file by hand after the table exists just errors harmlessly, it does
-- not re-scan or duplicate anything.
--
-- WHY SELECT * (not a curated column subset): same explicit decision as Events -- "we might
-- discover later something important in their data ... unless we reimport from scratch."
--
-- Source: gdelt-bq.gdeltv2.gkg -- Google's public BigQuery mirror of the GDELT Project's GKG
-- table. GDELT publishes this as free/open for any use (gdeltproject.org); `gdelt-bq` is a
-- public GCP project we don't own or control -- our own `mba-ai-509708.gdelt.gkg` below is our
-- private, billed COPY of a slice of it, not the origin.
-- Destination: mba-ai-509708.gdelt.gkg (ours, private, billed to this project)
-- DATE is 14-digit YYYYMMDDHHMMSS -- different shape from Events' 8-digit SQLDATE; verified
-- against the live schema before writing this, not assumed.
-- See spec.md's Reproducibility section for the full pipeline this feeds into.

CREATE TABLE `mba-ai-509708.gdelt.gkg` AS
SELECT *
FROM `gdelt-bq.gdeltv2.gkg`
WHERE DATE BETWEEN 20150201000000 AND 20241231235959
