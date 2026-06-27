from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")

BLACK = (12, 12, 12, 255)
GRAY = (92, 92, 92, 255)
LIGHT = (218, 218, 218, 255)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def text_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill=BLACK, stroke=WHITE, sw: int = 8) -> None:
    fnt = font("impact.ttf", size)
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=sw)
    x = xy[0] - (box[2] - box[0]) // 2
    y = xy[1] - (box[3] - box[1]) // 2
    draw.text((x, y), text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke)


def crop_save(img: Image.Image, path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 70
        img = img.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(img.width, bbox[2] + pad),
                min(img.height, bbox[3] + pad),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def draw_finger(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill=LIGHT, outline=BLACK) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=w // 2, fill=fill, outline=outline, width=13)
    draw.arc((x + 12, y + 18, x + w - 12, y + w), 200, 340, fill=GRAY, width=5)


def draw_palm(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], fill=LIGHT) -> None:
    draw.rounded_rectangle(bbox, radius=78, fill=fill, outline=BLACK, width=16)
    x1, y1, x2, y2 = bbox
    for i in range(3):
        yy = y1 + 70 + i * 58
        draw.arc((x1 + 55, yy, x2 - 55, yy + 85), 8, 172, fill=GRAY, width=5)


def draw_spark(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill=BLACK) -> None:
    pts = []
    for i in range(8):
        rr = r if i % 2 == 0 else r // 3
        a = -math.pi / 2 + i * math.pi / 4
        pts.append((cx + int(math.cos(a) * rr), cy + int(math.sin(a) * rr)))
    draw.polygon(pts, fill=fill)


def peace(draw: ImageDraw.ImageDraw) -> None:
    draw_finger(draw, 410, 180, 105, 410)
    draw_finger(draw, 570, 165, 105, 430)
    draw_finger(draw, 645, 505, 95, 270)
    draw_finger(draw, 330, 525, 95, 250)
    draw_palm(draw, (390, 555, 690, 950))
    draw.line((515, 620, 505, 835), fill=GRAY, width=7)
    draw.line((600, 625, 620, 835), fill=GRAY, width=7)
    text_center(draw, (540, 1070), "PEACE", 120)
    for x, y in [(310, 240), (760, 270), (295, 820), (805, 765)]:
        draw_spark(draw, x, y, 34)


def rock(draw: ImageDraw.ImageDraw) -> None:
    draw_finger(draw, 345, 190, 100, 455)
    draw_finger(draw, 665, 190, 100, 455)
    draw_finger(draw, 500, 530, 92, 235)
    draw_finger(draw, 235, 625, 105, 280)
    draw_finger(draw, 765, 625, 105, 280)
    draw_palm(draw, (382, 560, 720, 960))
    draw.line((320, 1050, 790, 980), fill=BLACK, width=24)
    text_center(draw, (555, 1135), "NOISE", 118, BLACK, WHITE, 8)
    for x in (260, 850):
        draw.ellipse((x - 28, 430, x + 28, 486), fill=BLACK)


def ok_sign(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((355, 300, 685, 630), fill=LIGHT, outline=BLACK, width=18)
    draw.ellipse((455, 400, 585, 530), fill=TRANSPARENT, outline=BLACK, width=18)
    draw_finger(draw, 625, 235, 90, 430)
    draw_finger(draw, 735, 300, 85, 380)
    draw_finger(draw, 795, 410, 82, 340)
    draw_finger(draw, 300, 570, 95, 315)
    draw_palm(draw, (410, 585, 700, 940))
    draw.arc((360, 270, 715, 655), 120, 315, fill=GRAY, width=7)
    text_center(draw, (555, 1070), "OKAY", 128)
    draw_spark(draw, 265, 280, 38)
    draw_spark(draw, 865, 755, 30)


def crossed(draw: ImageDraw.ImageDraw) -> None:
    draw_finger(draw, 480, 125, 105, 500)
    draw_finger(draw, 585, 160, 105, 470)
    draw.line((515, 200, 670, 695), fill=GRAY, width=8)
    draw_finger(draw, 365, 560, 90, 300)
    draw_finger(draw, 700, 570, 90, 292)
    draw_palm(draw, (430, 610, 725, 930))
    draw.arc((470, 140, 680, 300), 205, 335, fill=BLACK, width=18)
    text_center(draw, (580, 1088), "LUCK", 118)
    for x, y in [(330, 355), (820, 355), (350, 965), (805, 980)]:
        draw_spark(draw, x, y, 28)


def point(draw: ImageDraw.ImageDraw) -> None:
    draw_finger(draw, 250, 395, 610, 105)
    draw_finger(draw, 565, 510, 95, 240)
    draw_finger(draw, 505, 590, 95, 240)
    draw_finger(draw, 440, 665, 95, 225)
    draw_palm(draw, (285, 555, 585, 905))
    draw.polygon([(850, 405), (970, 448), (850, 490)], fill=BLACK)
    draw.line((315, 447, 870, 447), fill=WHITE, width=9)
    draw.line((310, 950, 820, 1015), fill=BLACK, width=22)
    text_center(draw, (570, 1110), "POINT", 120)
    draw_spark(draw, 1000, 350, 36)
    draw_spark(draw, 970, 565, 22)


RENDERERS = [
    ("gesture_peace", peace),
    ("gesture_noise", rock),
    ("gesture_okay", ok_sign),
    ("gesture_luck", crossed),
    ("gesture_right", point),
]


def make_overview(paths: list[Path], out: Path) -> None:
    tile = 360
    label_h = 42
    sheet = Image.new("RGB", (tile * len(paths), tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = idx * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((idx * tile + 16, tile + 10), path.stem, fill=(0, 0, 0))
    sheet.save(out, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render 5 black-white-gray gesture print tests.")
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / "印花图_透明底" / f"黑白灰手势印花测试_{args.date}"
    paths: list[Path] = []
    for name, renderer in RENDERERS:
        img = Image.new("RGBA", (1200, 1200), TRANSPARENT)
        draw = ImageDraw.Draw(img)
        renderer(draw)
        path = out_dir / f"{name}.png"
        crop_save(img, path)
        paths.append(path)
        print(f"rendered {path}")
    make_overview(paths, out_dir / "_overview.jpg")
    notes = ROOT / "生成提示词" / f"黑白灰手势印花测试_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(
        "黑白灰手势印花测试：peace、rock/noise、okay、luck、pointing。透明底，不走正式流程。\n",
        encoding="utf-8",
    )
    print(f"Output dir: {out_dir}")
    print(f"Overview: {out_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
