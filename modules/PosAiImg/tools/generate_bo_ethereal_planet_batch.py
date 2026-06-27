from __future__ import annotations

import argparse
import math
import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from generate_bo_ethereal_line_batch import (
        MODEL_DIR,
        Placement,
        blank,
        line,
        list_images,
        make_overview,
        safe_filename,
        shirt_color,
        star,
        stroked_arc,
        stroked_ellipse,
        write_xlsx,
        validate,
    )
except ModuleNotFoundError:
    from tools.generate_bo_ethereal_line_batch import (
        MODEL_DIR,
        Placement,
        blank,
        line,
        list_images,
        make_overview,
        safe_filename,
        shirt_color,
        star,
        stroked_arc,
        stroked_ellipse,
        write_xlsx,
        validate,
    )
from tshirt_print_tool import composite_one


ROOT = Path(__file__).resolve().parents[1]
BATCH_STYLE = "空灵星球线条印花"


@dataclass(frozen=True)
class Paths:
    print_dir: Path
    product_dir: Path
    prompt_file: Path
    output_xlsx: Path


MOTIFS = [
    "星环行星",
    "月相轨道",
    "日食光环",
    "星座图谱",
    "彗星轨迹",
    "银河漩涡",
    "双星环绕",
    "星球地平线",
    "小行星带",
    "宇宙门户",
]

TITLE_SUFFIXES = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]

DARKS = [(28, 35, 47, 245), (43, 45, 53, 245), (35, 50, 52, 245)]
LIGHTS = [(242, 238, 220, 245), (246, 242, 230, 245), (236, 240, 230, 245)]
ACCENTS = [(93, 190, 198, 225), (158, 140, 220, 220), (210, 195, 150, 225), (132, 184, 164, 220)]


