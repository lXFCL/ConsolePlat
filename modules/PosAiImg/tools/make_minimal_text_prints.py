from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "简约艺术字文字印花_5款_2026-06-09"
PROMPT_DIR = ROOT / "生成提示词"
PROMPT_FILE = PROMPT_DIR / "简约艺术字文字印花_5款_2026-06-09.txt"


@dataclass(frozen=True)
class TextDesign:
    slug: str
    lines: tuple[str, ...]
    font_path: Path
    font_size: int
    fill: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int] | None = None
    stroke_width: int = 0
    line_gap: int = 16
    tracking: int = 0
    y_shift: int = 0
    style: str = "underline"


FONT_DIR = Path("C:/Windows/Fonts")


DESIGNS = [
    TextDesign(
        slug="01_korean_annyeong",
        lines=("안녕",),
        font_path=FONT_DIR / "malgunbd.ttf",
        font_size=310,
        fill=(18, 18, 18, 255),
        accent=(178, 57, 49, 255),
        stroke=(246, 239, 223, 255),
        stroke_width=10,
        tracking=-4,
        style="dots",
    ),
    TextDesign(
        slug="02_japanese_ii_hi",
        lines=("いい日",),
        font_path=FONT_DIR / "YuGothB.ttc",
        font_size=285,
        fill=(24, 27, 29, 255),
        accent=(71, 96, 139, 255),
        stroke=(246, 246, 241, 255),
        stroke_width=8,
        tracking=2,
        style="thin_frame",
    ),
    TextDesign(
        slug="03_english_slow_day",
        lines=("SLOW", "DAY"),
        font_path=FONT_DIR / "GOTHICB.TTF",
        font_size=215,
        fill=(15, 15, 15, 255),
        accent=(184, 134, 98, 255),
        stroke=(248, 244, 233, 255),
        stroke_width=8,
        line_gap=-8,
        tracking=14,
        style="underline",
    ),
    TextDesign(
        slug="04_chinese_manmanlai",
        lines=("慢慢来",),
        font_path=FONT_DIR / "STKAITI.TTF",
        font_size=300,
        fill=(20, 20, 20, 255),
        accent=(54, 121, 83, 255),
        stroke=(248, 242, 230, 255),
        stroke_width=6,
        tracking=0,
        style="side_marks",
    ),
    TextDesign(
        slug="05_mixed_hello_nihao",
        lines=("HELLO", "你好"),
        font_path=FONT_DIR / "msyhbd.ttc",
        font_size=198,
        fill=(16, 16, 16, 255),
        accent=(150, 49, 58, 255),
        stroke=(244, 244, 238, 255),
        stroke_width=5,
        line_gap=8,
        tracking=10,
        style="corner_marks",
    ),
]


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: int,
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] | None = None,
) -> None:
    x, y = xy
    for char in text:
        draw.text(
            (x, y),
            char,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        box = draw.textbbox((x, y), char, font=font, stroke_width=stroke_width)
        x += (box[2] - box[0]) + tracking


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking: int,
    stroke_width: int,
) -> tuple[int, int]:
    if not text:
        return 0, 0
    widths = []
    heights = []
    for char in text:
        box = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    width = sum(widths) + max(0, len(text) - 1) * tracking
    return width, max(heights)


