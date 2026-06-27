from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def dualtone(source: Path, output: Path) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    alpha = img.getchannel("A")

    outline = alpha.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(1.4))
    shadow = Image.new("RGBA", img.size, (8, 8, 8, 0))
    shadow.putalpha(outline.point(lambda p: int(p * 0.72)))

    content = Image.new("RGBA", img.size, (238, 238, 238, 0))
    # Keep source grayscale variation so rings and hand shading remain visible.
    gray = ImageOps.grayscale(img)
    content_rgb = Image.merge("RGB", (gray, gray, gray)).convert("RGBA")
    content_rgb.putalpha(alpha.point(lambda p: int(p * 0.96)))

    canvas = Image.new("RGBA", img.size, (255, 255, 255, 0))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(content_rgb)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def make_overview(paths: list[Path], output_path: Path, bg_color: str) -> None:
    tile = 420
    label_h = 48
    sheet = Image.new("RGB", (tile * len(paths), tile + label_h), bg_color)
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
    src_dir = ROOT / "印花图_透明底" / "爆款参考正面双手势印花提取_2026-06-13-v2"
    parser = argparse.ArgumentParser(description="Add dark outline to front-facing gesture prints for black and white shirts.")
    parser.add_argument("--source-dir", type=Path, default=src_dir)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "印花图_透明底" / "正面双手势黑白灰印花_双色可见_final_2026-06-13")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    preferred = [
        args.source_dir / "02_clean_gray.png",
        args.source_dir / "05_bold_visible.png",
    ]
    outputs: list[Path] = []
    for idx, source in enumerate(preferred, start=1):
        output = args.output_dir / f"{idx:02d}_front_double_gesture_dualtone.png"
        dualtone(source, output)
        outputs.append(output)
        print(f"saved {output}")
    make_overview(outputs, args.output_dir / "_overview_on_black.jpg", "black")
    make_overview(outputs, args.output_dir / "_overview_on_white.jpg", "white")
    print(f"Output dir: {args.output_dir}")
    print(f"Black overview: {args.output_dir / '_overview_on_black.jpg'}")
    print(f"White overview: {args.output_dir / '_overview_on_white.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
