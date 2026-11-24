"""Build CRSC pairs from stored model outputs and persist metric results."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from emojilens_api.db.models import (
    Adjudication,
    Annotation,
    AnnotationTask,
    Experiment,
    MetricResult,
    ModelOutput,
    ModelVersion,
    Source,
    Variant,
)
from emojilens_core.eval import CRSC_VERSION, Pair, cosine, report


def human_status(session: Session, variant_ids: set[int]) -> dict[int, str]:
    """Adjudicated label if present, else unanimous non-unsure label, else 'disagreement'."""
    out: dict[int, str] = {}
    if not variant_ids:
        return out
    tasks = session.execute(
        select(AnnotationTask.id, AnnotationTask.variant_id).where(
            AnnotationTask.variant_id.in_(variant_ids)
        )
    ).all()
    by_task = {t: v for t, v in tasks}
    adjudicated = {
        by_task[t]: lab
        for t, lab in session.execute(
            select(Adjudication.task_id, Adjudication.semantic_label).where(
                Adjudication.task_id.in_(by_task)
            )
        ).all()
    }
    labels: dict[int, set[str]] = defaultdict(set)
    for t, lab in session.execute(
        select(Annotation.task_id, Annotation.semantic_label).where(Annotation.task_id.in_(by_task))
    ).all():
        if lab != "unsure":
            labels[by_task[t]].add(lab)
    for vid in variant_ids:
        if vid in adjudicated:
            out[vid] = adjudicated[vid]
        elif len(labels.get(vid, set())) == 1:
            out[vid] = next(iter(labels[vid]))
        elif labels.get(vid):
            out[vid] = "disagreement"
    return out


def build_pairs(session: Session, exp: Experiment) -> list[Pair]:
    rows = session.execute(
        select(ModelOutput, ModelVersion.key)
        .join(ModelVersion, ModelOutput.model_version_id == ModelVersion.id)
        .where(
            ModelOutput.experiment_id == exp.id, ModelOutput.capability.in_(("EMBED", "CLASSIFY"))
        )
    ).all()
    src: dict[tuple[str, str, int, str], ModelOutput] = {}
    var: dict[tuple[str, str, int, str], list[ModelOutput]] = defaultdict(list)
    for o, key in rows:
        k = (key, o.modality, o.source_id, o.capability)
        if o.variant_id is None:
            src[k] = o
        else:
            var[k].append(o)
    sources = {
        s.id: s
        for s in session.scalars(
            select(Source).where(Source.id.in_({k[2] for k in src} | {k[2] for k in var}))
        )
    }
    vids = {o.variant_id for os in var.values() for o in os if o.variant_id is not None}
    variants = {v.id: v for v in session.scalars(select(Variant).where(Variant.id.in_(vids)))}
    human = human_status(session, vids)

    merged: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for (key, modality, sid, cap), outs in var.items():
        s_out = src.get((key, modality, sid, cap))
        for vo in outs:
            assert vo.variant_id is not None
            m = merged.setdefault((key, modality, sid, vo.variant_id), {})
            if cap == "EMBED":
                usable = (
                    s_out is not None
                    and not s_out.error
                    and not vo.error
                    and isinstance(s_out.raw, list)
                    and isinstance(vo.raw, list)
                )
                m["sem"] = cosine(s_out.raw, vo.raw) if usable and s_out is not None else None
            else:
                m["js"] = None if s_out is None or s_out.error else s_out.safety
                m["jv"] = None if vo.error else vo.safety
    pairs = []
    for (key, modality, sid, vid), m in merged.items():
        s, v = sources[sid], variants[vid]
        pairs.append(
            Pair(
                group=s.source_group,
                language=s.language,
                family=v.families,
                modality=modality,
                model=key,
                sem=m.get("sem"),
                judge_source=m.get("js"),
                judge_variant=m.get("jv"),
                human=human.get(vid, "unannotated"),
                identity=v.families == "identity",
            )
        )
    return pairs


def compute_and_store(session: Session, exp: Experiment, resamples: int, seed: int) -> int:
    pairs = build_pairs(session, exp)
    rep = report(pairs, resamples=resamples, seed=seed)
    session.execute(
        delete(MetricResult).where(
            MetricResult.experiment_id == exp.id, MetricResult.crsc_version == CRSC_VERSION
        )
    )
    n = 0
    for sr in [*rep.overall, *rep.strata]:
        model, _, stratum = sr.stratum.partition(":")
        if sr.stratum == "model":
            model, stratum = sr.value, "overall"
        for metric, res in (("crsc_sem", sr.sem), ("crsc_safe", sr.safe)):
            details = {k: v for k, v in asdict(res).items() if k != "metric"}
            session.add(
                MetricResult(
                    experiment_id=exp.id,
                    crsc_version=CRSC_VERSION,
                    metric=metric,
                    model=model,
                    stratum=stratum,
                    stratum_value=sr.value if stratum != "overall" else "all",
                    value=res.metric.value,
                    ci_low=res.metric.ci_low,
                    ci_high=res.metric.ci_high,
                    n=res.metric.n,
                    n_groups=res.metric.n_groups,
                    details=details,
                    resamples=resamples,
                    seed=seed,
                )
            )
            n += 1
    session.commit()
    return n
