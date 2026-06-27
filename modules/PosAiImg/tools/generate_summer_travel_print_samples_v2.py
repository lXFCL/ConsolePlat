from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import sys

from PIL import Image, ImageDraw, ImageFont

from generate_summer_travel_print_samples import CREAM, DARK, RED, GREEN, BLUE, GOLD, FONT_DIR, paste_center


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "印花图_透明底" / "夏日饮品旅行小图样稿_v2_2026-06-14"


@dataclass(frozen=True)
class Spec:
    sku: str
    label: str
    motif: str
    accent: tuple[int, int, int, int]


SPECS = [
    Spec("SUMMER-V2-001", "CITRUS", "spritz", GOLD),
    Spec("SUMMER-V2-002", "CAFE", "cup_map", GREEN),
    Spec("SUMMER-V2-003", "COAST 86", "sun_wave", RED),
    Spec("SUMMER-V2-004", "DAY PASS", "ticket_pin", BLUE),
    Spec("SUMMER-V2-005", "SEA NOTE", "postcard_shell", GREEN),
]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def text_center(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, y: int, fill: tuple[int, int, int, int], stroke: int = 0) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    x = (1500 - (box[2] - box[0])) // 2 - box[0]
    draw.text((x, y - box[1]), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=CREAM)
    return (x + box[0], y, x + box[2], y + box[3] - box[1])


def stroked(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int, int], width: int) -> None:
    pts = [(int(x), int(y)) for x, y in points]
    draw.line(pts, fill=CREAM, width=width + 12, joint="curve")
    draw.line(pts, fill=color, width=width, joint="curve")


def outlined_arc(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], start: int, end: int, color: tuple[int, int, int, int], width: int) -> None:
    draw.arc(box, start, end, fill=CREAM, width=width + 12)
    draw.arc(box, start, end, fill=color, width=width)


def outlined_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int, int], outline: tuple[int, int, int, int], width: int) -> None:
    grow = width // 2 + 6
    outer = (box[0] - grow, box[1] - grow, box[2] + grow, box[3] + grow)
    draw.ellipse(outer, fill=CREAM)
    draw.ellipse(box, fill=fill, outline=outline, width=width)


