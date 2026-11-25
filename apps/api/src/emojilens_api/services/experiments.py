"""Experiment execution: persistent job lifecycle, cancellation, interruption and resumption.

States: queued -> running -> completed | failed | cancelled; running/cancelling -> interrupted
when the API process restarts mid-run. Interrupted and failed runs are never marked successful.
A resumed run skips outputs that already exist, so stored results are never duplicated.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from emojilens_api.db import utcnow
from emojilens_api.db.models import Experiment, ModelOutput, ModelVersion, Source, Variant
from emojilens_api.services.multimodal import (
    artifact_path,
    get_or_render,
    ocr_reading,
    reading_extra,
)
from emojilens_core.datasets import text_sha256
from emojilens_core.models import (
    SAFETY_TASK,
    Capability,
    ModelRegistry,
    SafetyJudge,
    response_behavior,
)
from emojilens_core.models.safety import classifier_safety
from emojilens_core.multimodal import RenderConfig
from emojilens_core.repro import environment_metadata

log = logging.getLogger("emojilens.experiments")

# Repository root in a source checkout; git metadata is simply absent elsewhere.
REPO_ROOT = Path(__file__).resolve().parents[5]
SUPPORTED_MODALITIES = ("text", "ocr", "vlm")
DEFAULT_VLM_PROMPT = "Transcribe the text in this image exactly."
TERMINAL = ("completed", "failed", "cancelled", "interrupted")


def config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def model_version_row(session: Session, registry: ModelRegistry, key: str) -> ModelVersion:
    meta = registry.adapter(key).metadata()
    fields = {
        "key": key,
        "model_id": meta.model_id,
        "revision": meta.revision,
        "tokenizer_revision": meta.tokenizer_revision,
        "adapter": meta.adapter,
        "adapter_version": meta.adapter_version,
        "device": meta.device,
        "dtype": meta.dtype,
        "library_versions": meta.library_versions,
        "test_double": meta.test_double,
    }
    fp = config_hash(fields)
    row = session.scalar(select(ModelVersion).where(ModelVersion.fingerprint == fp))
    if row is None:
        row = ModelVersion(fingerprint=fp, **fields)
        session.add(row)
        session.flush()
    return row


@dataclass(frozen=True, slots=True)
class Unit:
    source_id: int
    variant_id: int | None
    text: str
    language: str
    model_key: str
    capability: Capability
    modality: str


def units(session: Session, registry: ModelRegistry, config: dict[str, Any]) -> Iterator[Unit]:
    version_id = int(config["version_id"])
    sources = {
        s.id: s
        for s in session.scalars(
            select(Source).where(Source.version_id == version_id).order_by(Source.id)
        )
    }
    items: list[tuple[int, int | None, str]] = [(s.id, None, s.text) for s in sources.values()]
    if config.get("recipe_hashes"):
        items += [
            (v.source_id, v.id, v.text)
            for v in session.scalars(
                select(Variant)
                .where(
                    Variant.version_id == version_id,
                    Variant.recipe_hash.in_(config["recipe_hashes"]),
                )
                .order_by(Variant.id)
            )
        ]
    for source_id, variant_id, text in items:
        for key in config["model_keys"]:
            supported = registry.config(key).capabilities
            for cap in config["capabilities"]:
                c = Capability(cap)
                if c in supported:
                    for modality in config["modalities"]:
                        # Vision input runs only on rendered images; other capabilities never do.
                        if (modality == "vlm") != (c is Capability.VISION_INPUT):
                            continue
                        yield Unit(
                            source_id,
                            variant_id,
                            text,
                            sources[source_id].language,
                            key,
                            c,
                            modality,
                        )


def count_units(session: Session, registry: ModelRegistry, config: dict[str, Any]) -> int:
    return sum(1 for _ in units(session, registry, config))


def run_experiment(
    factory: sessionmaker[Session],
    registry: ModelRegistry,
    exp_id: int,
    artifacts_root: Path | None = None,
) -> str:
    """Execute one experiment to a terminal state and return that state."""
    with factory() as session:
        exp = session.get(Experiment, exp_id)
        if exp is None or exp.status not in ("queued",):
            return exp.status if exp else "missing"
        exp.status, exp.started_at, exp.error = "running", utcnow(), None
        snapshot = {"started_at": exp.started_at.isoformat(), **environment_metadata(REPO_ROOT)}
        exp.run_environments = [*(exp.run_environments or []), snapshot]
        session.commit()
        config = dict(exp.config)
        judge = SafetyJudge(config["label_map"]) if config.get("label_map") else None
        try:
            versions = {k: model_version_row(session, registry, k).id for k in config["model_keys"]}
            session.commit()
            for unit in units(session, registry, config):
                session.refresh(exp, ["cancel_requested"])
                if exp.cancel_requested:
                    exp.status, exp.finished_at = "cancelled", utcnow()
                    session.commit()
                    return "cancelled"
                vkey = unit.variant_id or 0
                exists = session.scalar(
                    select(ModelOutput.id).where(
                        ModelOutput.experiment_id == exp.id,
                        ModelOutput.model_version_id == versions[unit.model_key],
                        ModelOutput.source_id == unit.source_id,
                        ModelOutput.variant_key == vkey,
                        ModelOutput.capability == unit.capability.value,
                        ModelOutput.modality == unit.modality,
                    )
                )
                if exists:
                    continue
                reading: dict[str, Any] | None = None
                model_input = unit.text
                if unit.modality == "vlm":
                    if artifacts_root is None:
                        raise RuntimeError("vlm modality requires an artifacts directory")
                    art = get_or_render(session, artifacts_root, unit.text, RenderConfig())
                    prompt = str(config.get("vlm_prompt") or DEFAULT_VLM_PROMPT)
                    reading = {
                        "artifact_id": art.id,
                        "image_sha256": art.image_sha256,
                        "prompt": prompt,
                    }
                    image = str(artifact_path(artifacts_root, art))
                    result = registry.run(unit.model_key, unit.capability, image, prompt=prompt)
                elif unit.modality == "ocr":
                    if artifacts_root is None:
                        raise RuntimeError("ocr modality requires an artifacts directory")
                    art, ocr = ocr_reading(session, artifacts_root, registry, unit.text)
                    reading = reading_extra(art, ocr)
                    model_input = str(ocr.normalized.get("text") or "")
                if unit.modality != "vlm":
                    result = registry.run(unit.model_key, unit.capability, model_input)
                declared = registry.config(unit.model_key).languages
                supported = (unit.language in declared) if declared else None
                coverage = {"_language": unit.language, "_language_supported": supported}
                result = replace(result, normalized={**result.normalized, **coverage})
                if reading is not None:
                    result = replace(result, normalized={**result.normalized, "_reading": reading})
                    if reading.get("ocr_error"):
                        result = replace(
                            result,
                            error={
                                "code": "ocr_failed",
                                "message": "OCR reading failed",
                                "details": reading["ocr_error"],
                            },
                        )
                behavior = safety = None
                if unit.capability is Capability.GENERATE:
                    behavior = response_behavior(result)[0].value
                is_safety_model = registry.config(unit.model_key).task == SAFETY_TASK
                if unit.capability is Capability.CLASSIFY and judge is not None and is_safety_model:
                    safety = classifier_safety(result, judge.label_map, judge.unsafe_threshold)[
                        0
                    ].value
                tok = result.tokenization
                session.add(
                    ModelOutput(
                        experiment_id=exp.id,
                        model_version_id=versions[unit.model_key],
                        source_id=unit.source_id,
                        variant_id=unit.variant_id,
                        variant_key=vkey,
                        capability=unit.capability.value,
                        modality=unit.modality,
                        input_sha256=text_sha256(model_input),
                        raw=result.raw_output,
                        normalized=result.normalized,
                        tokenization=None
                        if tok is None
                        else {
                            "tokens": tok.tokens,
                            "ids": tok.ids,
                            "offsets": tok.offsets,
                            "unknown": tok.unknown_tokens,
                        },
                        params=result.params,
                        latency_ms=result.latency_ms,
                        error=result.error,
                        behavior=behavior,
                        safety=safety,
                    )
                )
                exp.done_items += 1
                exp.failed_items += 1 if result.error else 0
                session.commit()
            exp.status, exp.finished_at = "completed", utcnow()
            session.commit()
            return "completed"
        except Exception as exc:
            session.rollback()
            exp = session.get(Experiment, exp_id)
            assert exp is not None
            exp.status, exp.finished_at = "failed", utcnow()
            exp.error = f"{type(exc).__name__}: {exc}"[:2000]
            session.commit()
            log.exception("experiment %s failed", exp_id)
            return "failed"


def mark_interrupted(factory: sessionmaker[Session]) -> int:
    """On startup, runs left in running/cancelling were interrupted: record that explicitly."""
    with factory() as session:
        rows = session.scalars(
            select(Experiment).where(Experiment.status.in_(("running", "cancelling")))
        ).all()
        for exp in rows:
            exp.status = "interrupted"
            exp.finished_at = utcnow()
            exp.error = (
                "The API stopped while this experiment was running. "
                "Stored outputs are kept; resume to continue."
            )
        session.commit()
        return len(rows)


class ExperimentWorker:
    """Single background thread that executes queued experiments in order."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        registry: ModelRegistry,
        poll_s: float = 0.5,
        artifacts_root: Path | None = None,
    ) -> None:
        self.factory = factory
        self.artifacts_root = artifacts_root
        self.registry = registry
        self.poll_s = poll_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> int | None:
        with self.factory() as session:
            exp_id = session.scalar(
                select(Experiment.id)
                .where(Experiment.status == "queued")
                .order_by(Experiment.id)
                .limit(1)
            )
        if exp_id is None:
            return None
        run_experiment(self.factory, self.registry, exp_id, self.artifacts_root)
        return exp_id

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self.run_once() is None:
                    self._stop.wait(self.poll_s)
            except Exception:  # keep the worker alive; the failure is logged
                log.exception("experiment worker iteration failed")
                self._stop.wait(self.poll_s)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._loop, name="experiment-worker", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
