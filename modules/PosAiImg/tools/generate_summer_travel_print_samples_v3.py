from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from PIL import Image, ImageDraw

from generate_summer_travel_print_samples import CREAM, DARK, RED, GREEN, BLUE, GOLD, FONT_DIR, paste_center
from generate_summer_travel_print_samples_v2 import (
    draw_cup_map,
    draw_spritz,
    draw_sun_wave,
    font,
    outlined_arc,
    outlined_ellipse,
    stroked,
    text_center,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "印花图_透明底" / "夏日饮品旅行小图样稿_v3_2026-06-14"


@dataclass(frozen=True)
class Spec:
    sku: str
    label: str
    motif: str
    accent: tuple[int, int, int, int]


SPECS = [
    Spec("SUMMER-V3-001", "CITRUS", "spritz", GOLD),
    Spec("SUMMER-V3-002", "SODA SUN", "soda", RED),
    Spec("SUMMER-V3-003", "CAFE", "cup_map", GREEN),
    Spec("SUMMER-V3-004", "CAFE ROAD", "cafe_road", BLUE),
    Spec("SUMMER-V3-005", "COAST 86", "sun_wave", RED),
]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def draw_soda(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 700
    draw.rounded_rectangle((cx - 135, cy - 260, cx + 135, cy + 220), radius=48, fill=CREAM, outline=DARK, width=16)
    draw.rounded_rectangle((cx - 112, cy - 18, cx + 112, cy + 186), radius=34, fill=accent)
    draw.rounded_rectangle((cx - 88, cy - 328, cx + 88, cy - 244), radius=20, fill=CREAM, outline=DARK, width=13)
    draw.line((cx - 44, cy - 360, cx - 10, cy - 448), fill=DARK, width=12)
    draw.line((cx + 18, cy - 360, cx + 76, cy - 450), fill=DARK, width=12)
    for x in range(cx - 70, cx + 71, 35):
        draw.ellipse((x - 10, cy + 48, x + 10, cy + 68), fill=CREAM)
    outlined_ellipse(draw, (cx + 128, cy - 296, cx + 326, cy - 98), CREAM, DARK, 12)
    outlined_ellipse(draw, (cx - 340, cy - 108, cx - 164, cy + 68), CREAM, DARK, 12)
    outlined_arc(draw, (cx - 470, cy - 510, cx + 470, cy + 400), 205, 335, GOLD, 12)


def draw_cafe_road(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int, int]) -> None:
    cx, cy = 750, 690
    draw.rounded_rectangle((cx - 170, cy - 180, cx + 170, cy + 150), radius=44, fill=CREAM, outline=DARK, width=16)
    draw.arc((cx + 122, cy - 72, cx + 284, cy + 96), -70, 83, fill=CREAM, width=36)
    draw.arc((cx + 136, cy - 58, cx + 254, cy + 82), -70, 83, fill=DARK, width=12)
    outlined_arc(draw, (cx - 365, cy - 450, cx + 365, cy + 250), 215, 325, GOLD, 12)
    for offset in (-62, 0, 62):
        stroked(draw, [(cx + offset, cy - 250), (cx + offset - 20, cy - 320), (cx + offset + 16, cy - 380)], accent, 8)
    route = [(350, 930), (505, 855), (665, 920), (820, 845), (980, 900), (1140, 820)]
    stroked(draw, route, accent, 13)
    for x, y in route[1::2]:
        outlined_ellipse(draw, (x - 24, y - 24, x + 24, y + 24), CREAM, DARK, 8)


def render(spec: Spec) -> Path:
    img = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if spec.motif == "spritz":
        draw_spritz(draw, spec.accent)
    elif spec.motif == "soda":
        draw_soda(draw, spec.accent)
    elif spec.motif == "cup_map":
        draw_cup_map(draw, spec.accent)
    elif spec.motif == "cafe_road":
        draw_cafe_road(draw, spec.accent)
    else:
        draw_sun_wave(draw, spec.accent)

    text_center(draw, spec.label, font("ariblk.ttf", 84), 1118, DARK, 9)
    text_center(draw, "SUMMER DAILY", font("bahnschrift.ttf", 40), 1224, DARK, 4)
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