def draw_spritz(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 700
    draw.rounded_rectangle((cx - 150, cy - 180, cx + 150, cy + 230), radius=54, fill=CREAM, outline=DARK, width=16)
    draw.rounded_rectangle((cx - 124, cy - 10, cx + 124, cy + 206), radius=38, fill=accent)
    for i in range(5):
        draw.ellipse((cx - 92 + i * 44, cy + 32 + (i % 2) * 34, cx - 66 + i * 44, cy + 58 + (i % 2) * 34), fill=CREAM)
    draw.line((cx - 80, cy - 210, cx - 42, cy - 330), fill=DARK, width=12)
    draw.line((cx - 28, cy - 210, cx + 30, cy - 332), fill=DARK, width=12)
    outlined_ellipse(draw, (cx - 300, cy - 260, cx - 110, cy - 70), CREAM, DARK, 12)
    for deg in range(0, 360, 45):
        draw.line((cx - 205, cy - 165, cx - 205 + math.cos(math.radians(deg)) * 82, cy - 165 + math.sin(math.radians(deg)) * 82), fill=accent, width=6)
    outlined_arc(draw, (cx - 430, cy - 420, cx + 430, cy + 360), 205, 335, accent, 12)


def draw_cup_map(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 700
    draw.rounded_rectangle((cx - 180, cy - 160, cx + 180, cy + 160), radius=44, fill=CREAM, outline=DARK, width=16)
    draw.arc((cx + 132, cy - 58, cx + 290, cy + 110), -70, 83, fill=CREAM, width=36)
    draw.arc((cx + 146, cy - 46, cx + 260, cy + 94), -70, 83, fill=DARK, width=12)
    for offset in (-70, 0, 70):
        stroked(draw, [(cx + offset, cy - 235), (cx + offset - 18, cy - 295), (cx + offset + 20, cy - 350)], accent, 8)
    route = [(380, 930), (520, 860), (630, 930), (770, 850), (930, 900), (1085, 812)]
    stroked(draw, route, accent, 12)
    for x, y in route[::2]:
        outlined_ellipse(draw, (x - 24, y - 24, x + 24, y + 24), CREAM, DARK, 8)


def draw_sun_wave(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 720
    draw.pieslice((cx - 280, cy - 370, cx + 280, cy + 190), 180, 360, fill=CREAM, outline=DARK, width=18)
    for deg in range(205, 336, 18):
        x1 = cx + math.cos(math.radians(deg)) * 326
        y1 = cy - 90 + math.sin(math.radians(deg)) * 326
        x2 = cx + math.cos(math.radians(deg)) * 410
        y2 = cy - 90 + math.sin(math.radians(deg)) * 410
        draw.line((x1, y1, x2, y2), fill=accent, width=12)
    for i in range(6):
        y = cy + 18 + i * 54
        points = []
        for x in range(320, 1181, 24):
            points.append((x, y + math.sin((x - 320) / 860 * math.tau * 1.4 + i * 0.45) * 14))
        stroked(draw, points, accent if i % 2 else DARK, 10)


def draw_ticket_pin(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 705
    draw.rounded_rectangle((cx - 430, cy - 160, cx + 430, cy + 160), radius=34, fill=CREAM, outline=DARK, width=16)
    for x in (cx - 310, cx + 310):
        draw.ellipse((x - 52, cy - 52, x + 52, cy + 52), fill=(0, 0, 0, 0), outline=DARK, width=12)
    draw.rounded_rectangle((cx - 210, cy - 78, cx + 210, cy + 78), radius=18, outline=accent, width=12)
    for x in range(cx - 150, cx + 151, 60):
        draw.ellipse((x - 11, cy - 11, x + 11, cy + 11), fill=accent)
    pin_cx, pin_cy = cx + 295, cy - 260
    draw.ellipse((pin_cx - 74, pin_cy - 74, pin_cx + 74, pin_cy + 74), fill=CREAM, outline=DARK, width=12)
    draw.polygon([(pin_cx, pin_cy + 132), (pin_cx - 48, pin_cy + 38), (pin_cx + 48, pin_cy + 38)], fill=CREAM, outline=DARK)
    draw.ellipse((pin_cx - 24, pin_cy - 24, pin_cx + 24, pin_cy + 24), fill=accent)


def draw_postcard_shell(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 710
    draw.rounded_rectangle((cx - 380, cy - 250, cx + 380, cy + 250), radius=28, fill=CREAM, outline=DARK, width=16)
    draw.line((cx + 120, cy - 210, cx + 120, cy + 210), fill=DARK, width=10)
    for i in range(5):
        draw.rounded_rectangle((cx - 310, cy - 150 + i * 62, cx + 30, cy - 138 + i * 62), radius=6, fill=accent if i % 2 else DARK)
    draw.rectangle((cx + 185, cy - 170, cx + 312, cy - 70), outline=DARK, width=10)
    shell_cx, shell_cy = cx - 135, cy + 85
    outlined_arc(draw, (shell_cx - 150, shell_cy - 125, shell_cx + 150, shell_cy + 125), 200, 340, accent, 11)
    for deg in range(210, 331, 30):
        draw.line((shell_cx, shell_cy + 15, shell_cx + math.cos(math.radians(deg)) * 128, shell_cy + math.sin(math.radians(deg)) * 100), fill=DARK, width=7)
    outlined_arc(draw, (cx - 485, cy - 380, cx + 485, cy + 355), 205, 335, accent, 11)


def render(spec: Spec) -> Path:
    img = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if spec.motif == "spritz":
        draw_spritz(draw, spec.accent)
    elif spec.motif == "cup_map":
        draw_cup_map(draw, spec.accent)
    elif spec.motif == "sun_wave":
        draw_sun_wave(draw, spec.accent)
    elif spec.motif == "ticket_pin":
        draw_ticket_pin(draw, spec.accent)
    else:
        draw_postcard_shell(draw, spec.accent)

    label_font = font("ariblk.ttf", 88)
    small_font = font("bahnschrift.ttf", 42)
    text_center(draw, spec.label, label_font, 1115, DARK, 9)
    text_center(draw, "SUMMER DAILY", small_font, 1226, DARK, 4)
    draw.rounded_rectangle((560, 1192, 940, 1206), radius=7, fill=spec.accent)

    crop = img.getbbox()
    if crop:
        pad = 120
        img = img.crop((max(0, crop[0] - pad), max(0, crop[1] - pad), min(img.width, crop[2] + pad), min(img.height, crop[3] + pad)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{spec.sku}_{spec.label.replace(' ', '')}.png"
    img.save(path)
    return path


def overview(paths: list[Path]) -> Path:
    cell_w, cell_h = 520, 430
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
            paste_center(panel, art, (58, 50, cell_w - 58, cell_h - 42))
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
