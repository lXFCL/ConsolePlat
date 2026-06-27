from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import extract_print  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪韩文参考简单局部改款_2026-06-15"


def recolor_region(base: Image.Image, mask: np.ndarray, color: tuple[int, int, int], strength: float = 0.92) -> Image.Image:
    img = base.copy().convert("RGBA")
    arr = np.asarray(img).copy()
    alpha = arr[..., 3].astype(np.float32) / 255.0
    shade = np.clip(arr[..., :3].mean(axis=2).astype(np.float32) / 145.0, 0.62, 1.18)
    target = np.zeros_like(arr[..., :3], dtype=np.float32)
    for idx, value in enumerate(color):
        target[..., idx] = np.clip(value * shade, 0, 255)
    blend = (mask.astype(np.float32) * alpha * strength)[..., None]
    arr[..., :3] = np.clip(arr[..., :3] * (1.0 - blend) + target * blend, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def cat_fill_mask(base: Image.Image) -> np.ndarray:
    arr = np.asarray(base.convert("RGBA"))
    alpha = arr[..., 3] > 40
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    gray = alpha & (r > 75) & (r < 180)
    gray &= (np.abs(r.astype(np.int16) - g.astype(np.int16)) < 22)
    gray &= (np.abs(g.astype(np.int16) - b.astype(np.int16)) < 22)
    # Keep the Korean text out of body recolors.
    yy = np.indices(gray.shape)[0]
    gray &= yy > 245
    return gray


def fish_mask(base: Image.Image) -> Image.Image:
    arr = np.asarray(base.convert("RGBA"))
    alpha = arr[..., 3] > 25
    yy, xx = np.indices(alpha.shape)
    # Rotated band around the original fish. This catches the fish and its black outline,
    # while avoiding most of the cat body and Korean text.
    x0, y0 = 498.0, 590.0
    angle = math.radians(-42.0)
    xr = (xx - x0) * math.cos(angle) - (yy - y0) * math.sin(angle)
    yr = (xx - x0) * math.sin(angle) + (yy - y0) * math.cos(angle)
    band = (xr > -32) & (xr < 360) & (np.abs(yr) < 48)
    band &= yy > 390
    mask = alpha & band
    img = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    return img.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(0.6))


