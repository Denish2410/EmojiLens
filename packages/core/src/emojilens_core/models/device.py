"""Device selection (CPU / Apple Silicon MPS / CUDA) and resource checks. Never assumes CUDA."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceChoice:
    device: str
    reason: str


def torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def select_device(preference: str = "auto") -> DeviceChoice:
    """Pick a device. ``auto`` prefers MPS on Apple Silicon, then CUDA, then CPU."""
    if preference not in ("auto", "cpu", "mps", "cuda"):
        raise ValueError(f"unknown device preference '{preference}'")
    if preference == "cpu":
        return DeviceChoice("cpu", "requested")
    if not torch_available():
        return DeviceChoice("cpu", "torch not installed; CPU-only adapters")
    import torch

    mps = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    cuda = bool(torch.cuda.is_available())
    if preference == "mps":
        return DeviceChoice("mps", "requested") if mps else DeviceChoice("cpu", "MPS unavailable")
    if preference == "cuda":
        return (
            DeviceChoice("cuda", "requested") if cuda else DeviceChoice("cpu", "CUDA unavailable")
        )
    if mps:
        return DeviceChoice("mps", "Apple Silicon MPS available")
    if cuda:
        return DeviceChoice("cuda", "CUDA available")
    return DeviceChoice("cpu", f"no accelerator on {platform.machine()}")


@dataclass(frozen=True, slots=True)
class Resources:
    available_ram_gb: float | None
    free_disk_gb: float
    cache_dir: str


def model_cache_dir() -> Path:
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))


def resources(cache_dir: Path | None = None) -> Resources:
    cache = cache_dir or model_cache_dir()
    probe = cache if cache.exists() else Path.home()
    free_disk = shutil.disk_usage(probe).free / 1e9
    ram: float | None = None
    try:
        ram = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1e9
    except (ValueError, OSError, AttributeError):
        ram = None  # macOS lacks SC_AVPHYS_PAGES; reported as unknown, not guessed
    return Resources(available_ram_gb=ram, free_disk_gb=round(free_disk, 2), cache_dir=str(cache))
