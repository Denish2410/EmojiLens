"""The config validator accepts the shipped template and rejects unsafe or malformed configs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "freeze_configs.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False, cwd=ROOT
    )


def test_template_is_valid() -> None:
    out = run("validate", "research/configs/templates/h4_crsc_sem_varieties.json")
    assert out.returncode == 0, out.stderr


def test_sentiment_label_map_and_missing_hypothesis_are_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "name": "x",
                "dataset": "d",
                "version": 1,
                "model_keys": ["classifier-xlmr-sentiment"],
                "capabilities": ["CLASSIFY"],
                "label_map": {"negative": "unsafe"},
            }
        )
    )
    out = run("validate", str(bad))
    assert out.returncode == 1
    assert "'hypothesis' is required" in out.stderr
    assert "sentiment model" in out.stderr


def test_lock_is_consistent() -> None:
    assert run("check").returncode == 0
