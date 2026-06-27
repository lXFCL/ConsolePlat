from __future__ import annotations

import argparse
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "模特图-干净"
PRINT_ROOT = ROOT / "印花图_透明底"
MOCKUP_ROOT = ROOT / "AI印花贴图测试"
PROMPT_ROOT = ROOT / "生成提示词"
FONT_DIR = Path("C:/Windows/Fonts")

BLACK = (18, 18, 18, 255)
INK = (28, 28, 26, 255)
WHITE = (255, 255, 255, 255)
CREAM = (246, 241, 225, 255)
RED = (198, 45, 43, 255)
BLUE = (45, 88, 160, 255)
GREEN = (55, 125, 88, 255)
GOLD = (196, 148, 67, 255)
PINK = (218, 92, 132, 255)
CYAN = (34, 178, 196, 255)


@dataclass(frozen=True)
class PrintSpec:
    key: str
    title: str
    note: str


SPECS = [
    PrintSpec("tiny_type", "小字母胸标", "小面积文字标，适合右胸"),
    PrintSpec("club_badge", "复古编号徽章", "短字母加编号，偏运动复古"),
    PrintSpec("botanical", "细线植物", "细线叶片和小花，日常感"),
    PrintSpec("mini_heart", "手绘爱心", "极简手绘符号"),
    PrintSpec("wave_word", "波浪短词", "弧形文字和小波浪"),
    PrintSpec("geo_square", "几何线框", "小方框线条，偏街头"),
    PrintSpec("sun_mark", "小太阳标", "圆形放射图形"),
    PrintSpec("pixel_tag", "像素标签", "小像素块与数字"),
    PrintSpec("script_mark", "手写短词", "轻手写感字标"),
    PrintSpec("leaf_number", "叶片编号", "自然元素加编号"),
]


def safe_name(text: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE).strip("_") or "image"


def font(candidates: list[str], size: int) -> ImageFont.ImageFont:
    for name in candidates:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.ImageFont,
             fill: tuple[int, int, int, int], stroke_fill: tuple[int, int, int, int] = WHITE,
             stroke_width: int = 5, anchor: str = "mm") -> None:
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor, stroke_fill=stroke_fill, stroke_width=stroke_width)


def star_points(cx: int, cy: int, outer: int, inner: int, points: int = 5) -> list[tuple[int, int]]:
    coords = []
    for i in range(points * 2):
        radius = outer if i % 2 == 0 else inner
        angle = -math.pi / 2 + i * math.pi / points
        coords.append((cx + int(math.cos(angle) * radius), cy + int(math.sin(angle) * radius)))
    return coords


