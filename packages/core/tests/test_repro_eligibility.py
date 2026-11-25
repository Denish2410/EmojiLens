"""Eligibility rules over constructed provenance facts (inputs to a pure function)."""

from __future__ import annotations

from dataclasses import replace

from emojilens_core.repro.eligibility import ExperimentFacts, ModelProvenance, assess

GOOD = ExperimentFacts(
    status="completed",
    dataset_kind="evaluation",
    dataset_frozen=True,
    total_items=100,
    done_items=100,
    failed_items=2,
    models=(ModelProvenance("embed", "abc123", False),),
    config_hash="f" * 64,
    environment_recorded=True,
)


def failing(f: ExperimentFacts) -> set[str]:
    return {r.key for r in assess(f).rules if not r.ok}


def test_fully_provenanced_run_is_eligible() -> None:
    result = assess(GOOD)
    assert result.eligible
    assert result.blocking == []


def test_each_rule_blocks_on_its_own() -> None:
    assert failing(replace(GOOD, status="interrupted")) == {"completed"}
    assert failing(replace(GOOD, done_items=99, failed_items=0)) == {"all_items_done"}
    assert failing(replace(GOOD, dataset_kind="synthetic_fixture")) == {"evaluation_dataset"}
    assert failing(replace(GOOD, dataset_frozen=False)) == {"frozen_dataset"}
    assert failing(replace(GOOD, models=(ModelProvenance("td", "x", True),))) == {"no_test_doubles"}
    assert failing(replace(GOOD, models=(ModelProvenance("embed", None, False),))) == {
        "pinned_revisions"
    }
    assert failing(replace(GOOD, failed_items=6)) == {"failure_rate"}
    assert failing(replace(GOOD, config_hash=None)) == {"config_hash"}
    assert failing(replace(GOOD, environment_recorded=False)) == {"environment"}


def test_blocking_reasons_name_the_offending_models() -> None:
    f = replace(
        GOOD, models=(ModelProvenance("td-a", "x", True), ModelProvenance("m", None, False))
    )
    reasons = " ".join(assess(f).blocking)
    assert "td-a" in reasons
    assert "m" in reasons
    assert assess(f).to_dict()["eligible"] is False
