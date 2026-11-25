"""Research report built only from stored outputs of eligible runs.

The report never computes new metrics and never includes an ineligible run's numbers. Ineligible
runs are listed with their blocking reasons, so the reader can see what was excluded and why.
When no run is eligible, the report says so and contains no results.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from emojilens_api.db.models import Experiment, MetricResult, ModelOutput, ModelVersion, Source
from emojilens_api.services.provenance import eligibility, manifest
from emojilens_core.models import ModelRegistry

REPORT_SCHEMA = "emojilens.report/1"


def _cell(text: object) -> str:
    """User-supplied text (run names, reasons) as a single inert Markdown table cell."""
    flat = " ".join(str(text).split())
    return flat.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;")


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def build_report(session: Session, registry: ModelRegistry) -> dict[str, Any]:
    experiments = session.scalars(select(Experiment).order_by(Experiment.id)).all()
    screened = []
    eligible_ids: list[int] = []
    for e in experiments:
        el = eligibility(session, registry, e)
        screened.append(
            {
                "id": e.id,
                "name": e.name,
                "status": e.status,
                "eligible": el.eligible,
                "blocking": el.blocking,
            }
        )
        if el.eligible:
            eligible_ids.append(e.id)

    included = []
    for exp_id in eligible_ids:
        exp = session.get(Experiment, exp_id)
        assert exp is not None
        man = manifest(session, registry, exp)
        rows = session.execute(
            select(
                ModelVersion.key,
                Source.language,
                ModelOutput.modality,
                ModelOutput.capability,
                ModelOutput.error,
            )
            .join(ModelVersion, ModelVersion.id == ModelOutput.model_version_id)
            .join(Source, Source.id == ModelOutput.source_id)
            .where(ModelOutput.experiment_id == exp_id)
        ).all()
        counts: Counter[tuple[str, str, str, str]] = Counter()
        errors: Counter[tuple[str, str, str, str]] = Counter()
        for key, lang, modality, cap, err in rows:
            counts[(key, lang, modality, cap)] += 1
            errors[(key, lang, modality, cap)] += 1 if err else 0
        metrics = session.scalars(
            select(MetricResult)
            .where(MetricResult.experiment_id == exp_id)
            .order_by(MetricResult.metric, MetricResult.model, MetricResult.stratum)
        ).all()
        included.append(
            {
                "manifest": man,
                "outputs": [
                    {
                        "model": k[0],
                        "language": k[1],
                        "modality": k[2],
                        "capability": k[3],
                        "n": n,
                        "errors": errors[k],
                    }
                    for k, n in sorted(counts.items())
                ],
                "metrics": [
                    {
                        "crsc_version": m.crsc_version,
                        "metric": m.metric,
                        "model": m.model,
                        "stratum": m.stratum,
                        "stratum_value": m.stratum_value,
                        "value": m.value,
                        "ci_low": m.ci_low,
                        "ci_high": m.ci_high,
                        "n": m.n,
                        "n_groups": m.n_groups,
                    }
                    for m in metrics
                ],
            }
        )
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "screened": screened,
        "included": included,
    }


def render_markdown(report: dict[str, Any]) -> str:
    out = [
        "# EmojiLens research report",
        "",
        f"Generated {report['generated_at']} from stored outputs. Only runs that pass every "
        "eligibility rule (`emojilens_core.repro.eligibility`) contribute numbers. CRSC-sem and "
        "CRSC-safe are **experimental** metrics and are reported separately.",
        "",
        "## Screening",
        "",
    ]
    if not report["screened"]:
        out += ["No experiments are stored.", ""]
    else:
        out += ["| Run | Status | Eligible | Blocking reasons |", "|---|---|---|---|"]
        for s in report["screened"]:
            reasons = "; ".join(s["blocking"]) or "—"
            out.append(
                f"| #{s['id']} {_cell(s['name'])} | {s['status']} "
                f"| {'yes' if s['eligible'] else 'no'} | {_cell(reasons)} |"
            )
        out.append("")
    if not report["included"]:
        out += [
            "## Results",
            "",
            "**No eligible runs. This report contains no results.**",
            "",
        ]
        return "\n".join(out)
    for inc in report["included"]:
        m = inc["manifest"]
        e, d = m["experiment"], m["dataset"]
        out += [
            f"## Run #{e['id']}: {_cell(e['name'])}",
            "",
            f"- Config hash `{e['config_hash']}`; outputs digest `{m['outputs']['sha256']}` "
            f"({m['outputs']['count']} outputs)",
            f"- Dataset `{d['slug']}` v{d['version']} (`{d['content_sha256'][:16]}…`, "
            f"split seed {d['split_seed']})",
            "- Models: "
            + ", ".join(
                f"{x['key']}@{(x['revision'] or '')[:12]} on {x['device']}" for x in m["models"]
            ),
            f"- Code: {m['run_environments'][0]['git'].get('commit') or 'unknown'}",
            "",
            "### Outputs",
            "",
            "| Model | Language | Modality | Capability | n | Errors |",
            "|---|---|---|---|---|---|",
            *[
                f"| {o['model']} | {o['language']} | {o['modality']} | {o['capability']} "
                f"| {o['n']} | {o['errors']} |"
                for o in inc["outputs"]
            ],
            "",
            "### Stored CRSC results (experimental)",
            "",
        ]
        if not inc["metrics"]:
            out += ["No CRSC results were computed for this run.", ""]
        else:
            out += [
                "| Metric | Model | Stratum | Value | 95% CI | n | groups |",
                "|---|---|---|---|---|---|---|",
                *[
                    f"| {r['metric']} v{r['crsc_version']} | {r['model']} "
                    f"| {r['stratum']}={r['stratum_value']} | {_fmt(r['value'])} "
                    f"| [{_fmt(r['ci_low'])}, {_fmt(r['ci_high'])}] | {r['n']} | {r['n_groups']} |"
                    for r in inc["metrics"]
                ],
                "",
            ]
    return "\n".join(out)
