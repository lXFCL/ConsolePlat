from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "手写涂鸦短句印花_5款_2026-06-15"
OVERVIEW = OUT_DIR / "_overview.jpg"
PROMPT_DIR = ROOT / "生成提示词"
PROMPT_FILE = PROMPT_DIR / "手写涂鸦短句印花_5款_2026-06-15.txt"
FONT_DIR = Path("C:/Windows/Fonts")


@dataclass(frozen=True)
class DoodleDesign:
    filename: str
    lines: tuple[str, ...]
    font_path: Path
    font_size: int
    fill: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int]
    stroke_width: int
    line_gap: int
    rotation: float
    motif: str
    seed: int


DESIGNS = [
    DoodleDesign(
        filename="01_stay_easy.png",
        lines=("STAY", "EASY"),
        font_path=FONT_DIR / "Inkfree.ttf",
        font_size=238,
        fill=(24, 24, 23, 255),
        accent=(207, 64, 62, 255),
        stroke=(250, 245, 229, 255),
        stroke_width=8,
        line_gap=-18,
        rotation=-4.5,
        motif="stars",
        seed=101,
    ),
    DoodleDesign(
        filename="02_good_day.png",
        lines=("GOOD", "DAY"),
        font_path=FONT_DIR / "segoeprb.ttf",
        font_size=204,
        fill=(20, 21, 23, 255),
        accent=(49, 119, 143, 255),
        stroke=(247, 246, 239, 255),
        stroke_width=7,
        line_gap=-8,
        rotation=3.0,
        motif="smile",
        seed=102,
    ),
    DoodleDesign(
        filename="03_slow_down.png",
        lines=("SLOW", "DOWN"),
        font_path=FONT_DIR / "comicbd.ttf",
        font_size=218,
        fill=(18, 18, 18, 255),
        accent=(65, 132, 78, 255),
        stroke=(250, 243, 230, 255),
        stroke_width=8,
        line_gap=-10,
        rotation=-2.0,
        motif="underline",
        seed=103,
    ),
    DoodleDesign(
        filename="04_little_luck.png",
        lines=("LITTLE", "LUCK"),
        font_path=FONT_DIR / "mvboli.ttf",
        font_size=206,
        fill=(26, 22, 24, 255),
        accent=(183, 86, 128, 255),
        stroke=(249, 244, 233, 255),
        stroke_width=7,
        line_gap=-16,
        rotation=4.0,
        motif="sparkle",
        seed=104,
    ),
    DoodleDesign(
        filename="05_take_it_light.png",
        lines=("TAKE IT", "LIGHT"),
        font_path=FONT_DIR / "segoepr.ttf",
        font_size=194,
        fill=(19, 20, 20, 255),
        accent=(186, 130, 47, 255),
        stroke=(248, 246, 236, 255),
        stroke_width=7,
        line_gap=-2,
        rotation=-3.0,
        motif="corner",
        seed=105,
    ),
]


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.truetype(str(FONT_DIR / "comicbd.ttf"), size=size)


def text_bbox(text: str, font: ImageFont.FreeTypeFont, stroke_width: int) -> tuple[int, int, int, int]:
    probe = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(probe)
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def draw_wobbly_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: tuple[int, int, int, int],
    width: int,
    rng: random.Random,
    steps: int = 18,
) -> None:
    x1, y1 = start
    x2, y2 = end
    points = []
    for index in range(steps + 1):
        t = index / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        wobble = math.sin(t * math.pi * 2.0) * 5 + rng.uniform(-3, 3)
        points.append((int(x), int(y + wobble)))
    draw.line(points, fill=fill, width=width, joint="curve")


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int, int]) -> None:
    points = [(cx, cy - r), (cx + 4, cy - 4), (cx + r, cy), (cx + 4, cy + 4), (cx, cy + r), (cx - 4, cy + 4), (cx - r, cy), (cx - 4, cy - 4)]
    draw.polygon(points, fill=fill)


