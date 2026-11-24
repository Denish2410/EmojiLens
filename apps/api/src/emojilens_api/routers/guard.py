"""EmojiGuard API: assessment, detector training and baseline/ablation evaluation.

Ground truth for detection is *constructive*: a variant is labelled 1 when its recipe applied a
concealment or obfuscation family (unicode_smuggling, homoglyph, text_obfuscation, emoji_cipher),
otherwise 0 (sources, identity, emoji substitution and code-mixing, which are meaning-bearing
rather than concealing). These are transformation labels, not human judgments.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from emojilens_api.db.models import DetectorArtifact, GuardEvaluation, Source, Variant
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services import datasets as svc
from emojilens_core.eval.classification import Item, evaluate
from emojilens_core.guard import FEATURES, Ablation, Policy, assess, features
from emojilens_core.guard.baselines import (
    keyword_filter,
    nfkc_normalization,
    no_defence,
    strip_invisibles,
)
from emojilens_core.unicode import analyze

router = APIRouter(prefix="/guard", tags=["guard"])
ADVERSARIAL = {"unicode_smuggling", "homoglyph", "text_obfuscation", "emoji_cipher"}
ABLATIONS: dict[str, Ablation] = {
    "emojiguard_full": Ablation(),
    "rules_only": Ablation(detector=False),
    "detector_only": Ablation(rules=False),
    "without_decoders": Ablation(decoders=False),
    "without_view_rescoring": Ablation(view_rescoring=False),
    "without_indic_aware": Ablation(indic_aware=False),
}


class AblationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: bool = True
    detector: bool = True
    decoders: bool = True
    view_rescoring: bool = True
    indic_aware: bool = True


class PolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_threshold: float = Field(default=0.3, ge=0, le=1)
    flag_threshold: float = Field(default=0.6, ge=0, le=1)
    block_enabled: bool = False
    block_threshold: float = Field(default=0.9, ge=0, le=1)


class AssessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=20000)
    ablation: AblationIn = AblationIn()
    policy: PolicyIn = PolicyIn()
    detector_id: int | None = None


class DataIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str
    version: int = Field(ge=1)
    recipe_hashes: list[str] = Field(min_length=1, max_length=20)
    seed: int = Field(default=0, ge=0)


class EvalIn(DataIn):
    split: str = Field(default="test", pattern="^(train|validation|test)$")
    keywords: list[str] = Field(default_factory=list, max_length=50)
    detector_id: int | None = None
    resamples: int = Field(default=1000, ge=100, le=10000)


def _detector(session: Session, root: Path, detector_id: int | None) -> Any:
    if detector_id is None:
        return None
    art = session.get(DetectorArtifact, detector_id)
    if art is None:
        raise ApiError(404, "detector_not_found", f"No detector {detector_id}.")
    try:
        from emojilens_core.guard.detector import load
    except ImportError as exc:
        raise ApiError(
            503, "dependency_missing", "scikit-learn is not installed (extra 'learn')."
        ) from exc
    path = (root / art.rel_path).resolve()
    if root.resolve() not in path.parents:
        raise ApiError(404, "detector_not_found", "Invalid artifact path.")
    return load(path, art.sha256)


def _rows(
    session: Session, body: DataIn, split: str | None
) -> tuple[list[tuple[str, str, str, str, str, int]], str]:
    """(id, group, language, family, text, label) for sources and selected variants."""
    version = svc.get_version(session, body.dataset, body.version)
    if version.frozen_at is None:
        raise ApiError(409, "version_not_frozen", "Freeze the version first (group-aware splits).")
    srcs = session.scalars(select(Source).where(Source.version_id == version.id)).all()
    by_id = {s.id: s for s in srcs}
    out = [
        (s.external_id, s.source_group, s.language, "source", s.text, 0)
        for s in srcs
        if split is None or s.split == split
    ]
    for v in session.scalars(
        select(Variant).where(
            Variant.version_id == version.id, Variant.recipe_hash.in_(body.recipe_hashes)
        )
    ):
        s = by_id[v.source_id]
        if split is None or v.split == split:
            label = int(any(f in ADVERSARIAL for f in v.families.split("+")))
            out.append(
                (f"{s.external_id}#v{v.id}", s.source_group, s.language, v.families, v.text, label)
            )
    return out, version.dataset.kind


def _assessment_out(a: Any) -> dict[str, Any]:
    d = asdict(a)
    d["recommendation"] = a.recommendation.value
    return d


@router.post("/assess", responses={404: {"model": ErrorResponse}})
def assess_text(body: AssessIn, request: Request) -> dict[str, Any]:
    with request.app.state.sessionmaker() as session:
        det = _detector(session, request.app.state.artifacts_root, body.detector_id)
    a = assess(
        body.text,
        policy=Policy(**body.policy.model_dump()),
        ablation=Ablation(**body.ablation.model_dump()),
        detector=det,
    )
    return _assessment_out(a)


@router.post(
    "/detectors",
    status_code=201,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def train_detector(body: DataIn, request: Request) -> dict[str, Any]:
    try:
        from emojilens_core.guard.detector import save, train
    except ImportError as exc:
        raise ApiError(
            503, "dependency_missing", "scikit-learn is not installed (extra 'learn')."
        ) from exc
    root: Path = request.app.state.artifacts_root
    with request.app.state.sessionmaker() as session:
        train_rows, kind = _rows(session, body, "train")
        val_rows, _ = _rows(session, body, "validation")
        try:
            det = train([(features(analyze(r[4])), r[5]) for r in train_rows], seed=body.seed)
        except ValueError as exc:
            raise ApiError(422, "training_data_insufficient", str(exc)) from exc
        val_items = []
        for rid, group, lang, fam, text, label in val_rows:
            score, _ = det.score(features(analyze(text)))
            val_items.append(Item(rid, group, label, int(score >= 0.5), score, lang, fam))
        val = evaluate(val_items) if val_items else None
        config = body.model_dump() | {
            "train_items": len(train_rows),
            "validation_items": len(val_rows),
            "dataset_kind": kind,
            "features": list(FEATURES),
        }
        name = hashlib.sha256(repr(sorted(config.items())).encode()).hexdigest()[:16]
        rel = f"detectors/{name}.joblib"
        sha = save(det, root / rel, config)
        art = DetectorArtifact(
            version=det.version,
            rel_path=rel,
            sha256=sha,
            feature_schema=list(FEATURES),
            training_config=config,
            evaluation={"validation": None if val is None else asdict(val), "calibrated": False},
        )
        session.add(art)
        session.commit()
        return {
            "id": art.id,
            "version": art.version,
            "sha256": sha,
            "training_config": config,
            "evaluation": art.evaluation,
        }


@router.get("/detectors")
def list_detectors(request: Request) -> list[dict[str, Any]]:
    with request.app.state.sessionmaker() as session:
        return [
            {
                "id": d.id,
                "version": d.version,
                "sha256": d.sha256,
                "training_config": d.training_config,
                "evaluation": d.evaluation,
                "created_at": d.created_at.isoformat(),
            }
            for d in session.scalars(select(DetectorArtifact).order_by(DetectorArtifact.id.desc()))
        ]


def _strata(items: list[Item], resamples: int, seed: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key in ("language", "family"):
        buckets: dict[str, list[Item]] = {}
        for i in items:
            buckets.setdefault(getattr(i, key), []).append(i)
        out[key] = {
            k: asdict(evaluate(v, resamples=resamples, seed=seed))
            for k, v in sorted(buckets.items())
        }
    return out


@router.post("/evaluations", status_code=201, responses={409: {"model": ErrorResponse}})
def run_evaluation(body: EvalIn, request: Request) -> dict[str, Any]:
    with request.app.state.sessionmaker() as session:
        det = _detector(session, request.app.state.artifacts_root, body.detector_id)
        rows, kind = _rows(session, body, body.split)
        if not rows:
            raise ApiError(422, "no_items", f"No items in split '{body.split}'.")
        systems: dict[str, Any] = {
            "no_defence": no_defence,
            "strip_invisibles": strip_invisibles,
            "nfkc_normalization": nfkc_normalization,
            "keyword_filter": keyword_filter(tuple(body.keywords)),
        }
        results: dict[str, Any] = {"systems": {}, "unavailable": {}}
        if not body.keywords:
            results["unavailable"]["keyword_filter"] = "no keywords configured"
            systems.pop("keyword_filter")
        results["unavailable"]["offtheshelf_classifier"] = (
            "no installed safety classifier (see docs/MODEL_SETUP_M4.md)"
        )
        for name, fn in systems.items():
            items = []
            for rid, group, lang, fam, text, label in rows:
                t0 = time.perf_counter()
                flagged, score, _ = fn(text)
                items.append(
                    Item(
                        rid,
                        group,
                        label,
                        int(flagged),
                        score,
                        lang,
                        fam,
                        (time.perf_counter() - t0) * 1000,
                    )
                )
            results["systems"][name] = {
                "kind": "baseline",
                "overall": asdict(evaluate(items, resamples=body.resamples, seed=body.seed)),
                "strata": _strata(items, 200, body.seed),
            }
        for name, ab in ABLATIONS.items():
            if not ab.rules and det is None:
                results["unavailable"][name] = "requires a trained detector"
                continue
            items = []
            for rid, group, lang, fam, text, label in rows:
                a = assess(text, ablation=ab, detector=det)
                items.append(
                    Item(
                        rid,
                        group,
                        label,
                        int(a.risk_score >= Policy().review_threshold),
                        a.risk_score,
                        lang,
                        fam,
                        a.latency_ms,
                    )
                )
            results["systems"][name] = {
                "kind": "emojiguard",
                "overall": asdict(evaluate(items, resamples=body.resamples, seed=body.seed)),
                "strata": _strata(items, 200, body.seed),
            }
        texts = {r[0]: r[4] for r in rows}
        results["items"] = {
            rid: {"text": texts[rid], "label": lab, "language": lang, "family": fam}
            for rid, _g, lang, fam, _t, lab in rows
        }
        config = body.model_dump() | {
            "dataset_kind": kind,
            "decision_threshold": Policy().review_threshold,
            "label_rule": sorted(ADVERSARIAL),
        }
        ev = GuardEvaluation(config=config, results=results)
        session.add(ev)
        session.commit()
        return {
            "id": ev.id,
            "config": config,
            "results": results,
            "research_reportable": kind != "synthetic_fixture",
        }


@router.get("/evaluations")
def list_evaluations(request: Request) -> list[dict[str, Any]]:
    with request.app.state.sessionmaker() as session:
        return [
            {"id": e.id, "config": e.config, "created_at": e.created_at.isoformat()}
            for e in session.scalars(select(GuardEvaluation).order_by(GuardEvaluation.id.desc()))
        ]


@router.get("/evaluations/{eval_id}", responses={404: {"model": ErrorResponse}})
def get_evaluation(eval_id: int, request: Request) -> dict[str, Any]:
    with request.app.state.sessionmaker() as session:
        e = session.get(GuardEvaluation, eval_id)
        if e is None:
            raise ApiError(404, "evaluation_not_found", f"No evaluation {eval_id}.")
        return {
            "id": e.id,
            "config": e.config,
            "results": e.results,
            "research_reportable": e.config.get("dataset_kind") != "synthetic_fixture",
            "created_at": e.created_at.isoformat(),
        }
