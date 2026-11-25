"""Model smoke validation: does each installed model actually execute, on every language variety?

This is an engineering check, not an experiment. It runs one short, harmless probe per variety
through each capability a model declares, twice, and records whether inference executed, how long
it took, a hash of the raw output and whether the two runs agreed. It never invents an outcome:
models that are not installed are recorded as ``skipped`` with the registry's own reason, and
failures keep their structured error code.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from emojilens_core.models import Capability, InferenceResult, ModelRegistry

# Harmless greeting-and-plan probes, one per supported variety, each with an emoji.
PROBES: dict[str, str] = {
    "en": "Good morning, see you at five 🙂",
    "hi": "सुप्रभात, पाँच बजे मिलते हैं 🙂",
    "gu": "સુપ્રભાત, પાંચ વાગ્યે મળીએ 🙂",
    "hi-Latn": "suprabhat, paanch baje milte hain 🙂",
    "gu-Latn": "suprabhat, paanch vage maliye 🙂",
}
IMAGE_CAPS = (Capability.OCR, Capability.VISION_INPUT)
VLM_PROMPT = "Transcribe the text in this image exactly."

Renderer = Callable[[str, Path], str]  # (text, out_dir) -> image path


@dataclass(frozen=True, slots=True)
class ProbeResult:
    model_key: str
    capability: str
    language: str
    status: str  # executed | failed | skipped
    detail: str = ""
    latency_ms: float | None = None
    output_sha256: str | None = None
    deterministic: bool | None = None
    language_declared: bool | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelReport:
    key: str
    model_id: str
    task: str
    revision: str | None
    test_double: bool
    availability: str
    availability_detail: str
    probes: list[ProbeResult]

    @property
    def executed(self) -> int:
        return sum(p.status == "executed" for p in self.probes)

    @property
    def failed(self) -> int:
        return sum(p.status == "failed" for p in self.probes)


def output_hash(result: InferenceResult) -> str:
    raw = result.raw_output
    if result.tokenization is not None:
        raw = {"tokens": result.tokenization.tokens, "ids": result.tokenization.ids}
    blob = json.dumps(raw, sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _summary(result: InferenceResult) -> dict[str, Any]:
    n = result.normalized
    out: dict[str, Any] = {}
    for key in ("label", "dim", "length", "unknown_tokens"):
        if key in n:
            out[key] = n[key]
    if isinstance(n.get("text"), str):
        out["text_chars"] = len(n["text"])
    return out


def validate_model(
    registry: ModelRegistry,
    key: str,
    *,
    languages: tuple[str, ...] = tuple(PROBES),
    renderer: Renderer | None = None,
) -> ModelReport:
    cfg = registry.config(key)
    av = registry.availability(key)
    probes: list[ProbeResult] = []
    for cap in cfg.capabilities:
        for lang in languages:
            declared = (lang in cfg.languages) if cfg.languages else None
            if not av.ok:
                probes.append(
                    ProbeResult(
                        key, cap.value, lang, "skipped", av.detail, language_declared=declared
                    )
                )
                continue
            text = PROBES[lang]
            payload, params = text, {}
            if cap in IMAGE_CAPS:
                if renderer is None:
                    probes.append(
                        ProbeResult(key, cap.value, lang, "skipped", "no renderer available")
                    )
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    payload = renderer(text, Path(tmp))
                    if cap is Capability.VISION_INPUT:
                        params = {"prompt": VLM_PROMPT}
                    first = registry.run(key, cap, payload, **params)
                    second = registry.run(key, cap, payload, **params)
            else:
                first = registry.run(key, cap, payload, **params)
                second = registry.run(key, cap, payload, **params)
            if first.error:
                probes.append(
                    ProbeResult(
                        key,
                        cap.value,
                        lang,
                        "failed",
                        str(first.error.get("code", "error")),
                        latency_ms=first.latency_ms,
                        language_declared=declared,
                    )
                )
                continue
            h1, h2 = output_hash(first), output_hash(second)
            summary = _summary(first)
            if cap in IMAGE_CAPS and isinstance(first.normalized.get("text"), str):
                # Whitespace-insensitive exact read-back of the probe; a quality signal only.
                summary["exact_readback"] = first.normalized["text"].split() == text.split()
            probes.append(
                ProbeResult(
                    key,
                    cap.value,
                    lang,
                    "executed",
                    latency_ms=first.latency_ms,
                    output_sha256=h1,
                    deterministic=h1 == h2,
                    language_declared=declared,
                    summary=summary,
                )
            )
    return ModelReport(
        key=cfg.key,
        model_id=cfg.model_id,
        task=cfg.task,
        revision=cfg.revision,
        test_double=cfg.test_double,
        availability=av.status.value,
        availability_detail=av.detail,
        probes=probes,
    )


def report_to_dict(reports: list[ModelReport]) -> list[dict[str, Any]]:
    return [{**asdict(r), "executed": r.executed, "failed": r.failed} for r in reports]


def render_markdown(
    reports: list[ModelReport], environment: dict[str, Any], checks: list[dict[str, Any]]
) -> str:
    """A human-readable validation report. Every row comes from an executed or skipped probe."""
    lines = [
        "# EmojiLens model validation report",
        "",
        "Engineering smoke validation: each installed model is run twice on one harmless probe per",
        "language variety. This shows that inference executes; it is **not** a research result.",
        "",
        "## Environment",
        "",
        f"- Python {environment['python']} on {environment['os']} {environment['machine']}",
        f"- Device: {environment['device']['selected']} ({environment['device']['reason']})",
        f"- Git commit: {environment['git'].get('commit') or 'unknown'}"
        + (" (uncommitted changes)" if environment["git"].get("dirty") else ""),
        "- Packages: " + ", ".join(f"{k} {v}" for k, v in environment["packages"].items() if v),
        "",
        "## Preflight",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
        *[f"| {c['name']} | {c['status']} | {c['detail']} |" for c in checks],
        "",
        "## Models",
        "",
        "| Model | Task | Revision | Availability | Executed | Failed | Skipped | Deterministic |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        skipped = sum(p.status == "skipped" for p in r.probes)
        det = [p.deterministic for p in r.probes if p.deterministic is not None]
        det_s = "n/a" if not det else "yes" if all(det) else f"{sum(det)}/{len(det)}"
        tag = " (TEST DOUBLE)" if r.test_double else ""
        lines.append(
            f"| {r.key}{tag} | {r.task} | {(r.revision or 'not pinned')[:12]} | {r.availability} "
            f"| {r.executed} | {r.failed} | {skipped} | {det_s} |"
        )
    lines += ["", "## Probes", ""]
    for r in reports:
        lines += [f"### {r.key}", ""]
        if all(p.status == "skipped" for p in r.probes):
            lines += [f"Skipped: {r.availability_detail}", ""]
            continue
        lines += [
            "| Capability | Language | Declared | Status | Latency ms | Output SHA-256 | Summary |",
            "|---|---|---|---|---|---|---|",
        ]
        for p in r.probes:
            declared = {True: "yes", False: "no", None: "unknown"}[p.language_declared]
            lat = "" if p.latency_ms is None else f"{p.latency_ms:.1f}"
            sha = (p.output_sha256 or "")[:16]
            summ = ", ".join(f"{k}={v}" for k, v in p.summary.items()) or p.detail
            lines.append(
                f"| {p.capability} | {p.language} | {declared} | {p.status} | {lat} | {sha} "
                f"| {summ} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
