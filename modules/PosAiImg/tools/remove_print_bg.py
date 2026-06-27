from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PRINT_DIR = ROOT / "\u5370\u82b1\u56fe"
OUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95"
EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    connected = np.zeros_like(mask, dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        if mask[0, x]:
            queue.append((0, x))
        if mask[h - 1, x]:
            queue.append((h - 1, x))
    for y in range(1, h - 1):
        if mask[y, 0]:
            queue.append((y, 0))
        if mask[y, w - 1]:
            queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        if connected[y, x] or not mask[y, x]:
            continue
        connected[y, x] = True
        if y > 0:
            queue.append((y - 1, x))
        if y + 1 < h:
            queue.append((y + 1, x))
        if x > 0:
            queue.append((y, x - 1))
        if x + 1 < w:
            queue.append((y, x + 1))
    return connected


def estimate_border_color(rgba: np.ndarray) -> np.ndarray | None:
    border = np.concatenate(
        [
            rgba[0, :, :],
            rgba[-1, :, :],
            rgba[:, 0, :],
            rgba[:, -1, :],
        ],
        axis=0,
    )
    opaque = border[border[:, 3] > 200]
    if opaque.size == 0:
        return None
    return np.median(opaque[:, :3].astype(np.float32), axis=0)


def looks_like_fake_checkerboard(rgba: np.ndarray) -> bool:
    border = np.concatenate(
        [
            rgba[0, :, :],
            rgba[-1, :, :],
            rgba[:, 0, :],
            rgba[:, -1, :],
        ],
        axis=0,
    )
    opaque = border[border[:, 3] > 200]
    if opaque.size == 0:
        return False

    rgb = opaque[:, :3].astype(np.int16)
    spread = np.max(rgb, axis=1) - np.min(rgb, axis=1)
    light_gray = (np.min(rgb, axis=1) >= 224) & (spread < 18)
    if light_gray.mean() < 0.9:
        return False

    luma = rgb.mean(axis=1)
    return np.percentile(luma, 95) - np.percentile(luma, 5) >= 6


def remove_white_bg(path: Path, output_path: Path, threshold: int = 244, color_distance: float = 42.0) -> None:
    img = Image.open(path).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    white = (rgb[..., 0] >= threshold) & (rgb[..., 1] >= threshold) & (rgb[..., 2] >= threshold)
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    white &= spread < 24

    bg_color = estimate_border_color(arr)
    if bg_color is not None:
        distance = np.linalg.norm(rgb.astype(np.float32) - bg_color[None, None, :], axis=2)
        background_like = white | (distance <= color_distance)
        if looks_like_fake_checkerboard(arr):
            neutral = spread < 28
            bright = np.min(rgb, axis=2) >= 224
            background = background_like | (neutral & bright)
        else:
            background = edge_connected(background_like)
    else:
        background = edge_connected(white)

    arr[..., 3] = np.where(background, 0, arr[..., 3])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove near-white backgrounds from print designs.")
    parser.add_argument("--input-dir", type=Path, default=PRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--threshold", type=int, default=244)
    parser.add_argument("--color-distance", type=float, default=42.0)
    args = parser.parse_args()

    files = [p for p in sorted(args.input_dir.iterdir()) if p.suffix.lower() in EXTS]
    exported = 0
    for path in files:
        output_path = args.output_dir / f"{path.stem}_transparent.png"
        remove_white_bg(path, output_path, args.threshold, args.color_distance)
        print(f"Saved {output_path}")
        exported += 1
    print(f"Done. Exported {exported} transparent print(s).")


if __name__ == "__main__":
    main()
