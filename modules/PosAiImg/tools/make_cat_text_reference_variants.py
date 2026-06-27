from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪韩文参考小改动_2026-06-15"


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    connected = np.zeros_like(mask, dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(w):
        if mask[0, x]:
            stack.append((0, x))
        if mask[h - 1, x]:
            stack.append((h - 1, x))
    for y in range(1, h - 1):
        if mask[y, 0]:
            stack.append((y, 0))
        if mask[y, w - 1]:
            stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        if connected[y, x] or not mask[y, x]:
            continue
        connected[y, x] = True
        if y > 0:
            stack.append((y - 1, x))
        if y + 1 < h:
            stack.append((y + 1, x))
        if x > 0:
            stack.append((y, x - 1))
        if x + 1 < w:
            stack.append((y, x + 1))
    return connected


def extract_print(source: Path, size: int) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    w, h = image.size
    crop = image.crop((int(w * 0.285), int(h * 0.395), int(w * 0.710), int(h * 0.735)))
    crop = crop.resize((size, size), Image.Resampling.LANCZOS)

    arr = np.asarray(crop).astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    bright_shirt = (r > 165) & (g > 160) & (b > 148) & ((np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])) < 34)
    background = edge_connected(bright_shirt)

    alpha = np.where(background, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, "L")
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.45))

    rgba = crop.convert("RGBA")
    rgba.putalpha(alpha_img)
    bbox = rgba.getbbox()
    if bbox:
        pad = 28
        rgba = rgba.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(rgba.width, bbox[2] + pad),
                min(rgba.height, bbox[3] + pad),
            )
        )

    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    rgba.thumbnail((int(size * 0.88), int(size * 0.88)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(rgba, ((size - rgba.width) // 2, (size - rgba.height) // 2))
    return canvas


def line_with_outline(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: tuple[int, int, int, int], width: int) -> None:
    draw.line(points, fill=(255, 255, 255, 235), width=width + 7, joint="curve")
    draw.line(points, fill=fill, width=width, joint="curve")


def recolor_gray(base: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    img = base.copy()
    arr = np.asarray(img).copy()
    alpha = arr[..., 3]
    gray_region = (alpha > 20) & (np.abs(arr[..., 0].astype(np.int16) - arr[..., 1].astype(np.int16)) < 18)
    gray_region &= (arr[..., 0] > 65) & (arr[..., 0] < 190)
    shade = arr[..., 0].astype(np.float32) / 128.0
    for idx, value in enumerate(rgb):
        arr[..., idx] = np.where(gray_region, np.clip(value * shade, 0, 255), arr[..., idx])
    return Image.fromarray(arr, "RGBA")


def add_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, fill: tuple[int, int, int, int]) -> None:
    points: list[tuple[float, float]] = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.43
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    draw.polygon(points, fill=fill)


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    variants: list[tuple[str, Image.Image]] = []

    img1 = base.copy()
    d1 = ImageDraw.Draw(img1)
    line_with_outline(d1, [(272, 196), (434, 196), (534, 196)], (21, 21, 21, 255), 7)
    d1.ellipse((247, 187, 264, 204), fill=(21, 21, 21, 255))
    d1.ellipse((544, 187, 561, 204), fill=(21, 21, 21, 255))
    variants.append(("01_text_underline", img1))

    img2 = recolor_gray(base, (91, 103, 96))
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((460, 435, 548, 462), radius=13, fill=(236, 246, 255, 255), outline=(18, 18, 18, 255), width=5)
    d2.line((468, 445, 540, 445), fill=(118, 170, 204, 255), width=4)
    variants.append(("02_blue_fish", img2))

    img3 = base.copy()
    d3 = ImageDraw.Draw(img3)
    d3.rounded_rectangle((322, 323, 391, 349), radius=12, fill=(235, 185, 102, 255), outline=(18, 18, 18, 255), width=5)
    d3.rounded_rectangle((399, 323, 468, 349), radius=12, fill=(235, 185, 102, 255), outline=(18, 18, 18, 255), width=5)
    d3.line((389, 336, 402, 336), fill=(18, 18, 18, 255), width=5)
    variants.append(("03_warm_glasses", img3))

    img4 = base.copy()
    d4 = ImageDraw.Draw(img4)
    add_star(d4, 525, 292, 24, (20, 20, 20, 255))
    add_star(d4, 525, 292, 14, (255, 255, 255, 255))
    add_star(d4, 553, 325, 15, (20, 20, 20, 255))
    add_star(d4, 553, 325, 8, (255, 255, 255, 255))
    variants.append(("04_small_stars", img4))

    img5 = recolor_gray(base, (112, 104, 96))
    d5 = ImageDraw.Draw(img5)
    d5.arc((303, 362, 475, 438), 18, 162, fill=(18, 18, 18, 255), width=7)
    d5.line((310, 389, 295, 376), fill=(18, 18, 18, 255), width=6)
    d5.line((469, 389, 486, 376), fill=(18, 18, 18, 255), width=6)
    variants.append(("05_cat_smile", img5))

    return variants


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 330
    label_h = 44
    cols = len(paths)
    sheet = Image.new("RGB", (cols * tile, tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 26, tile - 26), Image.Resampling.LANCZOS)
        x = i * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((i * tile + 12, tile + 11), path.stem[:34], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make five small edited variants from the cat Korean-text shirt reference.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = extract_print(args.source, args.size)
    base.save(args.output_dir / "_extracted_base.png")
    paths: list[Path] = []
    for name, image in make_variants(base):
        path = args.output_dir / f"{name}.png"
        image.save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, args.output_dir / "_overview.jpg")
    print(f"Output dir: {args.output_dir}")
    print(f"Overview: {args.output_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
