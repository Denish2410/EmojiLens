"""Learned detector: logistic regression over interpretable EmojiGuard features.

Trained only on a dataset version's *train* split (group-aware splits are assigned at freeze
time), with validation/test metrics computed on held-out splits. Scores are uncalibrated.
Requires the optional 'learn' extra (scikit-learn, joblib).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from emojilens_core.guard.engine import FEATURES

DETECTOR_VERSION = "0.1.0"


@dataclass
class LogisticDetector:
    model: Any
    version: str
    feature_schema: tuple[str, ...] = FEATURES

    def score(self, features: dict[str, float]) -> tuple[float, dict[str, float]]:
        x = [[features[f] for f in self.feature_schema]]
        p = float(self.model.predict_proba(x)[0][1])
        coef = {
            f: float(c) * features[f]
            for f, c in zip(self.feature_schema, self.model.coef_[0], strict=True)
        }
        return p, coef


def train(rows: list[tuple[dict[str, float], int]], seed: int = 0) -> LogisticDetector:
    from sklearn.linear_model import LogisticRegression

    labels = {y for _, y in rows}
    if labels != {0, 1}:
        raise ValueError("training data needs both positive and negative examples")
    x = [[f[name] for name in FEATURES] for f, _ in rows]
    y = [lab for _, lab in rows]
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed).fit(x, y)
    digest = hashlib.sha256(
        json.dumps([model.coef_.tolist(), model.intercept_.tolist()]).encode()
    ).hexdigest()[:12]
    return LogisticDetector(model=model, version=f"{DETECTOR_VERSION}+{digest}")


def save(det: LogisticDetector, path: Path, meta: dict[str, Any]) -> str:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": det.model,
            "version": det.version,
            "features": list(det.feature_schema),
            "meta": meta,
        },
        path,
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, expected_sha256: str) -> LogisticDetector:
    """Load a detector artifact only after verifying its hash (joblib/pickle must be trusted)."""
    import joblib

    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("detector artifact hash mismatch; refusing to load")
    blob = joblib.load(path)
    if tuple(blob["features"]) != FEATURES:
        raise ValueError("detector feature schema does not match this engine version")
    return LogisticDetector(model=blob["model"], version=blob["version"])
