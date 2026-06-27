from __future__ import annotations

import argparse
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "印花图_透明底" / "OpenPose安全动作_IPAdapter黑白灰手势印花四轮_2026-06-13-v4"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "精选清理版_黑白灰手势印花5款_2026-06-13"


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or not mask[y, x]:
                continue
            q: deque[tuple[int, int]] = deque([(y, x)])
            seen[y, x] = True
            comp: list[tuple[int, int]] = []
            while q:
                cy, cx = q.popleft()
                comp.append((cy, cx))
                for ny in range(cy - 1, cy + 2):
                    for nx in range(cx - 1, cx + 2):
                        if ny < 0 or nx < 0 or ny >= h or nx >= w or seen[ny, nx] or not mask[ny, nx]:
                            continue
                        seen[ny, nx] = True
                        q.append((ny, nx))
            comps.append(comp)
    return comps


def clean_alpha(path: Path, output: Path) -> None:
    img = Image.open(path).convert("RGBA")
    arr = np.asarray(img).copy()
    alpha = arr[..., 3]
    mask = alpha > 12
    comps = connected_components(mask)
    if not comps:
        img.save(output)
        return

    comps.sort(key=len, reverse=True)
    keep = np.zeros_like(mask, dtype=bool)
    largest = len(comps[0])
    min_keep = max(2800, int(largest * 0.04))
    for comp in comps:
        if len(comp) < min_keep:
            continue
        ys = [p[0] for p in comp]
        xs = [p[1] for p in comp]
        # Keep meaningful nearby fragments such as separated wrists, but drop tiny corner debris.
        if max(xs) < img.width * 0.12 and max(ys) > img.height * 0.72:
            continue
        for y, x in comp:
            keep[y, x] = True
    arr[..., 3] = np.where(keep, alpha, 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(output)


def make_overview(paths: list[Path], output: Path, bg: str) -> None:
    tile = 330
    label_h = 46
    cols = len(paths)
    sheet = Image.new("RGB", (cols * tile, tile + label_h), bg)
    draw = ImageDraw.Draw(sheet)
    label_color = (0, 0, 0) if bg == "white" else (235, 235, 235)
    for i, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        canvas = Image.new("RGBA", img.size, bg)
        canvas.alpha_composite(img)
        preview = canvas.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = i * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((i * tile + 12, tile + 12), path.stem[:36], fill=label_color)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs: list[Path] = []
    for path in sorted(args.source_dir.glob("*.png")):
        output = args.output_dir / path.name
        clean_alpha(path, output)
        outputs.append(output)
        print(f"saved {output}")
    make_overview(outputs, args.output_dir / "_overview_on_white.jpg", "white")
    make_overview(outputs, args.output_dir / "_overview_on_black.jpg", "black")
    print(f"Output dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
