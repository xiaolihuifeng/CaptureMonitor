#!/usr/bin/env python3
"""Generate CaptureMonitor app icons (Pillow + stdlib only).

Outputs:
    assets/icon.png  256x256 PNG
    assets/icon.ico  multi-size ICO [16, 32, 48, 64, 128, 256]

Design: dark rounded-square background with a cyan "capture frame"
glyph (rounded-rectangle lens + viewfinder corner marks).

Usage:
    python3 tools/make_icon.py

Deterministic: same input always yields the same output bytes.
No network access required.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

BASE_SIZE = 256
SS = 4  # supersampling factor for anti-aliased rendering
ICO_SIZES = [16, 32, 48, 64, 128, 256]

# Palette
BG_TOP = (47, 54, 72, 255)      # dark slate top
BG_BOTTOM = (23, 27, 38, 255)   # darker slate bottom
FRAME_COLOR = (94, 224, 255, 255)   # cyan
BODY_COLOR = (226, 234, 246, 255)   # off-white
LENS_RING = (94, 224, 255, 255)     # cyan
LENS_INNER = (30, 38, 54, 255)      # dark lens glass


def _v_gradient(size: int) -> Image.Image:
    """Vertical gradient background image, size x size."""
    img = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    top = BG_TOP
    bottom = BG_BOTTOM
    for y in range(size):
        t = y / max(size - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        draw.line([(0, y), (size - 1, y)], fill=color, width=1)
    return img


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_icon(size: int = BASE_SIZE) -> Image.Image:
    """Render the icon at the given size (drawn with SS supersampling)."""
    s = size * SS
    img = _v_gradient(s)
    draw = ImageDraw.Draw(img)

    def sc(v: float) -> int:
        return int(round(v * SS))

    # --- dark rounded-square background ---
    _rounded_rect(
        draw,
        (0, 0, s - 1, s - 1),
        radius=sc(size * 0.22),
        fill=None,
        outline=(60, 68, 88, 255),
        width=sc(2),
    )

    # --- viewfinder corner marks (capture frame) ---
    corner_len = sc(size * 0.085)
    corner_w = sc(size * 0.028)
    margin = sc(size * 0.10)
    pts = [
        (margin, margin),
        (s - margin, margin),
        (margin, s - margin),
        (s - margin, s - margin),
    ]
    for cx, cy in pts:
        # horizontal segment
        draw.rectangle(
            [cx, cy, cx + corner_len, cy + corner_w],
            fill=FRAME_COLOR,
        )
        # vertical segment
        draw.rectangle(
            [cx, cy, cx + corner_w, cy + corner_len],
            fill=FRAME_COLOR,
        )

    # --- camera body (rounded rectangle) ---
    body_w = sc(size * 0.46)
    body_h = sc(size * 0.30)
    body_x0 = (s - body_w) // 2
    body_y0 = (s - body_h) // 2 + sc(size * 0.02)
    body_box = (body_x0, body_y0, body_x0 + body_w, body_y0 + body_h)
    _rounded_rect(draw, body_box, radius=sc(size * 0.055), fill=BODY_COLOR)

    # top viewfinder bump
    bump_w = sc(size * 0.14)
    bump_h = sc(size * 0.075)
    bump_x0 = (s - bump_w) // 2
    bump_y0 = body_y0 - bump_h + sc(size * 0.012)
    _rounded_rect(
        draw,
        (bump_x0, bump_y0, bump_x0 + bump_w, body_y0 + sc(size * 0.02)),
        radius=sc(size * 0.035),
        fill=BODY_COLOR,
    )

    # --- lens ---
    lens_r = sc(size * 0.105)
    lens_cx = s // 2
    lens_cy = (body_y0 * 2 + body_h) // 2
    ring_box = (
        lens_cx - lens_r,
        lens_cy - lens_r,
        lens_cx + lens_r,
        lens_cy + lens_r,
    )
    draw.ellipse(ring_box, fill=LENS_RING)
    inner_r = int(lens_r * 0.68)
    inner_box = (
        lens_cx - inner_r,
        lens_cy - inner_r,
        lens_cx + inner_r,
        lens_cy + inner_r,
    )
    draw.ellipse(inner_box, fill=LENS_INNER)
    # lens highlight
    hl_r = int(inner_r * 0.32)
    draw.ellipse(
        (lens_cx - int(inner_r * 0.45), lens_cy - int(inner_r * 0.55),
         lens_cx - int(inner_r * 0.45) + hl_r * 2, lens_cy - int(inner_r * 0.55) + hl_r * 2),
        fill=(126, 218, 255, 255),
    )

    # --- clip to rounded-square so corners are transparent ---
    mask = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        (0, 0, s - 1, s - 1),
        radius=sc(size * 0.24),
        fill=255,
    )
    img.putalpha(mask)

    if SS != 1:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    icon = draw_icon(BASE_SIZE)

    png_path = ASSETS_DIR / "icon.png"
    icon.save(png_path, format="PNG", optimize=False)
    print(f"Wrote {png_path} ({icon.size[0]}x{icon.size[1]})")

    ico_path = ASSETS_DIR / "icon.ico"
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(sz, sz) for sz in ICO_SIZES],
    )
    print(f"Wrote {ico_path} (sizes: {ICO_SIZES})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
