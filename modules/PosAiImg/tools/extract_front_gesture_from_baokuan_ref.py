from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def crop_print_area(image: Image.Image) -> Image.Image:
    w, h = image.size
    # Crop the chest print area from the provided product reference.
    return image.crop((int(w * 0.29), int(h * 0.36), int(w * 0.73), int(h * 0.63)))


def make_alpha(rgb: np.ndarray, low_cut: int, high_cut: int) -> Image.Image:
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    luma = (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.float32)
    chroma = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    bright_hand = (luma >= low_cut) & (chroma < 70)
    highlight = luma >= high_cut
    alpha = np.where(bright_hand | highlight, np.clip((luma - low_cut) * 255 / max(1, high_cut - low_cut), 0, 255), 0)
    return Image.fromarray(alpha.astype(np.uint8), "L")


def extract_variant(crop: Image.Image, size: int, low_cut: int, high_cut: int, grow: int, feather: float) -> Image.Image:
    work = crop.convert("RGB")
    rgb = np.asarray(work)
    alpha = make_alpha(rgb, low_cut, high_cut)
    for _ in range(grow):
        alpha = alpha.filter(ImageFilter.MaxFilter(3))
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))

    gray = ImageOps.grayscale(work)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    # Convert the printed hands to grayscale ink with enough contrast for black shirts.
    ink_luma = np.asarray(gray, dtype=np.uint8)
    ink_rgb = np.stack([ink_luma, ink_luma, ink_luma], axis=-1)
    rgba = np.dstack([ink_rgb, np.asarray(alpha, dtype=np.uint8)])
    img = Image.fromarray(rgba, "RGBA")

    bbox = img.getbbox()
    if bbox:
        pad = 80
        img = img.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(img.width, bbox[2] + pad),
                min(img.height, bbox[3] + pad),
            )
        )
    img.thumbnail((int(size * 0.96), int(size * 0.96)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 48
    cols = 3
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "black")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile
        y0 = (idx // cols) * (tile + label_h)
        sheet.paste(preview, (x0 + (tile - preview.width) // 2, y0 + (tile - preview.height) // 2))
        draw.text((x0 + 12, y0 + tile + 12), path.stem[:38], fill=(0, 0, 0))
    sheet.save(output_path, quality=94)


def make_white_overview(paths: list[Path], output_path: Path) -> None:
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
    parser = argparse.ArgumentParser(description="Extract front-facing double hand gesture print from a product reference image.")
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "爆款印花知识库" / "爆款1" / "3636a61b5561417c830a0982d6bf42da-goods.jpeg",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--size", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image = ImageOps.exif_transpose(Image.open(args.source)).convert("RGB")
    crop = crop_print_area(image)
    out_dir = ROOT / "印花图_透明底" / f"爆款参考正面双手势印花提取_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    crop.save(out_dir / "_crop_reference.jpg", quality=95)

    variants = [
        ("01_soft_gray", 52, 190, 1, 0.8),
        ("02_clean_gray", 62, 205, 1, 0.5),
        ("03_bright_gray", 74, 218, 1, 0.35),
        ("04_dense_detail", 44, 178, 0, 0.4),
        ("05_bold_visible", 86, 210, 2, 0.5),
        ("06_light_highlight", 100, 230, 2, 0.35),
    ]
    paths: list[Path] = []
    for name, low_cut, high_cut, grow, feather in variants:
        output = out_dir / f"{name}.png"
        extract_variant(crop, args.size, low_cut, high_cut, grow, feather).save(output)
        paths.append(output)
        print(f"saved {output}")
    make_overview(paths, out_dir / "_overview_on_black.jpg")
    make_white_overview(paths, out_dir / "_overview_on_white.jpg")
    print(f"Output dir: {out_dir}")
    print(f"Overview: {out_dir / '_overview_on_black.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
