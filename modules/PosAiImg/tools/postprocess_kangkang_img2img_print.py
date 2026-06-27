from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def hand_region_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    skin = (r > 110) & (g > 65) & (b > 45) & (r > b + 18) & (r >= g - 5)
    bright = ((r + g + b) / 3 > 160) & (r > b + 10)
    return skin | bright


def largest_connected_component(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or not mask[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            comp: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                comp.append((cy, cx))
                for ny in (cy - 1, cy, cy + 1):
                    for nx in (cx - 1, cx, cx + 1):
                        if ny < 0 or nx < 0 or ny >= h or nx >= w or seen[ny, nx] or not mask[ny, nx]:
                            continue
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(comp) > len(best):
                best = comp
    out = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        out[y, x] = True
    return out


def make_print(source: Path, output: Path, size: int) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    arr = np.asarray(img)
    mask = largest_connected_component(hand_region_mask(arr))
    mask_img = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    mask_img = mask_img.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(2.5))

    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges, cutoff=1)
    shade = ImageOps.invert(gray)
    ink_strength = Image.blend(edges, shade, 0.42)
    ink_strength = ImageOps.autocontrast(ink_strength, cutoff=1)

    strength_arr = np.asarray(ink_strength, dtype=np.float32)
    mask_arr = np.asarray(mask_img, dtype=np.float32) / 255.0
    alpha = np.clip((strength_arr * 1.35 + 28) * mask_arr, 0, 255).astype(np.uint8)
    alpha = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.35))

    ink = Image.new("RGBA", img.size, (15, 15, 15, 0))
    ink.putalpha(alpha)
    bbox = ink.getbbox()
    if bbox:
        pad = 80
        ink = ink.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(ink.width, bbox[2] + pad),
                min(ink.height, bbox[3] + pad),
            )
        )
    ink.thumbnail((int(size * 0.88), int(size * 0.88)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(ink, ((size - ink.width) // 2, (size - ink.height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 420
    label_h = 48
    sheet = Image.new("RGB", (tile * len(paths), tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = idx * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((idx * tile + 14, tile + 12), path.stem[:40], fill=(0, 0, 0))
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    default_source_dir = ROOT / "印花图_透明底" / "康康参考图img2img黑白灰手势候选_2026-06-13-v2"
    parser = argparse.ArgumentParser(description="Post-process Kangkang img2img candidates into transparent monochrome print assets.")
    parser.add_argument("--source-dir", type=Path, default=default_source_dir)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "印花图_透明底" / "康康以下克上黑白灰手势印花_final_2026-06-13")
    parser.add_argument("--size", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = [
        args.source_dir / "01_pose_preserve_engraving.png",
        args.source_dir / "02_pose_preserve_bold.png",
    ]
    outputs: list[Path] = []
    for idx, source in enumerate(sources, start=1):
        output = args.output_dir / f"{idx:02d}_kangkang_gekokujo_bw_print.png"
        make_print(source, output, args.size)
        outputs.append(output)
        print(f"saved {output}")
    make_overview(outputs, args.output_dir / "_overview.jpg")
    print(f"Output dir: {args.output_dir}")
    print(f"Overview: {args.output_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
