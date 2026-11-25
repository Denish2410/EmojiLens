"""Research report tests. Runs here use TEST DOUBLES on a synthetic fixture, so none is eligible."""

from __future__ import annotations

from fastapi.testclient import TestClient
from test_experiments_api import body, dataset, run_worker


def test_empty_database_report_states_no_results(client: TestClient) -> None:
    md = client.get("/api/v1/reports/research.md")
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert "No experiments are stored." in md.text
    assert "This report contains no results." in md.text


def test_ineligible_runs_are_screened_but_contribute_nothing(td_client: TestClient) -> None:
    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    run_worker(td_client)
    rep = td_client.get("/api/v1/reports/research").json()
    assert rep["included"] == []
    [screened] = rep["screened"]
    assert screened["id"] == exp["id"]
    assert screened["eligible"] is False
    assert any("test doubles used" in r for r in screened["blocking"])
    md = td_client.get("/api/v1/reports/research.md").text
    assert f"#{exp['id']}" in md
    assert "This report contains no results." in md
    assert "### Outputs" not in md


def test_markdown_renders_an_included_run() -> None:
    """Rendering check on a constructed report structure; these values are not results."""
    from emojilens_api.services.reporting import render_markdown

    report = {
        "generated_at": "2026-11-26T00:00:00+00:00",
        "screened": [
            {"id": 7, "name": "r", "status": "completed", "eligible": True, "blocking": []}
        ],
        "included": [
            {
                "manifest": {
                    "experiment": {"id": 7, "name": "r", "config_hash": "c" * 64},
                    "dataset": {
                        "slug": "d",
                        "version": 1,
                        "content_sha256": "d" * 64,
                        "split_seed": 3,
                    },
                    "models": [{"key": "m", "revision": "r" * 40, "device": "mps"}],
                    "run_environments": [{"git": {"commit": "a" * 40}}],
                    "outputs": {"count": 2, "sha256": "e" * 64},
                },
                "outputs": [
                    {
                        "model": "m",
                        "language": "gu",
                        "modality": "text",
                        "capability": "EMBED",
                        "n": 2,
                        "errors": 0,
                    }
                ],
                "metrics": [
                    {
                        "crsc_version": "0.1",
                        "metric": "crsc_sem",
                        "model": "m",
                        "stratum": "language",
                        "stratum_value": "gu",
                        "value": None,
                        "ci_low": None,
                        "ci_high": None,
                        "n": 2,
                        "n_groups": 1,
                    }
                ],
            }
        ],
    }
    md = render_markdown(report)
    assert "## Run #7: r" in md
    assert "| m | gu | text | EMBED | 2 | 0 |" in md
    assert "| crsc_sem v0.1 | m | language=gu | — | [—, —] | 2 | 1 |" in md
    assert "contains no results" not in md


def test_user_text_cannot_break_report_tables() -> None:
    from emojilens_api.services.reporting import render_markdown

    report = {
        "generated_at": "t",
        "screened": [
            {
                "id": 1,
                "name": "a | b\n# x <img>",
                "status": "queued",
                "eligible": False,
                "blocking": ["r|1"],
            }
        ],
        "included": [],
    }
    md = render_markdown(report)
    row = next(line for line in md.splitlines() if line.startswith("| #1"))
    assert row == "| #1 a \\| b # x &lt;img> | queued | no | r\\|1 |"
