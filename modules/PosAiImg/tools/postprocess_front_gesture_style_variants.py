from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def largest_component(mask: np.ndarray) -> np.ndarray:
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


def crop_to_alpha(img: Image.Image, pad: int = 70, size: int = 1200) -> Image.Image:
    bbox = img.getbbox()
    if bbox:
        img = img.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(img.width, bbox[2] + pad),
                min(img.height, bbox[3] + pad),
            )
        )
    img.thumbnail((int(size * 0.88), int(size * 0.88)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def remove_white_or_black_background(source: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    arr = np.asarray(rgba)
    rgb = arr[..., :3].astype(np.int16)
    alpha = arr[..., 3].astype(np.uint8)
    luma = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)
    chroma = np.max(rgb, axis=2) - np.min(rgb, axis=2)

    # Keep non-background content: gray hands, jewelry, and strong black ink.
    keep = (alpha > 0) & (
        ((luma > 34) & (luma < 238) & (chroma < 80))
        | ((luma < 80) & (chroma < 55))
        | ((luma > 180) & (chroma < 45))
    )
    # Avoid large flat white/black page blocks by keeping the largest non-edge component.
    keep[:4, :] = False
    keep[-4:, :] = False
    keep[:, :4] = False
    keep[:, -4:] = False
    comp = largest_component(keep)
    comp_img = Image.fromarray((comp.astype(np.uint8) * 255), "L")
    comp_img = comp_img.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.6))

    gray = ImageOps.grayscale(rgba)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    content = Image.merge("RGBA", (gray, gray, gray, comp_img))
    return crop_to_alpha(content)


def force_dualtone(source: Image.Image) -> Image.Image:
    img = source.convert("RGBA")
    alpha = img.getchannel("A")
    gray = ImageOps.grayscale(img)
    gray = ImageEnhanceSafe.autocontrast(gray)

    outline = alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(1.0))
    shadow = Image.new("RGBA", img.size, (8, 8, 8, 0))
    shadow.putalpha(outline.point(lambda p: int(p * 0.55)))
    content = Image.merge("RGBA", (gray, gray, gray, alpha.point(lambda p: int(p * 0.96))))
    canvas = Image.new("RGBA", img.size, (255, 255, 255, 0))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(content)
    return canvas


class ImageEnhanceSafe:
    @staticmethod
    def autocontrast(gray: Image.Image) -> Image.Image:
        return ImageOps.autocontrast(gray, cutoff=1)


def make_overview(paths: list[Path], output_path: Path, bg_color: str) -> None:
    tile = 330
    label_h = 48
    cols = len(paths)
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
        draw.text((idx * tile + 12, tile + 12), path.stem[:36], fill=label_color)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    source_dir = ROOT / "印花图_透明底" / "正面不同手势黑白灰高街印花5款_2026-06-13"
    parser = argparse.ArgumentParser(description="Post-process generated different gesture variants into transparent monochrome print candidates.")
    parser.add_argument("--source-dir", type=Path, default=source_dir)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "印花图_透明底" / "不同手势黑白灰高街印花5款_后处理_2026-06-13")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source in sorted(args.source_dir.glob("*.png")):
        image = Image.open(source).convert("RGBA")
        cleaned = remove_white_or_black_background(image)
        final = force_dualtone(cleaned)
        output = args.output_dir / source.name
        final.save(output)
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
