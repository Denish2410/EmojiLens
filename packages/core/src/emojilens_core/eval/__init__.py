"""Evaluation: CRSC consistency metrics (experimental) and statistics."""

from emojilens_core.eval.crsc import (
    CRSC_VERSION,
    CRSCReport,
    Interval,
    Pair,
    SafeResult,
    SemResult,
    cosine,
    crsc_safe,
    crsc_sem,
    group_bootstrap,
    report,
)

__all__ = [
    "CRSC_VERSION",
    "CRSCReport",
    "Interval",
    "Pair",
    "SafeResult",
    "SemResult",
    "cosine",
    "crsc_safe",
    "crsc_sem",
    "group_bootstrap",
    "report",
]
