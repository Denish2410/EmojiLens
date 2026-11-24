"""Model adapter framework: capabilities, registry, device/resources, SafetyJudge."""

from emojilens_core.models.base import ModelAdapter
from emojilens_core.models.device import DeviceChoice, Resources, resources, select_device
from emojilens_core.models.registry import ModelRegistry
from emojilens_core.models.safety import (
    JUDGE_VERSION,
    Judgment,
    ResponseBehavior,
    SafetyJudge,
    SafetyJudgment,
    response_behavior,
)
from emojilens_core.models.types import (
    Availability,
    AvailabilityStatus,
    Capability,
    ErrorCode,
    InferenceResult,
    ModelConfig,
    ModelError,
    ModelMetadata,
    TokenTrace,
)

__all__ = [
    "JUDGE_VERSION",
    "Availability",
    "AvailabilityStatus",
    "Capability",
    "DeviceChoice",
    "ErrorCode",
    "InferenceResult",
    "Judgment",
    "ModelAdapter",
    "ModelConfig",
    "ModelError",
    "ModelMetadata",
    "ModelRegistry",
    "Resources",
    "ResponseBehavior",
    "SafetyJudge",
    "SafetyJudgment",
    "TokenTrace",
    "resources",
    "response_behavior",
    "select_device",
]
