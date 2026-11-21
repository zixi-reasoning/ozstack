#!/usr/bin/env python3
"""Turn a photograph into a one-ink halftone PNG (transparent ground).

The dots sit on a screen rotated 45 degrees by default; each dot's radius
follows the local darkness, so the photograph reads at a distance and the
dot grid shows up close. Output has an alpha channel, so it can be laid
over the site's paper colour.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def parse_crop(value: str | None, width: int, height: int) -> tuple[int, int, int, int]:
    if not value:
        return (0, 0, width, height)
    left, top, right, bottom = (float(part) for part in value.split(","))
    return (
        round(left * width),
        round(top * height),
        round(right * width),
        round(bottom * height),
    )


def make_halftone(
    src: Path,
    out: Path,
    width: int = 1200,
    pitch: float = 12.0,
    angle: float = 45.0,
    ink: str = "#8fa99a",
    crop: str | None = None,
    contrast: float = 1.0,
    gamma: float = 0.85,
    white: float = 0.085,
    fade_left: float = 0.0,
    fade_v: float = 0.0,
    dot: float = 0.74,
    supersample: int = 3,
) -> None:
    photo = ImageOps.exif_transpose(Image.open(src)).convert("L")
    photo = photo.crop(parse_crop(crop, *photo.size))

    height = max(1, round(width * photo.height / photo.width))
    photo = photo.resize((width, height), Image.LANCZOS)
    photo = ImageOps.autocontrast(photo, cutoff=1)
    if contrast != 1.0:
        mid = 128
        photo = photo.point(
            lambda v: max(0, min(255, round((v - mid) * contrast + mid)))
        )
    if gamma != 1.0:
        photo = photo.point(lambda v: round(255 * (v / 255) ** gamma))

    # Sample a blurred copy so each dot takes the tone of its whole cell.
    tone = photo.filter(ImageFilter.GaussianBlur(radius=max(1.0, pitch * 0.45)))

    scale = supersample
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    theta = math.radians(angle)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    cell = pitch * scale
    radius_max = cell * dot
    cx, cy = canvas.width / 2, canvas.height / 2
    steps = int(math.hypot(canvas.width, canvas.height) / cell) + 2
    ink_rgba = (*hex_rgb(ink), 255)

    for row in range(-steps, steps + 1):
        for col in range(-steps, steps + 1):
            x = cx + (col * cos_t - row * sin_t) * cell
            y = cy + (col * sin_t + row * cos_t) * cell
            if not (0 <= x < canvas.width and 0 <= y < canvas.height):
                continue

            gx = min(width - 1, max(0, int(x / scale)))
            gy = min(height - 1, max(0, int(y / scale)))
            darkness = 1.0 - tone.getpixel((gx, gy)) / 255.0
            if darkness < white:
                continue

            radius = radius_max * math.sqrt(darkness)
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=ink_rgba,
            )

    canvas = canvas.resize((width, height), Image.LANCZOS)

    if fade_left > 0 or fade_v > 0:
        import numpy as np

        pixels = np.asarray(canvas).astype(np.float32)
        rows, cols = pixels.shape[:2]
        xs = np.linspace(0.0, 1.0, cols, dtype=np.float32)[None, :]
        ys = np.linspace(0.0, 1.0, rows, dtype=np.float32)[:, None]

        def smooth(t):
            t = np.clip(t, 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)

        fade = np.ones((rows, cols), dtype=np.float32)
        if fade_left > 0:
            fade *= smooth(xs / fade_left)
        if fade_v > 0:
            fade *= smooth(np.minimum(ys, 1.0 - ys) / fade_v)
        pixels[:, :, 3] *= fade
        canvas = Image.fromarray(pixels.clip(0, 255).astype(np.uint8), "RGBA")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".webp":
        canvas.save(out, "WEBP", quality=86, method=6)
    else:
        canvas.save(out, optimize=True)
    print(f"{out}  {canvas.width}x{canvas.height}  pitch={pitch}  ink={ink}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--pitch", type=float, default=12.0)
    parser.add_argument("--angle", type=float, default=45.0)
    parser.add_argument("--ink", default="#8fa99a")
    parser.add_argument(
        "--crop",
        help="left,top,right,bottom as 0-1 fractions of the source",
    )
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.85)
    parser.add_argument("--white", type=float, default=0.085)
    parser.add_argument("--fade-left", type=float, default=0.0)
    parser.add_argument("--fade-v", type=float, default=0.0)
    parser.add_argument("--dot", type=float, default=0.74)
    parser.add_argument("--supersample", type=int, default=3)
    args = parser.parse_args()

    make_halftone(
        args.src,
        args.out,
        width=args.width,
        pitch=args.pitch,
        angle=args.angle,
        ink=args.ink,
        crop=args.crop,
        contrast=args.contrast,
        gamma=args.gamma,
        white=args.white,
        fade_left=args.fade_left,
        fade_v=args.fade_v,
        dot=args.dot,
        supersample=args.supersample,
    )


if __name__ == "__main__":
    main()
