from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def crop_hands(source: Image.Image) -> Image.Image:
    width, height = source.size
    # Reference photo is low resolution; this crop keeps both hands and removes most face/body.
    box = (
        int(width * 0.24),
        int(height * 0.28),
        int(width * 0.72),
        int(height * 0.77),
    )
    return source.crop(box)


def luminance_alpha(gray: Image.Image, dark_threshold: int, soft_width: int) -> Image.Image:
    arr = np.asarray(gray, dtype=np.int16)
    alpha = np.clip((dark_threshold + soft_width - arr) * 255 / max(1, soft_width), 0, 255).astype(np.uint8)
    return Image.fromarray(alpha, "L")


def remove_small_alpha(alpha: Image.Image, threshold: int) -> Image.Image:
    arr = np.asarray(alpha, dtype=np.uint8)
    arr = np.where(arr >= threshold, arr, 0).astype(np.uint8)
    return Image.fromarray(arr, "L")


def render_variant(crop: Image.Image, size: int, dark_threshold: int, soft_width: int, blur: float, dilate: int) -> Image.Image:
    work = crop.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(work)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    smooth = gray.filter(ImageFilter.GaussianBlur(radius=blur))
    edges = smooth.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges, cutoff=1)
    dark = ImageOps.invert(gray)
    mixed = Image.blend(edges, dark, 0.35)
    mixed = ImageOps.autocontrast(mixed, cutoff=1)

    alpha = luminance_alpha(ImageOps.invert(mixed), dark_threshold, soft_width)
    alpha = remove_small_alpha(alpha, 18)
    for _ in range(dilate):
        alpha = alpha.filter(ImageFilter.MaxFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.35))

    ink = Image.new("RGBA", (size, size), (18, 18, 18, 0))
    ink.putalpha(alpha)
    bbox = ink.getbbox()
    if bbox:
        pad = 70
        cropped = ink.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(size, bbox[2] + pad),
                min(size, bbox[3] + pad),
            )
        )
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        canvas.alpha_composite(cropped, ((size - cropped.width) // 2, (size - cropped.height) // 2))
        ink = canvas
    return ink


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 48
    cols = 3
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile
        y0 = (idx // cols) * (tile + label_h)
        sheet.paste(preview, (x0 + (tile - preview.width) // 2, y0 + (tile - preview.height) // 2))
        draw.text((x0 + 12, y0 + tile + 12), path.stem[:38], fill=(0, 0, 0))
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert the Kangkang gekokujo reference photo into monochrome print candidates.")
    parser.add_argument("--source", type=Path, default=ROOT / "参考图" / "zmjjkk_gekokujo_reference.jpg")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--size", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGB")
    crop = crop_hands(source)
    out_dir = ROOT / "印花图_透明底" / f"康康参考图转黑白灰手势印花_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    crop.save(out_dir / "_crop_reference.jpg", quality=94)

    variants = [
        ("01_soft_engraving", 116, 88, 0.9, 0),
        ("02_bold_ink", 132, 70, 0.6, 1),
        ("03_high_contrast", 148, 58, 0.45, 1),
        ("04_line_heavy", 160, 46, 0.25, 1),
        ("05_dense_shadow", 122, 55, 0.7, 2),
        ("06_clean_screenprint", 176, 38, 0.2, 2),
    ]
    paths: list[Path] = []
    for name, threshold, soft, blur, dilate in variants:
        image = render_variant(crop, args.size, threshold, soft, blur, dilate)
        path = out_dir / f"{name}.png"
        image.save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, out_dir / "_overview.jpg")
    print(f"Output dir: {out_dir}")
    print(f"Overview: {out_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
