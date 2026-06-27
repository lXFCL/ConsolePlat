from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BLACK = (10, 10, 10, 255)
GRAY = (92, 92, 92, 255)
LIGHT = (224, 224, 224, 255)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def finger(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, angle: float = 0) -> None:
    img = Image.new("RGBA", (w + 60, h + 60), TRANSPARENT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 20, 30 + w, 20 + h), radius=w // 2, fill=LIGHT, outline=BLACK, width=10)
    for yy in (int(h * 0.28), int(h * 0.52), int(h * 0.75)):
        d.arc((42, 20 + yy - 20, 18 + w, 20 + yy + 28), 10, 170, fill=GRAY, width=4)
    if angle:
        img = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    draw._image.alpha_composite(img, (x - img.width // 2, y - img.height // 2))


def palm(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, angle: float = 0) -> None:
    img = Image.new("RGBA", (w + 90, h + 90), TRANSPARENT)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((45, 45, 45 + w, 45 + h), radius=52, fill=LIGHT, outline=BLACK, width=12)
    for off in (0.28, 0.48, 0.68):
        yy = 45 + int(h * off)
        d.arc((45 + 42, yy - 32, 45 + w - 42, yy + 45), 10, 170, fill=GRAY, width=4)
    d.line((45 + w * 0.25, 45 + h * 0.82, 45 + w * 0.52, 45 + h * 0.55), fill=GRAY, width=4)
    if angle:
        img = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    draw._image.alpha_composite(img, (cx - img.width // 2, cy - img.height // 2))


def sleeve_shadow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.line((x1, y1, x2, y2), fill=BLACK, width=18)
    draw.line((x1 + 26, y1 - 8, x2 + 18, y2 - 28), fill=GRAY, width=5)


def spark(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    pts = []
    for i in range(8):
        rr = r if i % 2 == 0 else r // 3
        a = -math.pi / 2 + i * math.pi / 4
        pts.append((cx + int(math.cos(a) * rr), cy + int(math.sin(a) * rr)))
    draw.polygon(pts, fill=BLACK)


def seal_prayer(draw: ImageDraw.ImageDraw) -> None:
    palm(draw, 470, 630, 155, 330, -7)
    palm(draw, 690, 630, 155, 330, 7)
    for x, a in [(455, -5), (510, -2), (650, 2), (705, 5)]:
        finger(draw, x, 300, 54, 350, a)
    finger(draw, 575, 392, 58, 315, 0)
    sleeve_shadow(draw, 390, 900, 310, 1140)
    sleeve_shadow(draw, 770, 900, 850, 1140)
    draw.line((575, 250, 575, 910), fill=BLACK, width=10)
    spark(draw, 270, 290, 28)
    spark(draw, 890, 290, 28)


def seal_interlock(draw: ImageDraw.ImageDraw) -> None:
    palm(draw, 500, 675, 170, 300, -18)
    palm(draw, 680, 675, 170, 300, 18)
    for i, x in enumerate([395, 470, 545, 620, 695, 770]):
        finger(draw, x, 445 + (i % 2) * 35, 56, 270, -24 if i < 3 else 24)
    draw.line((425, 595, 745, 595), fill=BLACK, width=12)
    draw.line((450, 680, 720, 680), fill=GRAY, width=6)
    sleeve_shadow(draw, 380, 900, 275, 1110)
    sleeve_shadow(draw, 785, 900, 890, 1110)
    spark(draw, 580, 235, 32)


def seal_cross(draw: ImageDraw.ImageDraw) -> None:
    palm(draw, 475, 675, 160, 310, -12)
    palm(draw, 695, 675, 160, 310, 12)
    finger(draw, 530, 330, 58, 390, -28)
    finger(draw, 640, 330, 58, 390, 28)
    finger(draw, 460, 430, 54, 285, -8)
    finger(draw, 710, 430, 54, 285, 8)
    draw.line((445, 330, 730, 615), fill=BLACK, width=11)
    draw.line((725, 330, 440, 615), fill=BLACK, width=11)
    sleeve_shadow(draw, 390, 900, 310, 1130)
    sleeve_shadow(draw, 780, 900, 860, 1130)


def seal_triangle(draw: ImageDraw.ImageDraw) -> None:
    palm(draw, 465, 700, 160, 300, -20)
    palm(draw, 705, 700, 160, 300, 20)
    finger(draw, 505, 360, 54, 345, -35)
    finger(draw, 665, 360, 54, 345, 35)
    finger(draw, 585, 355, 54, 330, 0)
    draw.polygon([(500, 485), (670, 485), (585, 620)], outline=BLACK, fill=TRANSPARENT)
    draw.line((500, 485, 670, 485, 585, 620, 500, 485), fill=BLACK, width=12)
    draw.arc((430, 305, 740, 700), 205, 335, fill=GRAY, width=6)
    sleeve_shadow(draw, 365, 910, 285, 1135)
    sleeve_shadow(draw, 805, 910, 885, 1135)


def seal_stack(draw: ImageDraw.ImageDraw) -> None:
    palm(draw, 515, 670, 160, 300, -8)
    palm(draw, 675, 620, 160, 300, 80)
    finger(draw, 530, 305, 56, 345, -8)
    finger(draw, 610, 305, 56, 345, 8)
    finger(draw, 715, 565, 54, 330, 82)
    finger(draw, 710, 465, 54, 300, 82)
    draw.line((420, 560, 850, 560), fill=BLACK, width=13)
    draw.line((500, 350, 650, 690), fill=GRAY, width=7)
    sleeve_shadow(draw, 430, 915, 345, 1140)
    sleeve_shadow(draw, 825, 710, 1030, 810)


RENDERERS = [
    ("seal_prayer", seal_prayer),
    ("seal_interlock", seal_interlock),
    ("seal_cross", seal_cross),
    ("seal_triangle", seal_triangle),
    ("seal_stack", seal_stack),
]


def crop_save(img: Image.Image, path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 70
        img = img.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad)))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


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
    parser = argparse.ArgumentParser(description="Render 5 monochrome line-art hand-seal print tests.")
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / "印花图_透明底" / f"黑白灰线稿结印手势测试_{args.date}"
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
    notes = ROOT / "生成提示词" / f"黑白灰线稿结印手势测试_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("黑白灰线稿结印手势测试：原创双手结印感、透明底、不含角色和版权符号。\n", encoding="utf-8")
    print(f"Output dir: {out_dir}")
    print(f"Overview: {out_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
