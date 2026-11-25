"""Preflight and environment-metadata tests. Environments here are constructed inputs to a pure
check function, not records of any real machine."""

from __future__ import annotations

import getpass
import json
import socket
from pathlib import Path
from typing import Any

from emojilens_core.repro import environment_metadata, preflight_checks, summarize


def m4_env(**over: Any) -> dict[str, Any]:
    env: dict[str, Any] = {
        "python": "3.11.9",
        "os": "Darwin",
        "machine": "arm64",
        "apple_silicon": True,
        "torch": {"installed": True, "mps_available": True, "cuda_available": False},
        "resources": {"available_ram_gb": None, "free_disk_gb": 120.0},
        "packages": {
            "torch": "2.5.1",
            "transformers": "4.46.0",
            "sentence_transformers": "3.2.1",
            "huggingface_hub": "0.26.0",
        },
        "tesseract": {"installed": True, "version": "5.5.0", "languages": ["eng", "guj", "hin"]},
        "chromium": {"playwright_installed": True},
        "git": {"commit": "a" * 40, "dirty": False},
    }
    env.update(over)
    return env


def by_name(env: dict[str, Any], **kw: Any) -> dict[str, str]:
    return {c.name: c.status for c in preflight_checks(env, **kw)}


def test_ready_m4_passes_with_unknown_ram_skipped() -> None:
    pins = {"embed-multilingual-minilm": {"revision": "b" * 40}}
    checks = preflight_checks(m4_env(), pins=pins)
    status = {c.name: c.status for c in checks}
    assert status["ram"] == "skip"  # macOS RAM is reported unknown, never guessed
    assert status["huggingface.co"] == "skip"  # no network unless asked
    assert summarize(checks) == "pass"


def test_missing_model_stack_is_a_required_failure() -> None:
    env = m4_env(
        torch={"installed": False},
        packages={"torch": None, "transformers": None},
    )
    status = by_name(env)
    assert status["torch"] == "fail"
    assert status["transformers"] == "fail"
    assert summarize(preflight_checks(env)) == "fail"


def test_missing_gujarati_ocr_pack_warns() -> None:
    env = m4_env(tesseract={"installed": True, "version": "5", "languages": ["eng", "hin"]})
    checks = preflight_checks(env, pins={"x": {"revision": "c"}})
    tess = next(c for c in checks if c.name == "tesseract")
    assert tess.status == "warn"
    assert "guj" in tess.detail
    assert summarize(checks) == "warn"


def test_non_apple_machine_and_missing_mps_only_warn() -> None:
    env = m4_env(apple_silicon=False, os="Linux", machine="x86_64")
    assert by_name(env)["apple_silicon"] == "warn"
    no_mps = m4_env(torch={"installed": True, "mps_available": False})
    assert by_name(no_mps)["torch"] == "warn"


def test_low_disk_fails() -> None:
    assert by_name(m4_env(resources={"available_ram_gb": 8, "free_disk_gb": 2.0}))["disk"] == "fail"


def test_environment_metadata_is_shareable() -> None:
    root = Path(__file__).resolve().parents[3]
    env = environment_metadata(root)
    assert env["python"].startswith("3.")
    assert set(env["packages"]) >= {"numpy", "torch", "transformers"}
    raw = json.dumps(env)
    assert str(Path.home()) not in raw
    assert str(root) not in raw
    assert socket.gethostname() not in raw
    assert f'"{getpass.getuser()}"' not in raw
