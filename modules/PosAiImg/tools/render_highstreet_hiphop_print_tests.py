from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
STYLE_NAME = "高街嘻哈印花"


BLACK = (12, 12, 12, 255)
CREAM = (246, 238, 215, 255)
WHITE = (255, 255, 255, 255)
RED = (203, 32, 38, 255)
GOLD = (199, 153, 71, 255)
GRAY = (68, 68, 68, 255)


@dataclass(frozen=True)
class PrintSpec:
    sku: str
    name: str
    title: str


def batch_name(start: int, count: int, batch_date: str | None = None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"{STYLE_NAME}_BO-{start}-BO-{end}_{stamp}"


def output_dir(start: int, count: int, batch_date: str | None = None) -> Path:
    return ROOT / "印花图_透明底" / batch_name(start, count, batch_date)


def prompt_file(start: int, count: int, batch_date: str | None = None) -> Path:
    return ROOT / "生成提示词" / f"{batch_name(start, count, batch_date)}.txt"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font_obj: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke_fill: tuple[int, int, int, int] = WHITE,
    stroke_width: int = 10,
) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=font_obj, stroke_width=stroke_width)
    w = box[2] - box[0]
    h = box[3] - box[1]
    x = xy[0] - w // 2
    y = xy[1] - h // 2
    draw.text((x, y), text, font=font_obj, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
    return (x, y, x + w, y + h)


def fit_font(text: str, font_name: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 40:
        f = font(font_name, size)
        box = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=f, stroke_width=16)
        if box[2] - box[0] <= max_width:
            return f
        size -= 6
    return font(font_name, size)


def draw_crown(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill: tuple[int, int, int, int]) -> None:
    w = int(260 * scale)
    h = int(145 * scale)
    base_y = cy + h // 3
    points = [
        (cx - w // 2, base_y),
        (cx - int(w * 0.33), cy - h // 4),
        (cx - int(w * 0.15), base_y - int(h * 0.2)),
        (cx, cy - h // 2),
        (cx + int(w * 0.15), base_y - int(h * 0.2)),
        (cx + int(w * 0.33), cy - h // 4),
        (cx + w // 2, base_y),
    ]
    draw.polygon(points, fill=fill, outline=BLACK)
    draw.rounded_rectangle((cx - w // 2, base_y - 12, cx + w // 2, base_y + 42), radius=16, fill=fill, outline=BLACK, width=7)
    for px, py in points[1::2]:
        draw.ellipse((px - 16, py - 16, px + 16, py + 16), fill=fill, outline=BLACK, width=5)


def draw_splatter(draw: ImageDraw.ImageDraw, rng: random.Random, center: tuple[int, int], radius: int, color: tuple[int, int, int, int]) -> None:
    cx, cy = center
    for _ in range(34):
        ang = rng.random() * math.tau
        dist = rng.randint(radius // 5, radius)
        r = rng.randint(4, 18)
        x = int(cx + math.cos(ang) * dist)
        y = int(cy + math.sin(ang) * dist)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
        if rng.random() < 0.25:
            draw.line((x, y, x, y + rng.randint(28, 90)), fill=color, width=max(3, r // 2))


def draw_chain(draw: ImageDraw.ImageDraw, y: int) -> None:
    for i, x in enumerate(range(275, 1226, 115)):
        color = GOLD if i % 2 == 0 else CREAM
        draw.rounded_rectangle((x - 55, y - 35, x + 55, y + 35), radius=34, outline=BLACK, width=24)
        draw.rounded_rectangle((x - 55, y - 35, x + 55, y + 35), radius=34, outline=color, width=12)


def draw_shield(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    outer = [(cx - 250, cy - 290), (cx + 250, cy - 290), (cx + 205, cy + 120), (cx, cy + 330), (cx - 205, cy + 120)]
    inner = [(cx - 195, cy - 220), (cx + 195, cy - 220), (cx + 160, cy + 80), (cx, cy + 245), (cx - 160, cy + 80)]
    draw.polygon(outer, fill=GOLD, outline=BLACK)
    draw.polygon(inner, fill=BLACK, outline=CREAM)
    draw.line((cx - 180, cy - 40, cx + 180, cy - 40), fill=GOLD, width=12)
    draw.line((cx - 145, cy + 95, cx + 145, cy + 95), fill=GOLD, width=10)
    for side in (-1, 1):
        for i in range(9):
            x = cx + side * (290 + i * 18)
            y = cy - 210 + i * 45
            draw.ellipse((x - 42, y - 18, x + 42, y + 18), fill=GOLD, outline=BLACK, width=4)


def draw_record(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.ellipse((cx - 360, cy - 360, cx + 360, cy + 360), fill=BLACK, outline=RED, width=36)
    draw.ellipse((cx - 245, cy - 245, cx + 245, cy + 245), outline=CREAM, width=22)
    draw.ellipse((cx - 118, cy - 118, cx + 118, cy + 118), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=BLACK)
    draw.arc((cx - 300, cy - 300, cx + 300, cy + 300), 205, 335, fill=RED, width=28)


def crop_and_save(img: Image.Image, path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 80
        bbox = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(img.width, bbox[2] + pad),
            min(img.height, bbox[3] + pad),
        )
        img = img.crop(bbox)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def render(spec: PrintSpec, path: Path, seed: int) -> None:
    rng = random.Random(seed)
    img = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    impact = fit_font(spec.title, "impact.ttf", 1050, 250)
    gothic = fit_font(spec.title, "GOTHICB.TTF", 980, 210)

    if spec.name == "皇冠涂鸦":
        draw_splatter(draw, rng, (750, 770), 470, RED)
        draw_crown(draw, 750, 430, 1.15, RED)
        centered_text(draw, (750, 760), "KING", impact, BLACK, CREAM, 20)
        centered_text(draw, (750, 1015), "VIBE", gothic, RED, BLACK, 12)
        draw.line((385, 1135, 1115, 1065), fill=BLACK, width=24)
    elif spec.name == "星芒锁链":
        draw_chain(draw, 420)
        draw.regular_polygon((750, 760, 355), n_sides=8, rotation=math.pi / 8, fill=BLACK, outline=GOLD)
        draw.regular_polygon((750, 760, 270), n_sides=8, rotation=math.pi / 8, outline=CREAM, width=18)
        centered_text(draw, (750, 685), "STREET", impact, CREAM, BLACK, 14)
        centered_text(draw, (750, 890), "CODE", impact, RED, CREAM, 10)
    elif spec.name == "黑金徽章":
        draw_shield(draw, 750, 720)
        draw_crown(draw, 750, 355, 0.78, GOLD)
        centered_text(draw, (750, 650), "NO", font("GOTHICB.TTF", 215), CREAM, BLACK, 10)
        centered_text(draw, (750, 860), "LIMIT", fit_font("LIMIT", "impact.ttf", 520, 220), GOLD, BLACK, 10)
    elif spec.name == "街头字标":
        for x, h in [(410, 340), (510, 455), (630, 285), (845, 420), (965, 300), (1075, 500)]:
            draw.rectangle((x, 390 + (500 - h), x + 80, 890), fill=BLACK)
            draw.rectangle((x + 12, 390 + (500 - h) + 24, x + 68, 890), outline=CREAM, width=4)
        draw_splatter(draw, rng, (750, 840), 470, RED)
        centered_text(draw, (750, 790), "CITY", impact, WHITE, BLACK, 22)
        centered_text(draw, (750, 1015), "FLOW", impact, RED, CREAM, 12)
        draw.line((315, 1120, 1200, 980), fill=BLACK, width=28)
    elif spec.name == "火焰唱片":
        draw_record(draw, 750, 745)
        draw_crown(draw, 750, 605, 0.55, GOLD)
        centered_text(draw, (750, 365), "NIGHT", impact, RED, CREAM, 10)
        centered_text(draw, (750, 1135), "BEAT", impact, RED, CREAM, 10)
        for i in range(12):
            ang = i * math.tau / 12
            x1 = 750 + int(math.cos(ang) * 430)
            y1 = 745 + int(math.sin(ang) * 430)
            x2 = 750 + int(math.cos(ang) * 500)
            y2 = 745 + int(math.sin(ang) * 500)
            draw.line((x1, y1, x2, y2), fill=RED if i % 2 else GOLD, width=14)

    crop_and_save(img, path)


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 42
    sheet = Image.new("RGB", (tile * len(paths), tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 36, tile - 36), Image.Resampling.LANCZOS)
        x = index * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((index * tile + 16, tile + 10), path.stem, fill=BLACK[:3])
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render local high street hip hop print tests only.")
    parser.add_argument("--start", type=int, default=706)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026061220)
    parser.add_argument("--date", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = ["皇冠涂鸦", "星芒锁链", "黑金徽章", "街头字标", "火焰唱片"]
    titles = ["KING VIBE", "STREET CODE", "NO LIMIT", "CITY FLOW", "NIGHT BEAT"]
    if args.count > len(names):
        raise ValueError(f"Only {len(names)} local test specs are available.")

    out_dir = output_dir(args.start, args.count, args.date)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = [
        PrintSpec(f"BO-{args.start + index}", names[index], titles[index])
        for index in range(args.count)
    ]
    paths: list[Path] = []
    for index, spec in enumerate(items):
        path = out_dir / f"{spec.sku}.png"
        render(spec, path, args.seed + index)
        paths.append(path)
        print(f"{spec.sku}: rendered {spec.name} -> {path}")

    make_overview(paths, out_dir / "_prints_overview.jpg")
    prompt_file(args.start, args.count, args.date).write_text(
        "\n".join(
            [
                "高街嘻哈印花测试，本地可控渲染。",
                "元素：皇冠、链条、徽章、涂鸦字标、唱片；透明底；不生成衣服、人物、真实品牌 Logo。",
                "",
                *[f"{spec.sku}: {spec.name} / {spec.title}" for spec in items],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Print dir: {out_dir}")
    print(f"Overview: {out_dir / '_prints_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
