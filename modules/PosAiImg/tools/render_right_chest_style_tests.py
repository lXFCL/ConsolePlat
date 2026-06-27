from __future__ import annotations

import argparse
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "模特图-干净"

BLACK = (16, 16, 16, 255)
WHITE = (255, 255, 255, 255)
CREAM = (246, 238, 218, 255)
RED = (203, 38, 42, 255)
BLUE = (45, 84, 150, 255)
GREEN = (64, 119, 86, 255)
GOLD = (196, 148, 67, 255)
GRAY = (96, 96, 96, 255)
PINK = (218, 91, 133, 255)
CYAN = (38, 190, 204, 255)


@dataclass(frozen=True)
class Style:
    key: str
    zh: str
    note: str


STYLES = [
    Style("type_badge", "字标小章", "小字标、缩写、短语、下划线，适合右胸小标。"),
    Style("retro_sport", "复古运动徽章", "校队感、数字、星星、盾牌，偏美式复古。"),
    Style("organic_mark", "自然地貌线标", "山线、叶片、太阳、等高线，柔和生活方式感。"),
    Style("playful_dot", "波点趣味符号", "波点、花形、笑脸、圆点阵，轻松年轻。"),
    Style("animal_abstract", "动物纹抽象章", "斑点、虎纹、斑马纹做成抽象小章。"),
    Style("y2k_glitch", "Y2K故障电码", "像素、故障切片、数字电码，偏机能科技。"),
]


def safe_name(text: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE).strip("_")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return ImageFont.truetype(str(path), size=size)


def text_center(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke_fill: tuple[int, int, int, int] = WHITE,
    stroke_width: int = 7,
) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)
    w = box[2] - box[0]
    h = box[3] - box[1]
    x = xy[0] - w // 2
    y = xy[1] - h // 2
    draw.text((x, y), text, font=fnt, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
    return (x, y, x + w, y + h)


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r1: int, r2: int, fill: tuple[int, int, int, int]) -> None:
    pts = []
    for i in range(10):
        r = r1 if i % 2 == 0 else r2
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + int(math.cos(a) * r), cy + int(math.sin(a) * r)))
    draw.polygon(pts, fill=fill)


def draw_leaf(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, color: tuple[int, int, int, int]) -> None:
    w = int(145 * scale)
    h = int(270 * scale)
    draw.ellipse((cx - w, cy - h, cx + w, cy + h), outline=color, width=max(5, int(11 * scale)))
    draw.line((cx, cy + h, cx, cy - h), fill=color, width=max(4, int(8 * scale)))
    for offset in (-75, -35, 10, 50):
        yy = cy + int(offset * scale)
        draw.line((cx, yy, cx + int(75 * scale), yy - int(45 * scale)), fill=color, width=max(3, int(5 * scale)))
        draw.line((cx, yy, cx - int(75 * scale), yy - int(45 * scale)), fill=color, width=max(3, int(5 * scale)))