def add_accents(
    draw: ImageDraw.ImageDraw,
    style: str,
    bbox: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = bbox
    width = right - left
    center_x = (left + right) // 2
    if style == "underline":
        y = bottom + 42
        draw.rounded_rectangle((left + 22, y, right - 22, y + 14), radius=7, fill=accent)
        draw.ellipse((center_x - 11, top - 34, center_x + 11, top - 12), fill=accent)
    elif style == "dots":
        y = bottom + 34
        for offset in (-70, 0, 70):
            draw.ellipse((center_x + offset - 13, y - 13, center_x + offset + 13, y + 13), fill=accent)
    elif style == "thin_frame":
        pad_x = 52
        pad_y = 34
        draw.rounded_rectangle(
            (left - pad_x, top - pad_y, right + pad_x, bottom + pad_y),
            radius=42,
            outline=accent,
            width=8,
        )
        draw.line((left - 18, bottom + 56, right + 18, bottom + 56), fill=accent, width=8)
    elif style == "side_marks":
        mark_w = max(42, width // 12)
        draw.rounded_rectangle((left - 74, top + 28, left - 52, bottom - 20), radius=11, fill=accent)
        draw.rounded_rectangle((right + 52, top + 28, right + 74, bottom - 20), radius=11, fill=accent)
        draw.line((center_x - mark_w, bottom + 48, center_x + mark_w, bottom + 48), fill=accent, width=10)
    elif style == "corner_marks":
        size = 52
        draw.line((left - 62, top - 30, left - 62 + size, top - 30), fill=accent, width=10)
        draw.line((left - 62, top - 30, left - 62, top - 30 + size), fill=accent, width=10)
        draw.line((right + 62, bottom + 30, right + 62 - size, bottom + 30), fill=accent, width=10)
        draw.line((right + 62, bottom + 30, right + 62, bottom + 30 - size), fill=accent, width=10)


def render_design(design: TextDesign) -> Path:
    canvas = Image.new("RGBA", (1600, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = load_font(design.font_path, design.font_size)

    sizes = [
        text_size(draw, line, font, design.tracking, design.stroke_width)
        for line in design.lines
    ]
    total_h = sum(h for _, h in sizes) + max(0, len(sizes) - 1) * design.line_gap
    y = (canvas.height - total_h) // 2 + design.y_shift
    line_boxes: list[tuple[int, int, int, int]] = []

    for line, (line_w, line_h) in zip(design.lines, sizes):
        x = (canvas.width - line_w) // 2
        draw_tracked_text(
            draw,
            (x, y),
            line,
            font,
            design.fill,
            design.tracking,
            design.stroke_width,
            design.stroke,
        )
        line_boxes.append((x, y, x + line_w, y + line_h))
        y += line_h + design.line_gap

    bbox = (
        min(box[0] for box in line_boxes),
        min(box[1] for box in line_boxes),
        max(box[2] for box in line_boxes),
        max(box[3] for box in line_boxes),
    )
    add_accents(draw, design.style, bbox, design.accent)

    alpha_box = canvas.getbbox()
    if alpha_box:
        pad = 120
        crop = (
            max(0, alpha_box[0] - pad),
            max(0, alpha_box[1] - pad),
            min(canvas.width, alpha_box[2] + pad),
            min(canvas.height, alpha_box[3] + pad),
        )
        canvas = canvas.crop(crop)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{design.slug}.png"
    canvas.save(path)
    return path


def make_overview(paths: list[Path]) -> None:
    tiles: list[Image.Image] = []
    for path in paths:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((320, 320), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (360, 410), (248, 248, 246))
        tile.paste(img, ((360 - img.width) // 2, (330 - img.height) // 2), img)
        draw = ImageDraw.Draw(tile)
        draw.text((18, 360), path.stem[:40], fill=(35, 35, 35))
        tiles.append(tile)

    sheet = Image.new("RGB", (len(tiles) * 360, 410), (232, 232, 228))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, (index * 360, 0))
    sheet.save(OUT_DIR / "_overview.jpg", quality=94)


def write_prompt_file() -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "简约艺术字文字印花，只保留文字、细线、点、角标等极少量排版元素，不要插画和徽章。",
        "所有印花必须贴在黑色、白色或深浅不同 T 恤上都清晰可见：使用高对比文字、浅色描边或深色描边，避免纯深色、纯浅色、低对比度。",
        "01 韩文：안녕，粗体简约艺术字，少量红色点缀。",
        "02 日文：いい日，细框艺术字，低饱和蓝色线条。",
        "03 英文：SLOW DAY，极简大写排版，下划线。",
        "04 中文：慢慢来，简约书写感艺术字，绿色侧标。",
        "05 中英混排：HELLO / 你好，简约角标排版。",
    ]
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    paths = [render_design(design) for design in DESIGNS]
    make_overview(paths)
    write_prompt_file()
    print(f"created {len(paths)} text prints")
    print(str(OUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