def crop_save(img: Image.Image, output_path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 38
        img = img.crop((
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(img.width, bbox[2] + pad),
            min(img.height, bbox[3] + pad),
        ))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def draw_tiny_type(draw: ImageDraw.ImageDraw) -> None:
    text_box(draw, (500, 405), "LITTLE", font(["GOTHICB.TTF", "arialbd.ttf"], 104), INK, CREAM, 8)
    text_box(draw, (500, 520), "DAY", font(["impact.ttf", "arialbd.ttf"], 178), BLACK, WHITE, 8)
    draw.rounded_rectangle((320, 625, 680, 665), radius=18, fill=RED)
    draw.line((370, 710, 630, 710), fill=BLACK, width=12)


def draw_club_badge(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((280, 260, 720, 740), radius=76, fill=CREAM, outline=BLACK, width=18)
    draw.rounded_rectangle((340, 325, 660, 675), radius=44, outline=RED, width=14)
    text_box(draw, (500, 445), "27", font(["impact.ttf", "arialbd.ttf"], 208), BLACK, CREAM, 5)
    text_box(draw, (500, 610), "LOCAL", font(["GOTHICB.TTF", "arialbd.ttf"], 70), RED, WHITE, 5)
    draw.polygon(star_points(320, 275, 34, 13), fill=GOLD)
    draw.polygon(star_points(680, 275, 34, 13), fill=GOLD)


def draw_botanical(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((285, 265, 715, 760), radius=80, fill=CREAM, outline=BLACK, width=8)
    draw.line((410, 680, 545, 315), fill=BLACK, width=13)
    for y, side in [(610, -1), (555, 1), (500, -1), (445, 1), (392, -1)]:
        x = int(498 + side * 24)
        if side < 0:
            box = (x - 95, y - 58, x + 16, y + 30)
        else:
            box = (x - 16, y - 58, x + 95, y + 30)
        draw.ellipse(box, outline=GREEN, width=11)
    for cx, cy in [(620, 405), (652, 460), (595, 485)]:
        draw.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), outline=BLACK, width=8)
    text_box(draw, (500, 735), "BLOOM", font(["GOTHICB.TTF", "arialbd.ttf"], 68), BLACK, WHITE, 5)


def draw_mini_heart(draw: ImageDraw.ImageDraw) -> None:
    draw.line((500, 705, 500, 360), fill=BLACK, width=11)
    draw.arc((340, 300, 506, 505), 205, 55, fill=RED, width=28)
    draw.arc((494, 300, 660, 505), 125, 335, fill=RED, width=28)
    draw.line((355, 438, 500, 620), fill=RED, width=28)
    draw.line((645, 438, 500, 620), fill=RED, width=28)
    text_box(draw, (500, 760), "tiny mood", font(["segoepr.ttf", "arial.ttf"], 58), BLACK, WHITE, 4)


def draw_wave_word(draw: ImageDraw.ImageDraw) -> None:
    for idx, y in enumerate([405, 465, 525]):
        pts = []
        for x in range(270, 731, 18):
            pts.append((x, y + int(math.sin((x + idx * 25) / 42) * 22)))
        draw.line(pts, fill=[BLUE, BLACK, CYAN][idx], width=13)
    text_box(draw, (500, 640), "SLOW", font(["impact.ttf", "arialbd.ttf"], 150), BLACK, WHITE, 8)
    text_box(draw, (500, 760), "WAVE", font(["GOTHICB.TTF", "arialbd.ttf"], 60), BLUE, WHITE, 4)


def draw_geo_square(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((278, 278, 722, 760), radius=26, fill=CREAM)
    for offset, color in [(0, BLACK), (35, GOLD), (70, BLACK)]:
        draw.rounded_rectangle((300 + offset, 305 + offset, 700 - offset, 705 - offset), radius=18, outline=color, width=12)
    for i in range(8):
        y = 365 + i * 38
        draw.line((360, y, 640, y + (18 if i % 2 else -18)), fill=BLACK, width=6)
    text_box(draw, (500, 755), "LINE", font(["impact.ttf", "arialbd.ttf"], 82), BLACK, WHITE, 5)


def draw_sun_mark(draw: ImageDraw.ImageDraw) -> None:
    for i in range(20):
        angle = i * math.tau / 20
        x1 = 500 + int(math.cos(angle) * 155)
        y1 = 485 + int(math.sin(angle) * 155)
        x2 = 500 + int(math.cos(angle) * 245)
        y2 = 485 + int(math.sin(angle) * 245)
        draw.line((x1, y1, x2, y2), fill=GOLD if i % 2 else BLACK, width=12)
    draw.ellipse((345, 330, 655, 640), fill=CREAM, outline=BLACK, width=16)
    text_box(draw, (500, 495), "SUN", font(["impact.ttf", "arialbd.ttf"], 132), BLACK, WHITE, 5)
    text_box(draw, (500, 725), "DAILY", font(["GOTHICB.TTF", "arialbd.ttf"], 62), GOLD, WHITE, 4)


def draw_pixel_tag(draw: ImageDraw.ImageDraw) -> None:
    rng = random.Random(618)
    for _ in range(28):
        x = rng.randrange(295, 690, 28)
        y = rng.randrange(300, 650, 28)
        color = CYAN if rng.random() < 0.36 else BLACK
        draw.rectangle((x, y, x + 24, y + 24), fill=color)
    draw.rounded_rectangle((330, 390, 670, 620), radius=24, fill=CREAM, outline=BLACK, width=13)
    text_box(draw, (500, 505), "404", font(["impact.ttf", "arialbd.ttf"], 150), BLACK, WHITE, 6)
    text_box(draw, (500, 720), "BYTE", font(["GOTHICB.TTF", "arialbd.ttf"], 68), CYAN, WHITE, 5)


def draw_script_mark(draw: ImageDraw.ImageDraw) -> None:
    text_box(draw, (500, 470), "mellow", font(["segoesc.ttf", "segoepr.ttf", "ariali.ttf"], 122), BLACK, WHITE, 7)
    draw.arc((270, 475, 730, 720), 185, 355, fill=PINK, width=14)
    for cx in [345, 500, 655]:
        draw.ellipse((cx - 18, 685, cx + 18, 721), fill=BLACK)
    text_box(draw, (500, 760), "small sign", font(["GOTHICB.TTF", "arialbd.ttf"], 50), PINK, WHITE, 4)


def draw_leaf_number(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((295, 280, 705, 720), radius=90, fill=CREAM, outline=BLACK, width=16)
    text_box(draw, (500, 450), "08", font(["impact.ttf", "arialbd.ttf"], 190), BLACK, CREAM, 7)
    draw.line((385, 635, 610, 535), fill=GREEN, width=12)
    for x, y, side in [(430, 615, -1), (485, 590, 1), (545, 562, -1), (590, 542, 1)]:
        draw.ellipse((x - 55 if side < 0 else x, y - 36, x if side < 0 else x + 55, y + 22), outline=GREEN, width=8)
    text_box(draw, (500, 745), "ROOT", font(["GOTHICB.TTF", "arialbd.ttf"], 58), GREEN, WHITE, 4)


DRAWERS = [
    draw_tiny_type,
    draw_club_badge,
    draw_botanical,
    draw_mini_heart,
    draw_wave_word,
    draw_geo_square,
    draw_sun_mark,
    draw_pixel_tag,
    draw_script_mark,
    draw_leaf_number,
]


def render_prints(output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for index, (spec, drawer) in enumerate(zip(SPECS, DRAWERS, strict=True), start=1):
        img = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        drawer(draw)
        output_path = output_dir / f"{index:02d}_{spec.key}_{spec.title}.png"
        crop_save(img, output_path)
        paths.append(output_path)
        print(f"print {index:02d}: {output_path}")
    return paths


def make_overview(image_paths: list[Path], output_path: Path, title: str) -> None:
    cols = 5
    tile_w, tile_h = 260, 270
    label_h = 42
    rows = (len(image_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, 48 + rows * (tile_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 16), title, fill=(0, 0, 0))
    for idx, path in enumerate(image_paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile_w - 28, tile_h - 28), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile_w
        y0 = 48 + (idx // cols) * (tile_h + label_h)
        sheet.paste(preview, (x0 + (tile_w - preview.width) // 2, y0 + (tile_h - preview.height) // 2))
        draw.text((x0 + 10, y0 + tile_h + 8), path.stem[:30], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def make_mockups(print_paths: list[Path], output_dir: Path, seed: int) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    placement = Placement(
        center_x=0.62,
        center_y=0.32,
        width=0.115,
        opacity=0.98,
        rotation=0.0,
        shadow_strength=0.16,
        wave_strength=0.003,
        remove_white_bg=False,
    )

    outputs: list[Path] = []
    for index, print_path in enumerate(print_paths, start=1):
        model_path = rng.choice(models)
        output_path = output_dir / f"{index:02d}_{safe_name(model_path.stem)}__{safe_name(print_path.stem)}_右上胸小印花.png"
        composite_one(model_path, print_path, output_path, placement)
        outputs.append(output_path)
        print(f"mockup {index:02d}: {output_path}")
    return outputs


def write_notes(output_path: Path, print_dir: Path, mockup_dir: Path) -> None:
    lines = [
        "右上胸小印花 10 张测试",
        "",
        "联网参考后的取向：小面积胸标、短字母/编号、细线植物、极简符号、几何标签。避免复杂大图，因为贴到右上胸后尺寸较小，细节容易糊。",
        "",
        "贴图参数：center_x=0.62, center_y=0.32, width=0.115, opacity=0.98, shadow_strength=0.16, wave_strength=0.003。",
        f"透明底印花目录：{print_dir}",
        f"主图贴图目录：{mockup_dir}",
        "",
    ]
    lines.extend(f"{idx:02d}. {spec.title}：{spec.note}" for idx, spec in enumerate(SPECS, start=1))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render 10 small right upper chest print tests on main product images.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d_%H%M"))
    parser.add_argument("--seed", type=int, default=2026061319)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batch_name = f"右上胸小印花10张测试_{args.date}"
    print_dir = PRINT_ROOT / batch_name
    mockup_dir = MOCKUP_ROOT / f"{batch_name}_主图贴图"
    notes_path = PROMPT_ROOT / f"{batch_name}.txt"

    print_paths = render_prints(print_dir)
    make_overview(print_paths, print_dir / "_prints_overview.jpg", "small right chest transparent prints")

    mockup_paths = make_mockups(print_paths, mockup_dir, args.seed)
    make_overview(mockup_paths, mockup_dir / "_mockups_overview.jpg", "small right upper chest mockups")
    write_notes(notes_path, print_dir, mockup_dir)

    print(f"Prints: {print_dir}")
    print(f"Mockups: {mockup_dir}")
    print(f"Notes: {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
