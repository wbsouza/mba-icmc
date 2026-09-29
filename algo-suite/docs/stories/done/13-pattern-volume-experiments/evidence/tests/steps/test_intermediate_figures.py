"""BDD checks against the actual frozen runs; no synthetic performance data."""

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from pytest_bdd import given, scenarios, then, when

EVIDENCE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "story13_intermediate_figures", EVIDENCE / "render_intermediate_figures.py"
)
assert SPEC is not None and SPEC.loader is not None
FIGURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIGURES)
scenarios("../features/intermediate_figures.feature")


@given("the real intermediate-results snapshot", target_fixture="runs")
def real_snapshot():
    """Load the evidence collected from completed and still-running real jobs."""
    snapshot = json.loads(FIGURES.SNAPSHOT.read_text())
    return {run["reference"]: run for run in snapshot["runs"]}


@when("the September execution figure is prepared", target_fixture="figure")
def prepare_figure(runs):
    """Render the actual September pair without writing any artifact."""
    figure = FIGURES.make_figure([runs["R08"], runs["R13"]], "September 2015")
    yield figure
    FIGURES.plt.close(figure)


@then("the chart has equity and drawdown panels in a two to one ratio")
def panel_geometry(figure):
    """Check the requested composition and shared date axis."""
    assert len(figure.axes) == 2
    assert figure.axes[0].get_gridspec().get_height_ratios() == [2, 1]
    assert figure.axes[0].get_shared_x_axes().joined(*figure.axes)


@then("every plotted sample equals its source equity and drawdown")
def source_samples_match(figure, runs):
    """Compare plotted coordinates with independently parsed existing CSV columns."""
    for index, reference in enumerate(("R08", "R13")):
        path = FIGURES.local_path(runs[reference]["files"]["equity.csv"]["path"])
        with path.open() as handle:
            rows = list(csv.DictReader(handle))
        equity = np.array([float(row["equity"]) for row in rows])
        underwater = -np.array([float(row["drawdown_pct"]) for row in rows])
        np.testing.assert_array_equal(figure.axes[0].lines[index].get_ydata(), equity)
        np.testing.assert_allclose(figure.axes[1].lines[index].get_ydata(), underwater)
        dates = figure.axes[0].lines[index].get_xdata()
        assert [moment.isoformat() for moment in dates] == [row["time"] for row in rows]


@then("both legend labels link to their own parameter appendix entries")
def parameter_links_match(figure):
    """Prevent a curve from being attributed to another run's parameters."""
    for label, reference in zip(figure.legends[0].get_texts(), ("R08", "R13"), strict=True):
        assert label.get_text().startswith(reference + " ")
        assert "risk=3%" in label.get_text()
        assert label.get_url().endswith("#" + reference.lower())


@when("an unfinished run is selected for plotting", target_fixture="rejection")
def reject_unfinished(runs):
    """Use the actually unfinished annual baseline entry."""
    with pytest.raises(ValueError) as rejection:
        FIGURES.load_completed(runs["R19"])
    return str(rejection.value)


@then("plotting rejects the selection as incomplete")
def incomplete_message(rejection):
    """Require an explicit rejection rather than provisional performance."""
    assert "Incomplete run R19" in rejection


@when("a completed run is checked against a mismatched archived hash", target_fixture="rejection")
def reject_changed_hash(runs):
    """Change only the expected fingerprint in memory; source bytes stay untouched."""
    artifact = dict(runs["R08"]["files"]["equity.csv"], sha256="0" * 64)
    with pytest.raises(ValueError) as rejection:
        FIGURES.verify_artifact(artifact)
    return str(rejection.value)


@then("plotting rejects the source hash mismatch")
def hash_message(rejection):
    """Require a stale-evidence error before any figure is rendered."""
    assert "Source hash mismatch" in rejection
