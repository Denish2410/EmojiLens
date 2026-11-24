"""Multimodal processing: sandboxed rendering and text-vs-reading comparison."""

from emojilens_core.multimodal.compare import Comparison, compare, levenshtein, visible_form
from emojilens_core.multimodal.render import (
    RENDERER_VERSION,
    RenderConfig,
    RenderResult,
    build_html,
    render_chromium,
    render_pillow,
)

__all__ = [
    "RENDERER_VERSION",
    "Comparison",
    "RenderConfig",
    "RenderResult",
    "build_html",
    "compare",
    "levenshtein",
    "render_chromium",
    "render_pillow",
    "visible_form",
]
