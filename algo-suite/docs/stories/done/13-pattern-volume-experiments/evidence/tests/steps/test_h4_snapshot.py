"""BDD checks of actual completed H4 artifacts; no simulated financial outputs."""

import csv
import importlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from pytest_bdd import given, scenarios, then, when

EVIDENCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EVIDENCE))
COLLECT = importlib.import_module("snapshot_h4_results")
FIGURES = importlib.import_module("render_h4_figures")
scenarios("../features/h4_snapshot.feature")


@given("the real completed H4 snapshot", target_fixture="snapshot")
def snapshot():
    """Load the independently gated archive, including zero-trade cells if present."""
    return json.loads(FIGURES.SNAPSHOT.read_text())


@then("both parents and all cell manifests pass the completion gate")
def gates(snapshot):
    """Require all eight cells without selecting for positive returns or trade activity."""
    assert len(snapshot["runs"]) == 8
    for matrix in snapshot["matrices"]:
        COLLECT.require_complete(matrix)
    for run in snapshot["runs"]:
        COLLECT.validate_cell(run)


@then("each cell has matching configuration, model hashes, and actual trade count")
def actual_artifacts(snapshot):
    """Check archived byte identities against sources, not win-rate-derived counts."""
    for run in snapshot["runs"]:
        for name in ("model.json", "trades.json", "strategy-config.json", "run.json"):
            FIGURES.previous.verify_artifact(run["files"][name])
        assert len(run["files"]["trades.json"]["value"]) == run["files"]["run.json"]["value"][
            "closed_trades"]


@then("every filter has archived parameters or an explicit absence")
def filter_coverage(snapshot):
    """Keep F4 and volume absences visible alongside all F1-F7 parameters."""
    for run in snapshot["runs"]:
        sections = COLLECT.parameter_sections(run["files"]["strategy-config.json"]["value"])
        assert set(sections) == {"F1", "F2", "F3", "F4", "volume", "F5", "F6", "F7"}
        assert sections["F1"]["price_features"]["bar_minutes"] == 240


@when("the final integrity report is marked unsuccessful in memory", target_fixture="rejection")
def bad_integrity(snapshot):
    """Do not mutate any source while exercising the incomplete-matrix rejection."""
    matrix = deepcopy(snapshot["matrices"][0])
    matrix["files"]["final-input-check.json"]["value"]["ok"] = False
    with pytest.raises(ValueError) as error:
        COLLECT.require_complete(matrix)
    return str(error.value)


@then("the completion gate rejects the matrix")
def rejected_matrix(rejection):
    """Assert that parent success alone cannot pass the evidence gate."""
    assert "Incomplete matrix" in rejection


@when("both H4 family figures are rendered", target_fixture="figures")
def figures(snapshot):
    """Render all cells in memory only, leaving frozen exports intact."""
    figures = [FIGURES.make_figure(snapshot["runs"][:4], "baseline"),
               FIGURES.make_figure(snapshot["runs"][4:], "hybrid")]
    yield figures
    for figure in figures:
        FIGURES.previous.plt.close(figure)


@then("all eight series preserve equity and drawdown in two to one panels")
def real_samples(figures, snapshot):
    """Independently parse CSV columns and compare every sample without resampling."""
    for index, run in enumerate(snapshot["runs"]):
        figure = figures[index // 4]
        assert figure.axes[0].get_gridspec().get_height_ratios() == [2, 1]
        with FIGURES.previous.local_path(run["files"]["equity.csv"]["path"]).open() as handle:
            rows = list(csv.DictReader(handle))
        np.testing.assert_array_equal(figure.axes[0].lines[index % 4].get_ydata(),
                                      [float(row["equity"]) for row in rows])
        np.testing.assert_allclose(figure.axes[1].lines[index % 4].get_ydata(),
                                    [-float(row["drawdown_pct"]) for row in rows])


@then("every H4 legend links to its own complete parameter entry")
def links(figures, snapshot):
    """Link coincident curves as separate cells, not a selected representative."""
    labels = [label for figure in figures for label in figure.legends[0].get_texts()]
    for label, run in zip(labels, snapshot["runs"], strict=True):
        assert label.get_text().startswith(run["reference"] + " ")
        assert label.get_url().endswith("#" + run["reference"].lower())


@when("the expected H4 equity hash is changed in memory", target_fixture="rejection")
def changed_hash(snapshot):
    """Exercise hash rejection while keeping experiment bytes untouched."""
    artifact = dict(snapshot["runs"][0]["files"]["equity.csv"], sha256="0" * 64)
    with pytest.raises(ValueError) as error:
        FIGURES.previous.verify_artifact(artifact)
    return str(error.value)


@then("H4 rendering rejects the stale evidence")
def rejected_hash(rejection):
    """Require a specific error instead of silently plotting changed evidence."""
    assert "Source hash mismatch" in rejection
