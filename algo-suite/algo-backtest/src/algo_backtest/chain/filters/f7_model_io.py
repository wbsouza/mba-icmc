"""Portable, pickle-free persistence for F7's `TrainedMetaLearner`.

A model is trained on the host (the uv workspace's scikit-learn/LightGBM/numpy) but
loaded inside the pinned LEAN container, which ships *older* versions of all three
(sklearn 1.6 / LightGBM 4.6 / numpy 1.26 at `quantconnect/lean:17748`). A pickled
(`joblib`) model does not survive that: a newer `LogisticRegression` unpickled by an
older sklearn fails at `predict_proba` (no `multi_class` attribute). So the model is
stored as data, not objects:

- each family sub-model as LightGBM's own text model format (`Booster.model_to_string`,
  stable across LightGBM 4.x) — reloaded as a `lightgbm.Booster`;
- the logistic combiner as its coefficients and intercept — evaluated directly as a
  sigmoid, no sklearn object needed at inference.

One JSON document also carries the training `provenance` (window, split, rows, input
hashes, git revision, package versions), so the file a backtest loads is self-describing.
Loading JSON executes no code, unlike unpickling.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    LightGBMFamilyModel,
    TrainedMetaLearner,
)
from lightgbm import Booster

FORMAT = "algo-backtest/f7-meta-learner"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class BoosterFamilyModel:
    """`FamilyPredictor` backed by a raw `lightgbm.Booster` (binary objective)."""

    booster: Booster

    def predict_proba_up(self, vector: Sequence[float]) -> float:
        """P(up) for one row: a binary booster's `predict` is the class-1 probability."""
        proba: Any = self.booster.predict(np.asarray([vector], dtype=float))
        return float(proba[0])


@dataclass(frozen=True)
class LogisticCombiner:
    """A fitted binary logistic regression reduced to its parameters."""

    coef: tuple[float, ...]
    intercept: float

    def predict_proba(self, inputs: np.ndarray) -> np.ndarray:
        """`[P(0), P(1)]` per row — the same contract as sklearn's `predict_proba`."""
        z = np.asarray(inputs, dtype=float) @ np.asarray(self.coef) + self.intercept
        up = 1.0 / (1.0 + np.exp(-z))
        return np.column_stack([1.0 - up, up])


def _booster_text(model: object) -> str:
    """A family sub-model's LightGBM text model, whichever predictor wraps it."""
    if isinstance(model, LightGBMFamilyModel):
        text: str = model.booster.booster_.model_to_string()
        return text
    if isinstance(model, BoosterFamilyModel):
        text = model.booster.model_to_string()
        return text
    raise TypeError(f"cannot persist family model of type {type(model).__name__}")


def _combiner_params(meta_model: object) -> dict[str, object]:
    """The combiner's coefficients/intercept from a fitted sklearn model or a reloaded one."""
    if isinstance(meta_model, LogisticCombiner):
        return {"coef": list(meta_model.coef), "intercept": meta_model.intercept}
    coef: Any = getattr(meta_model, "coef_", None)
    intercept: Any = getattr(meta_model, "intercept_", None)
    classes: Any = getattr(meta_model, "classes_", None)
    if coef is None or intercept is None or classes is None or list(classes) != [0, 1]:
        raise TypeError("meta_model must be a fitted binary LogisticRegression over labels [0, 1]")
    return {"coef": [float(c) for c in coef[0]], "intercept": float(intercept[0])}


def dump_model(
    model: TrainedMetaLearner, path: Path, provenance: Mapping[str, object]
) -> None:
    """Write `model` (plus its training `provenance`) as one portable JSON document."""
    document = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "families": [family.value for family in model.families],
        "family_models": {
            family.value: _booster_text(model.family_models[family]) for family in model.families
        },
        "combiner": _combiner_params(model.meta_model),
        "provenance": dict(provenance),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")


def load_model(path: Path) -> TrainedMetaLearner:
    """Rebuild a `TrainedMetaLearner` from `dump_model`'s JSON, with no pickle involved.

    Raises:
        ValueError: if the file is not an F7 model document of a supported version.
    """
    document = json.loads(path.read_text())
    if document.get("format") != FORMAT or document.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"{path} is not a {FORMAT} v{FORMAT_VERSION} document "
            f"(format={document.get('format')!r}, version={document.get('format_version')!r}); "
            "retrain it with scripts/train_*_meta_learner.py"
        )
    families = tuple(FeatureFamily(name) for name in document["families"])
    combiner = document["combiner"]
    return TrainedMetaLearner(
        families=families,
        family_models={
            family: BoosterFamilyModel(Booster(model_str=document["family_models"][family.value]))
            for family in families
        },
        meta_model=LogisticCombiner(
            coef=tuple(float(c) for c in combiner["coef"]), intercept=float(combiner["intercept"])
        ),
    )


def load_provenance(path: Path) -> dict[str, object]:
    """The training provenance recorded in a model document."""
    provenance: dict[str, object] = json.loads(path.read_text())["provenance"]
    return provenance


def load_families(path: Path) -> tuple[FeatureFamily, ...]:
    """The feature families a model document was trained on, without building boosters."""
    return tuple(FeatureFamily(name) for name in json.loads(path.read_text())["families"])


def require_families(
    model_families: Sequence[FeatureFamily], strategy_families: Sequence[str], where: str
) -> None:
    """Fail fast unless a model was trained on exactly the strategy's declared families.

    A model's families decide which sub-model outputs its combiner weighs: a baseline
    model (no NEWS) driving `hybrid` would silently ignore F4's enrichment, and a hybrid
    model under `baseline` would read NEWS features nobody provides. Order-insensitive:
    each model carries its own family order.

    Raises:
        ValueError: naming both family sets and `where` the model came from.
    """
    trained = sorted(family.value for family in model_families)
    declared = sorted(strategy_families)
    if trained != declared:
        raise ValueError(
            f"F7 model {where} was trained on families {trained}, but the strategy's "
            f"config.yaml declares meta_learner.families {declared}; train it with the "
            "matching scripts/train_*_meta_learner.py"
        )