def batch_name(start: int, count: int, batch_date: str | None = None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"{BATCH_STYLE}_BO-{start}-BO-{end}_{stamp}"


def batch_paths(start: int, count: int, batch_date: str | None = None) -> Paths:
    name = batch_name(start, count, batch_date)
    return Paths(
        print_dir=ROOT / "印花图_透明底" / name,
        product_dir=ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        prompt_file=ROOT / "生成提示词" / f"{name}.txt",
        output_xlsx=ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def palette(index: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
    return DARKS[index % len(DARKS)], LIGHTS[index % len(LIGHTS)], ACCENTS[index % len(ACCENTS)], ACCENTS[(index + 2) % len(ACCENTS)]


def pts_wave(x0: int, x1: int, y: float, amp: float, period: float, phase: float) -> list[tuple[float, float]]:
    pts = []
    for x in range(x0, x1 + 1, 10):
        env = math.sin(math.pi * (x - x0) / max(1, x1 - x0))
        pts.append((x, y + math.sin(x / period + phase) * amp * env))
    return pts


def stroked_circle(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, dark: tuple[int, int, int, int], light: tuple[int, int, int, int], accent: tuple[int, int, int, int] | None = None, inner_w: int = 9, outer_w: int = 20) -> None:
    box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    stroked_ellipse(draw, box, dark, light, inner_w, outer_w, accent, 4)


def planet_fill(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, dark: tuple[int, int, int, int], light: tuple[int, int, int, int], accent: tuple[int, int, int, int]) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=light)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=dark, width=12)
    for offset in (-0.32, 0.02, 0.33):
        y = cy + r * offset
        line(draw, pts_wave(int(cx - r * 0.68), int(cx + r * 0.68), y, r * 0.045, 52, offset * 4), dark, light, 5, 12, accent, 3)


def render_print(sku: str, index: int, output_dir: Path) -> Path:
    rng = random.Random(2026061400 + index * 97)
    img = blank()
    draw = ImageDraw.Draw(img, "RGBA")
    dark, light, accent, accent2 = palette(index)
    cx = 1300 + rng.randint(-70, 70)
    cy = 1240 + rng.randint(-70, 55)
    motif = index % 10

    if motif == 0:
        r = 230 + rng.randint(-25, 25)
        planet_fill(draw, cx, cy, r, dark, light, accent)
        for i in range(4):
            stroked_arc(draw, cx, cy + i * 18, 670 + i * 38, 145 + i * 16, 190, 350, dark, light, 8, 18, accent2 if i % 2 else accent, 4)
        for deg in range(0, 360, 45):
            star(draw, cx + math.cos(math.radians(deg)) * 610, cy + math.sin(math.radians(deg)) * 310, 10, light if deg % 90 else accent)

    elif motif == 1:
        x0 = cx - 570
        for i in range(7):
            r = 48 + i * 9
            x = x0 + i * 190
            draw.ellipse((x - r, cy - r, x + r, cy + r), fill=light if i in (0, 3, 6) else (0, 0, 0, 0), outline=dark, width=9)
            if i not in (0, 3, 6):
                draw.arc((x - r, cy - r, x + r, cy + r), 80, 280, fill=light, width=16)
                draw.arc((x - r, cy - r, x + r, cy + r), 80, 280, fill=dark, width=7)
        for i in range(5):
            stroked_arc(draw, cx, cy + 40, 700 - i * 70, 205 - i * 18, 202, 338, dark, light, 7, 16, accent if i % 2 == 0 else None, 3)
        star(draw, cx, cy - 310, 18, accent2)

    elif motif == 2:
        for r in [430, 335, 250]:
            stroked_circle(draw, cx, cy, r, dark, light, accent if r == 430 else None, 9, 20)
        draw.ellipse((cx - 165, cy - 165, cx + 165, cy + 165), fill=dark)
        draw.ellipse((cx - 96, cy - 96, cx + 96, cy + 96), fill=light)
        for i in range(10):
            angle = i * 36 + rng.randint(-5, 5)
            line(
                draw,
                [
                    (cx + math.cos(math.radians(angle)) * 505, cy + math.sin(math.radians(angle)) * 505),
                    (cx + math.cos(math.radians(angle)) * 615, cy + math.sin(math.radians(angle)) * 615),
                ],
                dark,
                light,
                7,
                15,
                accent2 if i % 2 else None,
                3,
            )

    elif motif == 3:
        points = []
        for _ in range(9):
            points.append((rng.randint(610, 1990), rng.randint(680, 1650)))
        points.sort()
        for a, b in zip(points, points[1:]):
            line(draw, [a, b], dark, light, 6, 14, accent, 3)
        for idx, (x, y) in enumerate(points):
            star(draw, x, y, 18 if idx in (0, len(points) - 1) else 12, light if idx % 2 else accent2)
        for i in range(4):
            stroked_arc(draw, cx, cy, 640 - i * 80, 270 - i * 22, 205, 335, dark, light, 6, 14, None)

    elif motif == 4:
        for i in range(7):
            stroked_arc(draw, cx - 120 + i * 12, cy + i * 18, 520 + i * 62, 160 + i * 20, 190, 348, dark, light, 7, 16, accent if i % 2 == 0 else None, 3)
        head_x = cx - 420 + rng.randint(-50, 40)
        head_y = cy - 155 + rng.randint(-30, 30)
        draw.ellipse((head_x - 82, head_y - 82, head_x + 82, head_y + 82), fill=light)
        draw.ellipse((head_x - 82, head_y - 82, head_x + 82, head_y + 82), outline=dark, width=10)
        for i in range(14):
            star(draw, cx + rng.randint(-670, 690), cy + rng.randint(-400, 440), rng.choice([7, 9, 11]), rng.choice([light, accent, accent2]))

    elif motif == 5:
        for i in range(9):
            a0 = 25 + i * 14
            a1 = 320 - i * 6
            stroked_arc(draw, cx, cy, 120 + i * 75, 58 + i * 39, a0, a1, dark, light, 7, 16, accent if i in (2, 5, 8) else None, 3)
        draw.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), fill=light)
        draw.ellipse((cx - 35, cy - 35, cx + 35, cy + 35), outline=dark, width=8)
        for _ in range(30):
            star(draw, rng.randint(560, 2040), rng.randint(650, 1680), rng.choice([7, 10, 13]), rng.choice([light, accent2]))

    elif motif == 6:
        planet_fill(draw, cx - 230, cy + 10, 145, dark, light, accent)
        planet_fill(draw, cx + 265, cy - 95, 105, dark, light, accent2)
        for i in range(7):
            stroked_arc(draw, cx, cy, 760 - i * 66, 250 - i * 18, 190, 350, dark, light, 7, 16, accent if i % 3 == 0 else None, 3)
        for deg in range(30, 360, 60):
            star(draw, cx + math.cos(math.radians(deg)) * 680, cy + math.sin(math.radians(deg)) * 365, 10, light)

    elif motif == 7:
        for i in range(8):
            y = cy + i * 42
            line(draw, pts_wave(520, 2080, y, 24 + i * 2, 82 + i * 4, i * 0.5), dark, light, 8, 18, accent if i % 2 else None, 3)
        draw.ellipse((cx - 225, cy - 340, cx + 225, cy + 110), fill=light)
        draw.rectangle((cx - 250, cy - 115, cx + 250, cy + 125), fill=(0, 0, 0, 0))
        draw.arc((cx - 225, cy - 340, cx + 225, cy + 110), 180, 360, fill=dark, width=12)
        for i in range(4):
            stroked_arc(draw, cx, cy + 130 + i * 36, 520 + i * 70, 125 + i * 18, 190, 350, dark, light, 6, 14, accent2 if i == 1 else None, 3)

    elif motif == 8:
        stroked_circle(draw, cx, cy, 235, dark, light, accent, 10, 22)
        for i in range(4):
            stroked_arc(draw, cx, cy + i * 16, 760 + i * 35, 145 + i * 20, 190, 350, dark, light, 7, 16, accent2 if i % 2 else None, 3)
        for i in range(26):
            angle = rng.uniform(190, 350)
            rr = rng.uniform(470, 760)
            x = cx + math.cos(math.radians(angle)) * rr
            y = cy + math.sin(math.radians(angle)) * rr * 0.26
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=rng.choice([light, accent, accent2]))

    else:
        for r in [680, 540, 405, 275]:
            stroked_arc(draw, cx, cy, r, r * 0.55, 200, 340, dark, light, 8, 18, accent if r in (680, 405) else None, 3)
            stroked_arc(draw, cx, cy + 110, r, r * 0.55, 20, 160, dark, light, 7, 16, accent2 if r in (540, 275) else None, 3)
        planet_fill(draw, cx, cy + 10, 122, dark, light, accent)
        for i, width in enumerate([900, 680, 460]):
            y = cy + 300 + i * 80
            draw.rounded_rectangle((cx - width // 2, y, cx + width // 2, y + 18), radius=9, fill=light)
            draw.rounded_rectangle((cx - width // 2 + 8, y + 5, cx + width // 2 - 8, y + 13), radius=5, fill=dark)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{sku}.png"
    img.save(path)
    return path


def title_for(index: int, color: str) -> str:
    color_word = "白色" if color == "白" else "黑色"
    motif = MOTIFS[index % len(MOTIFS)]
    suffix = TITLE_SUFFIXES[index % len(TITLE_SUFFIXES)]
    return f"夏季{color_word}空灵星球{motif}印花T恤 {suffix}"


def write_prompt_file(paths: Paths, start: int, count: int) -> None:
    end = start + count - 1
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    paths.prompt_file.write_text(
        "\n".join(
            [
                f"{BATCH_STYLE} BO-{start}-BO-{end}",
                "风格：空灵、放松、沉浸，加入星球、星环、轨道、月相、日食、星座、彗星、银河等元素。",
                "要求：50 张之间主体明显变化，避免只改参数导致图案重复。",
                "黑白 T 通用：深色主线适配白 T，米白外描边适配黑 T，少量浅青/浅紫/柔金点缀。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run(start: int, count: int, seed: int, batch_date: str | None = None) -> tuple[Paths, dict[str, object]]:
    paths = batch_paths(start, count, batch_date)
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    write_prompt_file(paths, start, count)

    print_paths = [render_print(f"BO-{start + idx}", idx, paths.print_dir) for idx in range(count)]

    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    paths.product_dir.mkdir(parents=True, exist_ok=True)
    shuffled = print_paths[:]
    rng.shuffle(shuffled)
    product_paths = []
    for print_path in shuffled:
        sku = print_path.stem
        idx = int(sku.split("-")[1]) - start
        model_path = rng.choice(models)
        color = shirt_color(model_path)
        title = title_for(idx, color)
        output_path = paths.product_dir / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        product_paths.append(output_path)
        print(f"{sku}: {model_path.name} -> {output_path.name}")

    make_overview(product_paths, paths.product_dir / "_overview.jpg")
    write_xlsx(paths.product_dir, paths.output_xlsx, count)
    return paths, validate(paths, start, count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO ethereal planet line-art T-shirt prints, product images, and xlsx.")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--date", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths, report = run(args.start, args.count, args.seed, args.date)
    print(f"print_dir={paths.print_dir}")
    print(f"product_dir={paths.product_dir}")
    print(f"prompt_file={paths.prompt_file}")
    print(f"xlsx={paths.output_xlsx}")
    print(f"validate={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