def crop_save(img: Image.Image, path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 46
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


def render_type_badge(draw: ImageDraw.ImageDraw, i: int) -> None:
    words = [("NOVA", "CLUB"), ("LOCAL", "DAY"), ("SLOW", "RUN"), ("OPEN", "AIR"), ("GOOD", "NOISE")]
    a, b = words[i]
    accent = [RED, BLUE, GREEN, GOLD, PINK][i]
    text_center(draw, (500, 380), a, font("impact.ttf", 190), BLACK, CREAM, 10)
    text_center(draw, (500, 575), b, font("GOTHICB.TTF", 116), accent, WHITE, 7)
    draw.rounded_rectangle((230, 690, 770, 735), radius=22, fill=BLACK)
    for x in range(290, 725, 78):
        draw.ellipse((x - 11, 760, x + 11, 782), fill=accent)


def render_retro_sport(draw: ImageDraw.ImageDraw, i: int) -> None:
    nums = ["07", "14", "23", "86", "99"]
    names = ["VARSITY", "TRACK", "FIELD", "RALLY", "LEAGUE"]
    accent = [BLUE, RED, GREEN, GOLD, GRAY][i]
    draw.rounded_rectangle((250, 215, 750, 785), radius=70, fill=CREAM, outline=BLACK, width=18)
    draw.rounded_rectangle((305, 280, 695, 720), radius=46, fill=BLACK, outline=accent, width=14)
    text_center(draw, (500, 455), nums[i], font("impact.ttf", 240), CREAM, BLACK, 8)
    text_center(draw, (500, 650), names[i], font("GOTHICB.TTF", 78), accent, CREAM, 5)
    draw_star(draw, 315, 230, 40, 17, accent)
    draw_star(draw, 685, 230, 40, 17, accent)


def render_organic_mark(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["RIDGE", "ROOT", "TIDE", "MOSS", "SUN"]
    colors = [GREEN, GOLD, BLUE, (94, 126, 73, 255), RED]
    color = colors[i]
    draw.rounded_rectangle((215, 235, 785, 765), radius=105, outline=color, width=18)
    for y in [380, 445, 515]:
        pts = [(250, y), (365, y - 60), (480, y - 18), (610, y - 90), (750, y - 28)]
        draw.line(pts, fill=BLACK, width=13, joint="curve")
    draw_leaf(draw, 500, 400, 0.42, color)
    draw.arc((360, 295, 640, 575), 205, 335, fill=GOLD, width=15)
    text_center(draw, (500, 690), labels[i], font("GOTHICB.TTF", 88), BLACK, WHITE, 6)


def render_playful_dot(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["DOT", "LUCK", "POP", "HOLA", "JOY"]
    colors = [(BLACK, RED), (BLUE, PINK), (GREEN, GOLD), (BLACK, CYAN), (RED, GOLD)]
    main, accent = colors[i]
    rng = random.Random(900 + i)
    for _ in range(42):
        x = rng.randint(250, 750)
        y = rng.randint(230, 750)
        r = rng.randint(9, 28)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=accent if rng.random() < 0.5 else main)
    draw.ellipse((318, 310, 682, 674), fill=CREAM, outline=BLACK, width=16)
    draw.arc((390, 405, 610, 570), 20, 160, fill=BLACK, width=16)
    draw.ellipse((400, 395, 445, 440), fill=BLACK)
    draw.ellipse((555, 395, 600, 440), fill=BLACK)
    text_center(draw, (500, 690), labels[i], font("impact.ttf", 110), accent, WHITE, 7)


def render_animal_abstract(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["SPOT", "ZEBRA", "TIGER", "CROC", "WILD"]
    draw.rounded_rectangle((245, 245, 755, 755), radius=92, fill=CREAM, outline=BLACK, width=16)
    rng = random.Random(1500 + i)
    if i in (0, 4):
        for _ in range(24):
            x = rng.randint(300, 700)
            y = rng.randint(300, 610)
            rx = rng.randint(18, 48)
            ry = rng.randint(14, 42)
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=BLACK)
    elif i == 1:
        for x in range(280, 740, 70):
            draw.line((x, 280, x + rng.randint(-80, 80), 645), fill=BLACK, width=rng.randint(18, 34))
    elif i == 2:
        for y in range(295, 630, 58):
            draw.line((290, y, 720, y + rng.randint(-55, 55)), fill=BLACK, width=22)
            draw.polygon([(310, y), (370, y + 42), (290, y + 62)], fill=GOLD)
    else:
        for y in range(300, 625, 62):
            for x in range(300, 710, 84):
                draw.rounded_rectangle((x, y, x + 58, y + 38), radius=13, outline=BLACK, width=8)
    text_center(draw, (500, 695), labels[i], font("impact.ttf", 116), RED if i == 2 else BLACK, WHITE, 7)


def render_y2k_glitch(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["SYNC", "404", "BYTE", "CTRL", "VOID"]
    accent = [CYAN, RED, BLUE, PINK, GREEN][i]
    rng = random.Random(2400 + i)
    for _ in range(26):
        x = rng.randint(250, 720)
        y = rng.randint(250, 760)
        w = rng.randint(18, 85)
        h = rng.randint(8, 28)
        draw.rectangle((x, y, x + w, y + h), fill=accent if rng.random() < 0.45 else BLACK)
    draw.rounded_rectangle((285, 325, 715, 675), radius=44, outline=BLACK, width=15)
    text_center(draw, (500, 495), labels[i], font("impact.ttf", 160), BLACK, WHITE, 9)
    draw.line((260, 575, 735, 520), fill=accent, width=18)
    draw.line((310, 620, 690, 665), fill=BLACK, width=12)


RENDERERS = {
    "type_badge": render_type_badge,
    "retro_sport": render_retro_sport,
    "organic_mark": render_organic_mark,
    "playful_dot": render_playful_dot,
    "animal_abstract": render_animal_abstract,
    "y2k_glitch": render_y2k_glitch,
}


def render_print(style: Style, index: int, path: Path) -> None:
    img = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    RENDERERS[style.key](draw, index)
    crop_save(img, path)


def make_overview(paths: list[tuple[Style, Path]], output_path: Path, title: str) -> None:
    tile_w, tile_h = 240, 260
    label_h = 34
    cols = 5
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h) + 44), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 14), title, fill=(0, 0, 0))
    for idx, (_style, path) in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile_w - 28, tile_h - 28), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile_w
        y0 = 44 + (idx // cols) * (tile_h + label_h)
        sheet.paste(preview, (x0 + (tile_w - preview.width) // 2, y0 + (tile_h - preview.height) // 2))
        draw.text((x0 + 10, y0 + tile_h + 6), path.stem[:28], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def make_right_chest_mockups(print_paths: list[tuple[Style, Path]], output_dir: Path, seed: int) -> list[tuple[Style, Path]]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(
        center_x=0.62,
        center_y=0.31,
        width=0.16,
        opacity=0.97,
        rotation=0.0,
        shadow_strength=0.16,
        wave_strength=0.004,
        remove_white_bg=False,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[Style, Path]] = []
    for idx, (style, print_path) in enumerate(print_paths):
        model = rng.choice(models)
        out = output_dir / f"{print_path.stem}_right_chest_preview.png"
        composite_one(model, print_path, out, placement)
        outputs.append((style, out))
        print(f"preview {idx + 1:02d}: {out}")
    return outputs


def write_notes(styles: list[Style], output_path: Path) -> None:
    lines = [
        "右胸小面积印花风格测试。",
        "只生成测试透明底印花和右胸位置预览；不更新货号、不生成 xlsx、不复制到上架目录。",
        "",
    ]
    lines.extend(f"- {style.zh}：{style.note}" for style in styles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render right-chest print style tests.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--per-style", type=int, default=5)
    parser.add_argument("--styles", type=int, default=6, choices=range(5, 9))
    parser.add_argument("--seed", type=int, default=2026061230)
    parser.add_argument("--skip-mockups", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = STYLES[: args.styles]
    stamp = args.date
    base_name = f"右胸印花风格测试_{stamp}"
    print_root = ROOT / "印花图_透明底" / base_name
    preview_root = ROOT / "AI印花贴图测试" / f"{base_name}_右胸预览"
    notes_path = ROOT / "生成提示词" / f"{base_name}.txt"
    print_paths: list[tuple[Style, Path]] = []

    for style in selected:
        style_dir = print_root / style.zh
        for i in range(args.per_style):
            name = f"{style.key}_{i + 1:02d}"
            path = style_dir / f"{name}.png"
            render_print(style, i, path)
            print_paths.append((style, path))
            print(f"print {style.zh} {i + 1}: {path}")

    make_overview(print_paths, print_root / "_all_prints_overview.jpg", "right chest print style tests")
    write_notes(selected, notes_path)

    if not args.skip_mockups:
        previews = make_right_chest_mockups(print_paths, preview_root, args.seed)
        make_overview(previews, preview_root / "_right_chest_overview.jpg", "right chest placement preview")

    print(f"Print root: {print_root}")
    print(f"Preview root: {preview_root}")
    print(f"Notes: {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
