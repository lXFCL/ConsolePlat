from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def adjust_variant(source: Image.Image, name: str) -> Image.Image:
    img = source.convert("RGBA")
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    gray = ImageOps.grayscale(rgb)

    if name == "soft_gray":
        gray = ImageEnhance.Contrast(gray).enhance(0.92)
        gray = ImageEnhance.Brightness(gray).enhance(1.10)
        outline_size, outline_opacity = 9, 0.46
        content_alpha = 0.92
    elif name == "clean_sharp":
        gray = ImageEnhance.Contrast(gray).enhance(1.18)
        gray = gray.filter(ImageFilter.SHARPEN)
        outline_size, outline_opacity = 11, 0.56
        content_alpha = 0.98
    elif name == "high_contrast":
        gray = ImageOps.autocontrast(gray, cutoff=1)
        gray = ImageEnhance.Contrast(gray).enhance(1.38)
        outline_size, outline_opacity = 13, 0.68
        content_alpha = 1.0
    elif name == "bold_outline":
        gray = ImageEnhance.Contrast(gray).enhance(1.05)
        gray = ImageEnhance.Brightness(gray).enhance(1.04)
        outline_size, outline_opacity = 17, 0.78
        content_alpha = 0.96
    elif name == "dark_street":
        gray = ImageOps.autocontrast(gray, cutoff=2)
        gray = ImageEnhance.Contrast(gray).enhance(1.55)
        gray = ImageEnhance.Brightness(gray).enhance(0.86)
        outline_size, outline_opacity = 15, 0.82
        content_alpha = 1.0
    else:
        raise ValueError(name)

    outline = alpha.filter(ImageFilter.MaxFilter(outline_size)).filter(ImageFilter.GaussianBlur(1.35))
    shadow = Image.new("RGBA", img.size, (8, 8, 8, 0))
    shadow.putalpha(outline.point(lambda p: int(p * outline_opacity)))

    arr = np.asarray(gray, dtype=np.uint8)
    content = Image.fromarray(np.dstack([arr, arr, arr, np.asarray(alpha.point(lambda p: int(p * content_alpha)), dtype=np.uint8)]), "RGBA")

    canvas = Image.new("RGBA", img.size, (255, 255, 255, 0))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(content)
    return canvas


def make_overview(paths: list[Path], output_path: Path, bg_color: str) -> None:
    tile = 360
    label_h = 48
    cols = 5
    sheet = Image.new("RGB", (cols * tile, tile + label_h), bg_color)
    draw = ImageDraw.Draw(sheet)
    label_color = (0, 0, 0) if bg_color == "white" else (230, 230, 230)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, bg_color)
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = idx * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((idx * tile + 14, tile + 12), path.stem[:40], fill=label_color)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create 5 similar front-facing monochrome gesture print variants.")
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "印花图_透明底" / "康康以下克上正面黑白手势_final_2026-06-13" / "康康以下克上正面黑白手势.png",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    out_dir = ROOT / "印花图_透明底" / f"正面以下克上双手势相似印花5款_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("01_soft_gray", "soft_gray"),
        ("02_clean_sharp", "clean_sharp"),
        ("03_high_contrast", "high_contrast"),
        ("04_bold_outline", "bold_outline"),
        ("05_dark_street", "dark_street"),
    ]
    paths: list[Path] = []
    for filename, name in variants:
        path = out_dir / f"{filename}.png"
        adjust_variant(source, name).save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, out_dir / "_overview_on_black.jpg", "black")
    make_overview(paths, out_dir / "_overview_on_white.jpg", "white")
    print(f"Output dir: {out_dir}")
    print(f"Black overview: {out_dir / '_overview_on_black.jpg'}")
    print(f"White overview: {out_dir / '_overview_on_white.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
