from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
OUTPUT_DIR = ROOT / "印花图_透明底" / "夏日饮品旅行小图样稿_2026-06-14"

DARK = (22, 27, 29, 255)
CREAM = (248, 243, 226, 255)
RED = (183, 55, 48, 255)
GREEN = (70, 120, 96, 255)
BLUE = (83, 104, 150, 255)
GOLD = (190, 137, 72, 255)


@dataclass(frozen=True)
class Spec:
    sku: str
    main: str
    sub: str
    motif: str
    accent: tuple[int, int, int, int]


SPECS = [
    Spec("SUMMER-001", "SPRITZ CLUB", "LEMON SUN", "lemon", GOLD),
    Spec("SUMMER-002", "CAFE HOUR", "SLOW WALK", "coffee", GREEN),
    Spec("SUMMER-003", "SUNSET MOTEL", "COAST 86", "sunset", RED),
    Spec("SUMMER-004", "WEEKEND TICKET", "DAY OFF", "ticket", BLUE),
    Spec("SUMMER-005", "SEA SIDE", "POSTCARD NOTE", "postcard", GREEN),
]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def centered(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, y: int, fill: tuple[int, int, int, int], stroke: int = 0) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    x = (1500 - (box[2] - box[0])) // 2 - box[0]
    draw.text((x, y - box[1]), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=CREAM)
    return (x + box[0], y, x + box[2], y + box[3] - box[1])


def stroked_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: tuple[int, int, int, int], width: int) -> None:
    draw.line([(int(x), int(y)) for x, y in points], fill=CREAM, width=width + 10, joint="curve")
    draw.line([(int(x), int(y)) for x, y in points], fill=fill, width=width, joint="curve")


def outlined_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], outline: tuple[int, int, int, int], width: int = 10, radius: int = 28) -> None:
    draw.rounded_rectangle(box, radius=radius, outline=CREAM, width=width + 9)
    draw.rounded_rectangle(box, radius=radius, outline=outline, width=width)


def draw_lemon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int, int]) -> None:
    draw.ellipse((cx - 115, cy - 115, cx + 115, cy + 115), fill=CREAM)
    draw.ellipse((cx - 98, cy - 98, cx + 98, cy + 98), outline=DARK, width=12)
    draw.ellipse((cx - 76, cy - 76, cx + 76, cy + 76), outline=color, width=8)
    for deg in range(0, 360, 45):
        x = cx + math.cos(math.radians(deg)) * 78
        y = cy + math.sin(math.radians(deg)) * 78
        draw.line((cx, cy, x, y), fill=DARK, width=6)
    draw.arc((cx - 190, cy - 54, cx + 190, cy + 120), 195, 345, fill=color, width=12)


def draw_coffee(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle((cx - 104, cy - 96, cx + 104, cy + 96), radius=28, fill=CREAM, outline=DARK, width=12)
    draw.arc((cx + 76, cy - 35, cx + 172, cy + 62), -70, 85, fill=CREAM, width=26)
    draw.arc((cx + 84, cy - 27, cx + 156, cy + 52), -70, 85, fill=DARK, width=10)
    for offset in (-54, 0, 54):
        stroked_line(draw, [(cx + offset, cy - 165), (cx + offset - 18, cy - 215), (cx + offset + 12, cy - 260)], color, 7)
    draw.rounded_rectangle((cx - 138, cy + 116, cx + 138, cy + 132), radius=8, fill=color)


def draw_sunset(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int, int]) -> None:
    draw.pieslice((cx - 175, cy - 175, cx + 175, cy + 175), 180, 360, fill=CREAM, outline=DARK, width=12)
    for i in range(4):
        y = cy + 18 + i * 38
        draw.rounded_rectangle((cx - 220 + i * 28, y, cx + 220 - i * 28, y + 12), radius=6, fill=color if i % 2 else DARK)
    for deg in range(205, 336, 26):
        x1 = cx + math.cos(math.radians(deg)) * 205
        y1 = cy + math.sin(math.radians(deg)) * 205
        x2 = cx + math.cos(math.radians(deg)) * 270
        y2 = cy + math.sin(math.radians(deg)) * 270
        draw.line((x1, y1, x2, y2), fill=color, width=10)


def draw_ticket(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int, int]) -> None:
    box = (cx - 250, cy - 105, cx + 250, cy + 105)
    draw.rounded_rectangle(box, radius=22, fill=CREAM, outline=DARK, width=12)
    for y in (cy - 78, cy + 78):
        draw.line((cx - 210, y, cx + 210, y), fill=color, width=8)
    for x in range(cx - 170, cx + 171, 68):
        draw.ellipse((x - 9, cy - 9, x + 9, cy + 9), fill=color)
    draw.arc((cx - 320, cy - 205, cx + 320, cy + 205), 200, 340, fill=DARK, width=10)


