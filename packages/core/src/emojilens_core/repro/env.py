"""Environment metadata and preflight checks for the M4 validation workflow.

Everything recorded here is safe to commit or share: versions, booleans, counts and coarse
hardware facts. Absolute paths, user names, hostnames and environment values are never
recorded. Network reachability is probed only when explicitly requested.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from emojilens_core.models.device import resources, select_device

# Python packages whose versions affect results, with their distribution names.
PACKAGES: tuple[tuple[str, str], ...] = (
    ("emojilens_core", "emojilens-core"),
    ("numpy", "numpy"),
    ("sklearn", "scikit-learn"),
    ("torch", "torch"),
    ("transformers", "transformers"),
    ("sentence_transformers", "sentence-transformers"),
    ("huggingface_hub", "huggingface-hub"),
    ("tokenizers", "tokenizers"),
    ("playwright", "playwright"),
)
PROJECT_OCR_LANGS = ("eng", "hin", "guj")


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail" | "skip"
    detail: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _version(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def _run(*args: str) -> str:
    try:
        out = subprocess.run(list(args), capture_output=True, text=True, timeout=20, check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (out.stdout + out.stderr).strip()


def tesseract_info() -> dict[str, Any]:
    binary = shutil.which("tesseract")
    if not binary:
        return {"installed": False, "version": None, "languages": []}
    first = _run(binary, "--version").splitlines()
    langs = _run(binary, "--list-langs").splitlines()[1:]
    return {
        "installed": True,
        "version": first[0].removeprefix("tesseract ").strip() if first else None,
        "languages": sorted(x.strip() for x in langs if x.strip() and " " not in x.strip()),
    }


def git_info(root: Path) -> dict[str, Any]:
    git = shutil.which("git")
    if not git or not (root / ".git").exists():
        return {"commit": None, "dirty": None}
    commit = _run(git, "-C", str(root), "rev-parse", "HEAD") or None
    status = _run(git, "-C", str(root), "status", "--porcelain", "--untracked-files=no")
    return {"commit": commit, "dirty": bool(status)}


def environment_metadata(
    root: Path | None = None, device_preference: str = "auto"
) -> dict[str, Any]:
    """A shareable snapshot of the software and hardware a run used."""
    choice = select_device(device_preference)
    res = resources()
    torch_meta: dict[str, Any] = {"installed": importlib.util.find_spec("torch") is not None}
    if torch_meta["installed"]:
        import torch

        torch_meta["mps_available"] = bool(
            getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        )
        torch_meta["cuda_available"] = bool(torch.cuda.is_available())
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "os": platform.system(),
        "os_release": platform.release().split("-")[0],
        "machine": platform.machine(),
        "apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
        "device": {"selected": choice.device, "reason": choice.reason},
        "torch": torch_meta,
        "resources": {
            "available_ram_gb": None
            if res.available_ram_gb is None
            else round(res.available_ram_gb, 1),
            "free_disk_gb": res.free_disk_gb,
        },
        "packages": {name: _version(dist) for name, dist in PACKAGES},
        "tesseract": tesseract_info(),
        "chromium": {"playwright_installed": importlib.util.find_spec("playwright") is not None},
        "git": git_info(root) if root else {"commit": None, "dirty": None},
    }


def _probe(url: str) -> str | None:
    """Return None when the host answers at all, else a short reason. Sends a HEAD request."""
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(url, method="HEAD")  # noqa: S310 - fixed https URLs only
        urllib.request.urlopen(req, timeout=8)  # noqa: S310
    except urllib.error.HTTPError:
        return None  # an HTTP status means the host is reachable
    except Exception as exc:
        return type(exc).__name__
    return None


def preflight_checks(
    env: dict[str, Any], *, pins: dict[str, Any] | None = None, network: bool = False
) -> list[Check]:
    """Evaluate an environment snapshot against the M4 validation requirements."""
    checks: list[Check] = []
    py = tuple(int(x) for x in env["python"].split(".")[:2])
    checks.append(
        Check("python", "pass" if py >= (3, 11) else "fail", f"Python {env['python']}", True)
    )
    checks.append(
        Check(
            "apple_silicon",
            "pass" if env["apple_silicon"] else "warn",
            f"{env['os']} {env['machine']}"
            + ("" if env["apple_silicon"] else " (the M4 target is Darwin arm64)"),
            False,
        )
    )
    t = env["torch"]
    if not t["installed"]:
        checks.append(
            Check(
                "torch",
                "fail",
                "torch not installed: uv sync --all-packages --extra models",
                True,
            )
        )
    else:
        mps = t.get("mps_available")
        checks.append(
            Check(
                "torch",
                "pass" if mps or not env["apple_silicon"] else "warn",
                f"torch {env['packages'].get('torch')}; "
                f"MPS {'available' if mps else 'unavailable'}",
                True,
            )
        )
    for pkg in ("transformers", "sentence_transformers", "huggingface_hub"):
        v = env["packages"].get(pkg)
        checks.append(
            Check(pkg, "pass" if v else "fail", v or "not installed (--extra models)", True)
        )
    free = env["resources"]["free_disk_gb"]
    checks.append(
        Check(
            "disk",
            "pass" if free >= 10 else "warn" if free >= 5 else "fail",
            f"{free} GB free (catalogue needs ~3.2 GB; 10 GB recommended)",
            True,
        )
    )
    ram = env["resources"]["available_ram_gb"]
    checks.append(
        Check(
            "ram",
            "skip" if ram is None else "pass" if ram >= 4 else "warn",
            "unknown on this OS (not guessed)" if ram is None else f"{ram} GB available",
            False,
        )
    )
    tess = env["tesseract"]
    if not tess["installed"]:
        checks.append(Check("tesseract", "fail", "tesseract not on PATH", True))
    else:
        missing = [lang for lang in PROJECT_OCR_LANGS if lang not in tess["languages"]]
        checks.append(
            Check(
                "tesseract",
                "warn" if missing else "pass",
                f"{tess['version']}; "
                + (f"missing packs: {', '.join(missing)}" if missing else "eng, hin, guj present"),
                True,
            )
        )
    checks.append(
        Check(
            "playwright",
            "pass" if env["chromium"]["playwright_installed"] else "fail",
            "renderer available" if env["chromium"]["playwright_installed"] else "not installed",
            True,
        )
    )
    pinned = sorted(k for k, v in (pins or {}).items() if isinstance(v, dict) and v.get("revision"))
    checks.append(
        Check(
            "model_pins",
            "pass" if pinned else "warn",
            f"pinned: {', '.join(pinned)}" if pinned else "no pins; run scripts/setup_models.py",
            False,
        )
    )
    g = env["git"]
    checks.append(
        Check(
            "git",
            "skip" if g["commit"] is None else "warn" if g["dirty"] else "pass",
            "not a git checkout"
            if g["commit"] is None
            else f"{g['commit'][:12]}{' (uncommitted changes)' if g['dirty'] else ''}",
            False,
        )
    )
    if network:
        reason = _probe("https://huggingface.co")
        checks.append(
            Check(
                "huggingface.co",
                "pass" if reason is None else "fail",
                "reachable" if reason is None else f"unreachable ({reason})",
                True,
            )
        )
    else:
        checks.append(Check("huggingface.co", "skip", "not probed (pass --network)", False))
    return checks


def summarize(checks: list[Check]) -> str:
    if any(c.required and c.status == "fail" for c in checks):
        return "fail"
    return "warn" if any(c.status in ("warn", "fail") for c in checks) else "pass"
