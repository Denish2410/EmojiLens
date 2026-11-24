"""Sandboxed text-to-image rendering.

Primary renderer: headless Chromium via Playwright. The text is HTML-escaped and inserted as
the content of a single element, so it is never interpreted as markup. JavaScript is disabled,
a Content-Security-Policy forbids every fetch, and every network request is aborted at the router.
Rendering is deterministic for a fixed configuration, browser build and font set.
Fallback: Pillow (no complex-script shaping guarantee; flagged in provenance).
"""

from __future__ import annotations

import hashlib
import html
import json
import os
from dataclasses import asdict, dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from emojilens_core.unicode import validate_unicode

RENDERER_VERSION = "1.0.0"
DEFAULT_FONTS = (
    "Noto Sans",
    "Noto Sans Devanagari",
    "Noto Sans Gujarati",
    "FreeSans",
    "DejaVu Sans",
    "Noto Color Emoji",
)


@dataclass(frozen=True, slots=True)
class RenderConfig:
    width: int = 900
    font_size: int = 32
    padding: int = 24
    line_height: float = 1.5
    fonts: tuple[str, ...] = DEFAULT_FONTS
    background: str = "#ffffff"
    color: str = "#000000"

    def validate(self) -> None:
        if not (
            200 <= self.width <= 2000 and 10 <= self.font_size <= 96 and 0 <= self.padding <= 200
        ):
            raise ValueError("render config out of bounds")
        for f in self.fonts:
            if not f.replace(" ", "").replace("-", "").isalnum():
                raise ValueError("font names may contain letters, digits, spaces and hyphens only")
        for c in (self.background, self.color):
            if not (
                c.startswith("#")
                and len(c) == 7
                and all(ch in "0123456789abcdefABCDEF" for ch in c[1:])
            ):
                raise ValueError("colors must be #rrggbb")

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RenderResult:
    image_path: str
    image_sha256: str
    width: int
    height: int
    renderer: str
    renderer_version: str
    provenance: dict[str, Any] = field(default_factory=dict)


def build_html(text: str, cfg: RenderConfig) -> str:
    fonts = ", ".join(f"'{f}'" for f in cfg.fonts)
    body = html.escape(text, quote=True)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta http-equiv='Content-Security-Policy' "
        "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
        f"<style>html,body{{margin:0;background:{cfg.background}}}"
        f"#t{{display:inline-block;box-sizing:border-box;width:{cfg.width}px;padding:{cfg.padding}px;"
        f"font-family:{fonts};font-size:{cfg.font_size}px;line-height:{cfg.line_height};color:{cfg.color};"
        "white-space:pre-wrap;overflow-wrap:anywhere;font-kerning:normal}}</style></head>"
        f"<body><div id='t'>{body}</div></body></html>"
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_chromium(text: str, out_dir: Path, cfg: RenderConfig | None = None) -> RenderResult:
    from playwright.sync_api import sync_playwright

    cfg = cfg or RenderConfig()
    cfg.validate()
    validate_unicode(text)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256((cfg.hash() + text).encode()).hexdigest()
    path = out_dir / f"{name}.png"
    blocked: list[str] = []
    executable = os.environ.get("EMOJILENS_CHROMIUM_PATH") or None
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=executable, args=["--disable-gpu", "--font-render-hinting=none"]
        )
        try:
            ctx = browser.new_context(
                viewport={"width": cfg.width, "height": 200},
                device_scale_factor=1,
                java_script_enabled=False,
                offline=True,
            )
            page = ctx.new_page()

            def _block(route: Any) -> None:
                blocked.append(route.request.url[:200])
                route.abort()

            page.route("**/*", _block)
            page.set_content(build_html(text, cfg), wait_until="load")
            page.locator("#t").screenshot(path=str(path), animations="disabled")
            browser_version = browser.version
        finally:
            browser.close()
    from PIL import Image

    with Image.open(path) as im:
        w, h = im.size
    try:
        pw = version("playwright")
    except PackageNotFoundError:
        pw = "unknown"
    return RenderResult(
        image_path=str(path),
        image_sha256=_sha(path),
        width=w,
        height=h,
        renderer="chromium",
        renderer_version=RENDERER_VERSION,
        provenance={
            "browser": browser_version,
            "playwright": pw,
            "config": asdict(cfg),
            "config_hash": cfg.hash(),
            "javascript": False,
            "network_requests_blocked": blocked,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        },
    )


def render_pillow(
    text: str, out_dir: Path, cfg: RenderConfig | None = None, font_path: str | None = None
) -> RenderResult:
    """Fallback renderer. Does NOT shape complex scripts reliably; flagged in provenance."""
    from PIL import Image, ImageDraw, ImageFont

    cfg = cfg or RenderConfig()
    cfg.validate()
    validate_unicode(text)
    out_dir.mkdir(parents=True, exist_ok=True)
    font = (
        ImageFont.truetype(font_path, cfg.font_size)
        if font_path
        else ImageFont.load_default(cfg.font_size)
    )
    lines = text.split("\n") or [""]
    lh = int(cfg.font_size * cfg.line_height)
    img = Image.new("RGB", (cfg.width, cfg.padding * 2 + lh * len(lines)), cfg.background)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((cfg.padding, cfg.padding + i * lh), line, fill=cfg.color, font=font)
    name = hashlib.sha256(("pillow" + cfg.hash() + text).encode()).hexdigest()
    path = out_dir / f"{name}.png"
    img.save(path)
    return RenderResult(
        image_path=str(path),
        image_sha256=_sha(path),
        width=img.width,
        height=img.height,
        renderer="pillow",
        renderer_version=RENDERER_VERSION,
        provenance={
            "config": asdict(cfg),
            "config_hash": cfg.hash(),
            "font": font_path,
            "complex_shaping": False,
        },
    )