def clear_mask(base: Image.Image, mask: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    arr = np.asarray(img).copy()
    m = np.asarray(mask).astype(np.float32) / 255.0
    arr[..., 3] = np.clip(arr[..., 3].astype(np.float32) * (1.0 - m), 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def restore_paws(base: Image.Image, edited: Image.Image) -> Image.Image:
    out = edited.copy().convert("RGBA")
    src = np.asarray(base.convert("RGBA"))
    dst = np.asarray(out).copy()
    yy, xx = np.indices(src.shape[:2])
    boxes = (
        ((xx >= 360) & (xx <= 515) & (yy >= 550) & (yy <= 690)),
        ((xx >= 575) & (xx <= 680) & (yy >= 500) & (yy <= 630)),
    )
    region = boxes[0] | boxes[1]
    alpha = src[..., 3] > 20
    r, g, b = src[..., 0], src[..., 1], src[..., 2]
    gray_fill = (r > 70) & (r < 185) & (np.abs(r.astype(np.int16) - g.astype(np.int16)) < 28)
    gray_fill &= np.abs(g.astype(np.int16) - b.astype(np.int16)) < 28
    dark_line = (r < 55) & (g < 55) & (b < 55)
    paw = region & alpha & (gray_fill | dark_line)
    dst[paw] = src[paw]
    return Image.fromarray(dst, "RGBA")


def draw_glasses(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.line((316, 353, 397, 357), fill=(16, 16, 16, 255), width=7)
    d.line((492, 353, 626, 348), fill=(16, 16, 16, 255), width=7)
    d.rounded_rectangle((392, 323, 470, 356), radius=13, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.rounded_rectangle((481, 322, 558, 354), radius=13, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.line((468, 340, 482, 339), fill=(18, 18, 18, 255), width=5)
    d.arc((411, 329, 454, 348), 15, 168, fill=(18, 18, 18, 255), width=4)
    d.arc((500, 328, 543, 347), 15, 168, fill=(18, 18, 18, 255), width=4)
    return out


def draw_round_glasses(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.line((318, 351, 390, 350), fill=(16, 16, 16, 255), width=7)
    d.line((558, 348, 626, 346), fill=(16, 16, 16, 255), width=7)
    d.ellipse((391, 319, 469, 362), fill=fill, outline=(18, 18, 18, 255), width=5)
    d.ellipse((480, 317, 558, 360), fill=fill, outline=(18, 18, 18, 255), width=5)
    d.line((466, 339, 482, 338), fill=(18, 18, 18, 255), width=5)
    d.arc((411, 330, 452, 349), 15, 168, fill=(18, 18, 18, 255), width=4)
    d.arc((500, 328, 541, 347), 15, 168, fill=(18, 18, 18, 255), width=4)
    return out


def recolor_fish(base: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    img = base.copy().convert("RGBA")
    arr = np.asarray(img).copy()
    alpha = arr[..., 3] > 25
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    yy, xx = np.indices(alpha.shape)
    x0, y0 = 498.0, 590.0
    angle = math.radians(-42.0)
    xr = (xx - x0) * math.cos(angle) - (yy - y0) * math.sin(angle)
    yr = (xx - x0) * math.sin(angle) + (yy - y0) * math.cos(angle)
    band = (xr > -15) & (xr < 335) & (np.abs(yr) < 36) & (yy > 405)
    bright_fill = (r > 145) & (g > 150) & (b > 145)
    mask = alpha & band & bright_fill
    shade = np.clip(arr[..., :3].mean(axis=2).astype(np.float32) / 205.0, 0.72, 1.08)
    for idx, value in enumerate(color):
        target = np.clip(value * shade, 0, 255)
        arr[..., idx] = np.where(mask, target, arr[..., idx])
    return Image.fromarray(arr, "RGBA")


def draw_phone(base: Image.Image) -> Image.Image:
    img = clear_mask(base, fish_mask(base))
    d = ImageDraw.Draw(img)
    poly = [(424, 668), (653, 442), (690, 480), (462, 706)]
    d.polygon(poly, fill=(245, 246, 244, 255), outline=(18, 18, 18, 255))
    d.line((438, 654, 665, 430), fill=(18, 18, 18, 255), width=8)
    d.line((466, 710, 696, 476), fill=(18, 18, 18, 255), width=8)
    d.line((424, 668, 462, 706), fill=(18, 18, 18, 255), width=8)
    d.line((653, 442, 690, 480), fill=(18, 18, 18, 255), width=8)
    d.rounded_rectangle((644, 464, 663, 482), radius=5, outline=(18, 18, 18, 255), width=4)
    d.line((468, 660, 650, 480), fill=(205, 215, 220, 255), width=4)
    return restore_paws(base, img)


def draw_flower_bunch(base: Image.Image) -> Image.Image:
    img = clear_mask(base, fish_mask(base))
    d = ImageDraw.Draw(img)
    stems = [(446, 682, 626, 475), (453, 688, 656, 492), (438, 664, 600, 453)]
    for x1, y1, x2, y2 in stems:
        d.line((x1, y1, x2, y2), fill=(39, 94, 63, 255), width=6)
    for cx, cy, color in [
        (626, 458, (238, 177, 188, 255)),
        (658, 489, (246, 213, 130, 255)),
        (602, 442, (177, 205, 238, 255)),
    ]:
        for dx, dy in [(0, -13), (12, -3), (8, 12), (-9, 10), (-13, -4)]:
            d.ellipse((cx + dx - 12, cy + dy - 12, cx + dx + 12, cy + dy + 12), fill=color, outline=(18, 18, 18, 255), width=3)
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(245, 238, 188, 255), outline=(18, 18, 18, 255), width=2)
    d.polygon([(419, 665), (456, 690), (431, 713), (397, 686)], fill=(230, 240, 232, 255), outline=(18, 18, 18, 255))
    return restore_paws(base, img)


def draw_pencil(base: Image.Image) -> Image.Image:
    img = clear_mask(base, fish_mask(base))
    d = ImageDraw.Draw(img)
    body = [(421, 663), (650, 435), (681, 466), (452, 694)]
    d.polygon(body, fill=(245, 196, 77, 255), outline=(18, 18, 18, 255))
    d.line((439, 651, 668, 453), fill=(255, 231, 138, 255), width=9)
    d.polygon([(650, 435), (700, 410), (681, 466)], fill=(238, 222, 185, 255), outline=(18, 18, 18, 255))
    d.polygon([(688, 416), (713, 400), (701, 430)], fill=(18, 18, 18, 255))
    d.polygon([(421, 663), (452, 694), (430, 716), (398, 684)], fill=(220, 80, 92, 255), outline=(18, 18, 18, 255))
    return img


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    variants: list[tuple[str, Image.Image]] = []
    variants.append(("01_only_green_glasses", draw_glasses(base, (82, 139, 116, 255))))
    variants.append(("02_only_blue_glasses", draw_glasses(base, (92, 142, 204, 255))))
    variants.append(("03_round_black_glasses", draw_round_glasses(base, (34, 34, 34, 255))))
    variants.append(("04_cat_warm_gray", recolor_region(base, cat_fill_mask(base), (144, 132, 120), 0.72)))
    variants.append(("05_fish_pale_blue", recolor_fish(base, (178, 219, 232))))
    return variants


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 330
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * tile, tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 28, tile - 28), Image.Resampling.LANCZOS)
        x = index * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((index * tile + 12, tile + 11), path.stem[:34], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make five simple local variants from the cat Korean-text print.")
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
