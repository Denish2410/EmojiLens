"""Adversarial transformation engine for controlled, local, defensive evaluation."""

from emojilens_core.transforms.base import (
    ChainResult,
    ChainStep,
    Param,
    StepResult,
    Transform,
    TransformError,
    TransformSpec,
    compose,
    run_chain,
    tiles,
)
from emojilens_core.transforms.families import FAMILIES, REGISTRY, decode_payload

__all__ = [
    "FAMILIES",
    "REGISTRY",
    "ChainResult",
    "ChainStep",
    "Param",
    "StepResult",
    "Transform",
    "TransformError",
    "TransformSpec",
    "compose",
    "decode_payload",
    "run_chain",
    "tiles",
]