def draw_postcard(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int, int]) -> None:
    outlined_box(draw, (cx - 250, cy - 150, cx + 250, cy + 150), color, width=9, radius=18)
    draw.line((cx + 65, cy - 122, cx + 65, cy + 122), fill=DARK, width=8)
    for i in range(4):
        draw.rounded_rectangle((cx - 210, cy - 92 + i * 48, cx - 18, cy - 82 + i * 48), radius=5, fill=DARK if i % 2 else color)
    draw.rectangle((cx + 105, cy - 105, cx + 205, cy - 30), outline=DARK, width=8)
    draw.arc((cx - 142, cy + 8, cx + 36, cy + 110), 190, 350, fill=color, width=10)


def render(spec: Spec) -> Path:
    img = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    title_font = font("ariblk.ttf", 138)
    sub_font = font("bahnschrift.ttf", 58)

    motif_y = 560
    if spec.motif == "lemon":
        draw_lemon(draw, 750, motif_y, spec.accent)
    elif spec.motif == "coffee":
        draw_coffee(draw, 750, motif_y, spec.accent)
    elif spec.motif == "sunset":
        draw_sunset(draw, 750, motif_y, spec.accent)
    elif spec.motif == "ticket":
        draw_ticket(draw, 750, motif_y, spec.accent)
    else:
        draw_postcard(draw, 750, motif_y, spec.accent)

    main_box = centered(draw, spec.main, title_font, 835, DARK, 11)
    sub_box = centered(draw, spec.sub, sub_font, 1012, DARK, 4)
    left = min(main_box[0], sub_box[0])
    right = max(main_box[2], sub_box[2])
    draw.rounded_rectangle((left + 28, 970, right - 28, 984), radius=7, fill=spec.accent)
    outlined_box(draw, (left - 64, 360, right + 64, 1098), spec.accent, width=7, radius=34)

    crop = img.getbbox()
    if crop:
        pad = 105
        img = img.crop((max(0, crop[0] - pad), max(0, crop[1] - pad), min(img.width, crop[2] + pad), min(img.height, crop[3] + pad)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{spec.sku}_{spec.main.replace(' ', '')}.png"
    img.save(out)
    return out


def paste_center(base: Image.Image, art: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    scale = min((x2 - x1) / art.width, (y2 - y1) / art.height)
    resized = art.resize((int(art.width * scale), int(art.height * scale)), Image.Resampling.LANCZOS)
    base.alpha_composite(resized, (x1 + (x2 - x1 - resized.width) // 2, y1 + (y2 - y1 - resized.height) // 2))


def overview(paths: list[Path]) -> Path:
    cell_w, cell_h = 520, 410
    margin = 34
    canvas = Image.new("RGBA", (cell_w * 3 + margin * 2, cell_h * len(paths) + margin * 2), (238, 238, 232, 255))
    draw = ImageDraw.Draw(canvas)
    label_font = font("bahnschrift.ttf", 31)
    for row, path in enumerate(paths):
        y = margin + row * cell_h
        checker = Image.new("RGBA", (cell_w, cell_h), (232, 232, 226, 255))
        checker_draw = ImageDraw.Draw(checker)
        for yy in range(0, cell_h, 40):
            for xx in range(0, cell_w, 40):
                if (xx // 40 + yy // 40) % 2:
                    checker_draw.rectangle((xx, yy, xx + 40, yy + 40), fill=(212, 212, 206, 255))
        white = Image.new("RGBA", (cell_w, cell_h), (248, 248, 244, 255))
        black = Image.new("RGBA", (cell_w, cell_h), (23, 24, 25, 255))
        art = Image.open(path).convert("RGBA")
        for panel in (checker, white, black):
            paste_center(panel, art, (70, 70, cell_w - 70, cell_h - 44))
        canvas.alpha_composite(checker, (margin, y))
        canvas.alpha_composite(white, (margin + cell_w, y))
        canvas.alpha_composite(black, (margin + cell_w * 2, y))
        draw.text((margin + 18, y + 14), path.stem.replace("_", " / "), font=label_font, fill=(35, 35, 35, 255))
    out = OUTPUT_DIR / "_overview.jpg"
    canvas.convert("RGB").save(out, quality=92)
    return out


def main() -> int:
    configure_stdout()
    paths = [render(spec) for spec in SPECS]
    out = overview(paths)
    print(f"output_dir={OUTPUT_DIR}")
    print(f"count={len(paths)}")
    print(f"overview={out}")
    for path in paths:
        print(path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
