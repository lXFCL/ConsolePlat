from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
OUTPUT_DIR = ROOT / "印花图_透明底" / "首推简约艺术字样稿_2026-06-14"


@dataclass(frozen=True)
class PrintSpec:
    sku: str
    lines: tuple[str, ...]
    font: Path
    fill: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    subtext: str
    style: str


SPECS = [
    PrintSpec(
        "TREND-001",
        ("SLOW", "DAY"),
        FONT_DIR / "bahnschrift.ttf",
        (22, 26, 27, 255),
        (246, 241, 226, 255),
        (181, 55, 48, 255),
        "NO RUSH CLUB",
        "underline",
    ),
    PrintSpec(
        "TREND-002",
        ("慢慢来",),
        FONT_DIR / "msyhbd.ttc",
        (18, 30, 28, 255),
        (249, 245, 232, 255),
        (72, 116, 96, 255),
        "TAKE TIME",
        "corner",
    ),
    PrintSpec(
        "TREND-003",
        ("休日", "計画"),
        FONT_DIR / "YuGothB.ttc",
        (28, 28, 30, 255),
        (245, 241, 231, 255),
        (88, 100, 146, 255),
        "WEEKEND NOTE",
        "side",
    ),
    PrintSpec(
        "TREND-004",
        ("좋은", "하루"),
        FONT_DIR / "malgunbd.ttf",
        (24, 31, 35, 255),
        (250, 246, 236, 255),
        (186, 133, 78, 255),
        "GOOD DAY",
        "dots",
    ),
    PrintSpec(
        "TREND-005",
        ("COAST", "CLUB"),
        FONT_DIR / "ariblk.ttf",
        (20, 24, 28, 255),
        (247, 243, 232, 255),
        (184, 58, 52, 255),
        "SUMMER 86",
        "frame",
    ),
]


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Missing font: {path}")
    return ImageFont.truetype(str(path), size=size)


def fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: Path, max_width: int, max_size: int) -> ImageFont.FreeTypeFont:
    size = max_size
    while size >= 72:
        font = load_font(font_path, size)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=12)
        if box[2] - box[0] <= max_width:
            return font
        size -= 8
    return load_font(font_path, 72)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke: tuple[int, int, int, int],
    stroke_width: int,
    canvas_width: int,
) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = (canvas_width - (box[2] - box[0])) // 2 - box[0]
    draw.text((x, y - box[1]), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
    return (x + box[0], y, x + box[2], y + box[3] - box[1])


def draw_accent(draw: ImageDraw.ImageDraw, style: str, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    cx = (left + right) // 2
    if style == "underline":
        draw.rounded_rectangle((left + 20, bottom + 34, right - 20, bottom + 52), radius=9, fill=color)
    elif style == "corner":
        size = 52
        width = 10
        draw.line((left - 56, top - 34, left - 56 + size, top - 34), fill=color, width=width)
        draw.line((left - 56, top - 34, left - 56, top - 34 + size), fill=color, width=width)
        draw.line((right + 56, bottom + 34, right + 56 - size, bottom + 34), fill=color, width=width)
        draw.line((right + 56, bottom + 34, right + 56, bottom + 34 - size), fill=color, width=width)
    elif style == "side":
        draw.rounded_rectangle((left - 70, top + 18, left - 50, bottom - 14), radius=8, fill=color)
        draw.rounded_rectangle((right + 50, top + 18, right + 70, bottom - 14), radius=8, fill=color)
    elif style == "dots":
        for offset in (-70, 0, 70):
            draw.ellipse((cx + offset - 13, bottom + 30, cx + offset + 13, bottom + 56), fill=color)
    elif style == "frame":
        draw.rounded_rectangle((left - 62, top - 36, right + 62, bottom + 45), radius=28, outline=color, width=9)


def render_print(spec: PrintSpec) -> Path:
    canvas = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    title_font = fit_font(draw, max(spec.lines, key=len), spec.font, 980, 270)
    small_font = load_font(FONT_DIR / "bahnschrift.ttf", 58)
    line_boxes = []
    line_height = 250 if len(spec.lines) > 1 else 300
    total_height = line_height * len(spec.lines) + 90
    y = (canvas.height - total_height) // 2

    for line in spec.lines:
        box = draw_centered_text(draw, y, line, title_font, spec.fill, spec.stroke, 13, canvas.width)
        line_boxes.append(box)
        y += line_height

    text_box = (
        min(box[0] for box in line_boxes),
        min(box[1] for box in line_boxes),
        max(box[2] for box in line_boxes),
        max(box[3] for box in line_boxes),
    )
    sub_box = draw_centered_text(draw, text_box[3] + 74, spec.subtext, small_font, spec.fill, spec.stroke, 4, canvas.width)
    full_box = (
        min(text_box[0], sub_box[0]),
        min(text_box[1], sub_box[1]),
        max(text_box[2], sub_box[2]),
        max(text_box[3], sub_box[3]),
    )
    draw_accent(draw, spec.style, full_box, spec.accent)

    crop = canvas.getbbox()
    if crop:
        pad = 120
        canvas = canvas.crop(
            (
                max(0, crop[0] - pad),
                max(0, crop[1] - pad),
                min(canvas.width, crop[2] + pad),
                min(canvas.height, crop[3] + pad),
            )
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{spec.sku}_{''.join(spec.lines)}.png"
    canvas.save(out)
    return out


def paste_center(base: Image.Image, overlay: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    max_w = x2 - x1
    max_h = y2 - y1
    scale = min(max_w / overlay.width, max_h / overlay.height)
    resized = overlay.resize((int(overlay.width * scale), int(overlay.height * scale)), Image.Resampling.LANCZOS)
    x = x1 + (max_w - resized.width) // 2
    y = y1 + (max_h - resized.height) // 2
    base.alpha_composite(resized, (x, y))


def make_overview(paths: list[Path]) -> Path:
    cell_w, cell_h = 520, 420
    margin = 40
    overview = Image.new("RGBA", (cell_w * 3 + margin * 2, cell_h * len(paths) + margin * 2), (238, 238, 232, 255))
    draw = ImageDraw.Draw(overview)
    label_font = load_font(FONT_DIR / "msyh.ttc", 32)
    labels = [
        "TREND-001 / SLOW DAY",
        "TREND-002 / CHINESE TAKE TIME",
        "TREND-003 / JAPANESE WEEKEND",
        "TREND-004 / KOREAN GOOD DAY",
        "TREND-005 / COAST CLUB",
    ]

    for row, path in enumerate(paths):
        y = margin + row * cell_h
        transparent_preview = Image.new("RGBA", (cell_w, cell_h), (232, 232, 226, 255))
        checker = ImageDraw.Draw(transparent_preview)
        for yy in range(0, cell_h, 40):
            for xx in range(0, cell_w, 40):
                if (xx // 40 + yy // 40) % 2:
                    checker.rectangle((xx, yy, xx + 40, yy + 40), fill=(212, 212, 206, 255))

        white_preview = Image.new("RGBA", (cell_w, cell_h), (248, 248, 244, 255))
        black_preview = Image.new("RGBA", (cell_w, cell_h), (23, 24, 25, 255))
        art = Image.open(path).convert("RGBA")
        paste_center(transparent_preview, art, (80, 78, cell_w - 80, cell_h - 54))
        paste_center(white_preview, art, (80, 78, cell_w - 80, cell_h - 54))
        paste_center(black_preview, art, (80, 78, cell_w - 80, cell_h - 54))

        overview.alpha_composite(transparent_preview, (margin, y))
        overview.alpha_composite(white_preview, (margin + cell_w, y))
        overview.alpha_composite(black_preview, (margin + cell_w * 2, y))
        draw.text((margin + 18, y + 14), labels[row], font=label_font, fill=(40, 40, 38, 255))

    out = OUTPUT_DIR / "_overview.jpg"
    overview.convert("RGB").save(out, quality=92)
    return out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = [render_print(spec) for spec in SPECS]
    overview = make_overview(paths)
    print(f"output_dir={OUTPUT_DIR}")
    print(f"count={len(paths)}")
    print(f"overview={overview}")
    for path in paths:
        print(path.name)


if __name__ == "__main__":
    main()