def add_motif(
    draw: ImageDraw.ImageDraw,
    design: DoodleDesign,
    bbox: tuple[int, int, int, int],
    rng: random.Random,
) -> None:
    left, top, right, bottom = bbox
    center_x = (left + right) // 2
    width = right - left

    if design.motif == "stars":
        for x, y, r in [(left - 72, top + 48, 22), (right + 68, bottom - 60, 18), (center_x + 20, top - 42, 14)]:
            draw_star(draw, x, y, r, design.accent)
        draw.arc((left - 42, bottom + 18, right + 42, bottom + 82), 6, 174, fill=design.accent, width=9)
    elif design.motif == "smile":
        face = (right + 42, top + 18, right + 138, top + 114)
        draw.ellipse(face, outline=design.accent, width=8)
        draw.ellipse((right + 68, top + 48, right + 78, top + 58), fill=design.accent)
        draw.ellipse((right + 102, top + 48, right + 112, top + 58), fill=design.accent)
        draw.arc((right + 68, top + 58, right + 112, top + 92), 8, 172, fill=design.accent, width=6)
        draw_wobbly_line(draw, (left + 18, bottom + 34), (right - 18, bottom + 28), design.accent, 10, rng)
    elif design.motif == "underline":
        draw_wobbly_line(draw, (left - 14, bottom + 44), (right + 12, bottom + 34), design.accent, 13, rng)
        draw_wobbly_line(draw, (left + width // 5, top - 28), (right - width // 5, top - 32), design.accent, 7, rng)
        for x in (left - 50, right + 50):
            draw.ellipse((x - 14, bottom + 22, x + 14, bottom + 50), fill=design.accent)
    elif design.motif == "sparkle":
        for x, y, r in [(left - 54, top + 30, 18), (right + 66, top + 76, 24), (center_x - 8, bottom + 52, 17)]:
            draw_star(draw, x, y, r, design.accent)
        draw.arc((left - 32, bottom + 14, right + 34, bottom + 88), 0, 180, fill=design.accent, width=8)
    elif design.motif == "corner":
        corner = 50
        draw.line((left - 58, top - 34, left - 58 + corner, top - 34), fill=design.accent, width=9)
        draw.line((left - 58, top - 34, left - 58, top - 34 + corner), fill=design.accent, width=9)
        draw.line((right + 58, bottom + 34, right + 58 - corner, bottom + 34), fill=design.accent, width=9)
        draw.line((right + 58, bottom + 34, right + 58, bottom + 34 - corner), fill=design.accent, width=9)
        for x in (left + width // 4, center_x, right - width // 4):
            draw.ellipse((x - 8, top - 44, x + 8, top - 28), fill=design.accent)


def render_design(design: DoodleDesign) -> Path:
    rng = random.Random(design.seed)
    canvas = Image.new("RGBA", (1600, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = load_font(design.font_path, design.font_size)

    line_boxes = [text_bbox(line, font, design.stroke_width) for line in design.lines]
    line_sizes = [(box[2] - box[0], box[3] - box[1]) for box in line_boxes]
    total_height = sum(height for _, height in line_sizes) + design.line_gap * (len(design.lines) - 1)
    y = (canvas.height - total_height) // 2 - 18
    actual_boxes: list[tuple[int, int, int, int]] = []

    for index, (line, (line_w, line_h)) in enumerate(zip(design.lines, line_sizes)):
        x = (canvas.width - line_w) // 2 + rng.randint(-18, 18)
        draw.text(
            (x, y),
            line,
            font=font,
            fill=design.fill,
            stroke_width=design.stroke_width,
            stroke_fill=design.stroke,
        )
        actual_boxes.append((x, y, x + line_w, y + line_h))
        y += line_h + design.line_gap + rng.randint(-3, 4)

    bbox = (
        min(box[0] for box in actual_boxes),
        min(box[1] for box in actual_boxes),
        max(box[2] for box in actual_boxes),
        max(box[3] for box in actual_boxes),
    )
    add_motif(draw, design, bbox, rng)

    alpha = canvas.getchannel("A")
    alpha_bbox = alpha.getbbox()
    if not alpha_bbox:
        raise RuntimeError(f"Empty design: {design.filename}")
    cropped = canvas.crop(alpha_bbox)
    padded = ImageOps.expand(cropped, border=110, fill=(0, 0, 0, 0))
    rotated = padded.rotate(design.rotation, expand=True, resample=Image.Resampling.BICUBIC)
    final_alpha = rotated.getchannel("A")
    final_bbox = final_alpha.getbbox()
    if final_bbox:
        rotated = rotated.crop(final_bbox)
    rotated = ImageOps.expand(rotated, border=44, fill=(0, 0, 0, 0))
    rotated.thumbnail((1300, 1300), Image.Resampling.LANCZOS)

    out_path = OUT_DIR / design.filename
    rotated.save(out_path)
    return out_path


def make_overview(paths: list[Path]) -> None:
    thumbs = []
    for path in paths:
        image = Image.open(path).convert("RGBA")
        preview = Image.new("RGBA", (560, 560), (245, 245, 240, 255))
        image.thumbnail((470, 470), Image.Resampling.LANCZOS)
        x = (preview.width - image.width) // 2
        y = (preview.height - image.height) // 2
        preview.alpha_composite(image, (x, y))
        thumbs.append(preview.convert("RGB"))

    overview = Image.new("RGB", (560 * 5, 620), (232, 232, 226))
    draw = ImageDraw.Draw(overview)
    label_font = ImageFont.truetype(str(FONT_DIR / "segoeui.ttf"), size=28)
    for index, thumb in enumerate(thumbs):
        x = index * 560
        overview.paste(thumb, (x, 0))
        draw.text((x + 24, 572), paths[index].stem, fill=(40, 40, 40), font=label_font)
    overview.save(OVERVIEW, quality=92)


def write_prompt_file() -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "手写涂鸦短句印花 5 款预览",
        "定位：商业 T 恤胸前局部印花，透明底，适合黑色/白色/灰色 T 恤。",
        "共性：短英文短句、手写字体、少量星星/笑脸/下划线/角标，深色主体加浅色描边，局部低饱和点缀色。",
        "",
    ]
    for design in DESIGNS:
        lines.append(f"{design.filename}: {' / '.join(design.lines)}; motif={design.motif}; font={design.font_path.name}")
    PROMPT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [render_design(design) for design in DESIGNS]
    make_overview(paths)
    write_prompt_file()
    print(f"Saved {len(paths)} PNG files to: {OUT_DIR}")
    print(f"Overview: {OVERVIEW}")
    print(f"Prompt notes: {PROMPT_FILE}")


if __name__ == "__main__":
    main()
