"""Research-reporting eligibility: may a stored experiment's results appear in a research report?

Eligibility is decided by rules over recorded provenance, never by looking at the results. Every
rule that fails is reported with a reason, so an ineligible run is explained rather than hidden.
Engineering runs (fixtures, test doubles, unpinned models) remain useful for development; they are
simply excluded from reports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ELIGIBILITY_VERSION = "1.0"
MAX_FAILED_FRACTION = 0.05


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    key: str
    revision: str | None
    test_double: bool


@dataclass(frozen=True, slots=True)
class ExperimentFacts:
    status: str
    dataset_kind: str
    dataset_frozen: bool
    total_items: int
    done_items: int
    failed_items: int
    models: tuple[ModelProvenance, ...]
    config_hash: str | None
    environment_recorded: bool = False


@dataclass(frozen=True, slots=True)
class Rule:
    key: str
    ok: bool
    reason: str


@dataclass(frozen=True, slots=True)
class Eligibility:
    eligible: bool
    version: str
    rules: tuple[Rule, ...] = field(default_factory=tuple)

    @property
    def blocking(self) -> list[str]:
        return [r.reason for r in self.rules if not r.ok]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "version": self.version,
            "rules": [asdict(r) for r in self.rules],
            "blocking": self.blocking,
        }


def assess(f: ExperimentFacts) -> Eligibility:
    doubles = sorted(m.key for m in f.models if m.test_double)
    unpinned = sorted(m.key for m in f.models if not m.test_double and not m.revision)
    failed_frac = f.failed_items / f.done_items if f.done_items else 0.0
    rules = (
        Rule("completed", f.status == "completed", f"run status is '{f.status}', not completed"),
        Rule(
            "all_items_done",
            f.total_items > 0 and f.done_items == f.total_items,
            f"{f.done_items}/{f.total_items} items processed",
        ),
        Rule(
            "evaluation_dataset",
            f.dataset_kind == "evaluation",
            f"dataset kind is '{f.dataset_kind}'; only evaluation datasets are reportable",
        ),
        Rule("frozen_dataset", f.dataset_frozen, "dataset version is not frozen"),
        Rule(
            "no_test_doubles",
            not doubles,
            f"test doubles used: {', '.join(doubles)}",
        ),
        Rule(
            "pinned_revisions",
            not unpinned,
            f"models without a pinned revision: {', '.join(unpinned)}",
        ),
        Rule(
            "failure_rate",
            failed_frac <= MAX_FAILED_FRACTION,
            f"{failed_frac:.1%} of items failed (limit {MAX_FAILED_FRACTION:.0%})",
        ),
        Rule("config_hash", bool(f.config_hash), "no configuration hash recorded"),
        Rule(
            "environment",
            f.environment_recorded,
            "no environment metadata recorded for the run",
        ),
    )
    return Eligibility(all(r.ok for r in rules), ELIGIBILITY_VERSION, rules)
