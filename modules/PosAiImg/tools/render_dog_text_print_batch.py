from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(r"C:\Windows\Fonts")
CANVAS_SIZE = (1400, 1400)
SCALE = 3

KOREAN_TEXTS = [
    "실수로 너무\n많이 먹었어요",
    "오늘도\n귀여워요",
    "조금만\n쉬어갈게요",
    "괜찮아\n천천히 해",
    "행복은\n작게 와요",
    "나는 지금\n충전 중",
    "귀여움\n주의보",
    "매일매일\n좋아져요",
    "기분 좋은\n하루",
    "멍멍\n괜찮아",
    "나랑 같이\n놀아요",
    "작고 소중한\n순간",
    "오늘은\n느긋하게",
    "마음은\n말랑말랑",
    "빵처럼\n포근해요",
    "조용히\n응원 중",
    "좋은 일이\n올 거예요",
    "잠깐만\n기다려요",
    "웃으면\n복이 와요",
    "너무 많이\n생각했어요",
    "오늘도\n잘했어요",
    "내 속도대로\n갈래요",
    "맛있는 게\n필요해요",
    "햇살 같은\n기분",
    "작은 용기\n큰 행복",
]

ENGLISH_TEXTS = [
    "TOO FULL\nTO MOVE",
    "SMALL DOG\nBIG MOOD",
    "SLOW DAY\nGOOD DAY",
    "NAP FIRST\nTHINK LATER",
    "SOFT HEART\nLOUD SNACKS",
    "STAY CUTE\nSTAY KIND",
    "TINY PAWS\nHUGE PLANS",
    "GOOD VIBES\nONLY",
    "I TRIED\nMY BEST",
    "SNACK MODE\nON",
    "LITTLE JOY\nCLUB",
    "PLEASE WAIT\nI AM LOADING",
    "COZY TODAY\nBRAVE TOMORROW",
    "NO RUSH\nJUST FLUFF",
    "HAPPY LITTLE\nMOMENT",
    "SEND NOODS\nAND NAPS",
    "QUIETLY\nCHEERING",
    "CUTE BUT\nTIRED",
    "ONE MORE\nSNACK",
    "SOFT DAYS\nAHEAD",
    "MOOD: ROUND\nAND READY",
    "HELLO FROM\nMY BLANKET",
    "BE KIND\nEAT WELL",
    "TINY BUT\nDRAMATIC",
    "CLOUDY DOG\nSUNNY HEART",
]


@dataclass(frozen=True)
class BatchResult:
    final_dir: Path
    test_dir: Path
    overview_path: Path
    manifest_path: Path


def default_output_root() -> Path:
    stamp = date.today().strftime("%Y%m%d")
    return ROOT / "图库" / "通用素材" / "2026" / "6月" / f"参考圆脸小狗韩英文字_50款_{stamp}"


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in candidates:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def fit_font(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    candidates: list[str],
    start_size: int,
    max_width: int,
    stroke_width: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(start_size, 42, -3):
        fnt = font(candidates, size)
        widths = [
            draw.textbbox((0, 0), line, font=fnt, stroke_width=stroke_width)[2]
            - draw.textbbox((0, 0), line, font=fnt, stroke_width=stroke_width)[0]
            for line in lines
        ]
        if max(widths, default=0) <= max_width:
            return fnt
    return font(candidates, 42)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    language: str,
    rng: random.Random,
) -> int:
    lines = text.splitlines()
    font_names = ["malgunbd.ttf", "malgun.ttf", "arialbd.ttf"] if language == "ko" else ["arialbd.ttf", "segoeui.ttf"]
    stroke = 6 * SCALE
    fnt = fit_font(draw, lines, font_names, 96 * SCALE, 820 * SCALE, stroke)
    line_gap = rng.randint(8, 20) * SCALE
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt, stroke_width=stroke)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    current_y = y
    for line, width, height in zip(lines, widths, heights):
        x = (CANVAS_SIZE[0] * SCALE - width) // 2 + rng.randint(-10, 10) * SCALE
        draw.text(
            (x, current_y),
            line,
            font=fnt,
            fill=(255, 255, 255, 255),
            stroke_width=stroke,
            stroke_fill=(18, 18, 18, 255),
        )
        current_y += height + line_gap
    return y + total_h


def ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline, width: int) -> None:
    box = tuple(v * SCALE for v in box)
    draw.ellipse(box, fill=fill, outline=outline, width=width * SCALE)


def line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, width: int) -> None:
    draw.line([(x * SCALE, y * SCALE) for x, y in points], fill=fill, width=width * SCALE, joint="curve")


def rounded_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline, width: int) -> None:
    draw.rounded_rectangle(
        tuple(v * SCALE for v in box),
        radius=radius * SCALE,
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def draw_puppy(draw: ImageDraw.ImageDraw, rng: random.Random, variant: int) -> None:
    cream = (255, 236, 201, 255)
    blush = (129, 180, 143, 135)
    black = (12, 12, 12, 255)
    stroke = 11

    cx = 700 + rng.randint(-16, 16)
    head_y = 720 + rng.randint(-10, 10)
    body_y = 990 + rng.randint(-8, 10)

    ellipse(draw, (cx - 255, head_y - 155, cx + 255, head_y + 168), cream, black, stroke)
    ellipse(draw, (cx - 292, head_y - 82, cx - 180, head_y + 40), cream, black, stroke)
    ellipse(draw, (cx + 180, head_y - 82, cx + 292, head_y + 40), cream, black, stroke)

    rounded_rectangle(draw, (cx - 265, body_y - 98, cx + 265, body_y + 112), 88, cream, black, stroke)
    line(draw, [(cx - 252, body_y - 90), (cx - 130, body_y - 118), (cx + 40, body_y - 116), (cx + 252, body_y - 84)], black, 10)

    eye_y = head_y + rng.randint(12, 24)
    ellipse(draw, (cx - 118, eye_y - 14, cx - 90, eye_y + 14), black, black, 1)
    ellipse(draw, (cx + 90, eye_y - 14, cx + 118, eye_y + 14), black, black, 1)
    ellipse(draw, (cx - 12, head_y + 72, cx + 12, head_y + 94), black, black, 1)
    line(draw, [(cx - 42, head_y + 105), (cx - 18, head_y + 122), (cx, head_y + 105), (cx + 18, head_y + 122), (cx + 42, head_y + 105)], black, 8)

    if variant % 4 == 0:
        line(draw, [(cx + 244, body_y - 34), (cx + 314, body_y - 100), (cx + 350, body_y - 30), (cx + 314, body_y + 30)], black, 11)
        ellipse(draw, (cx + 250, body_y - 4, cx + 326, body_y + 86), cream, black, stroke)
    elif variant % 4 == 1:
        ellipse(draw, (cx - 325, body_y - 8, cx - 252, body_y + 72), cream, black, stroke)
        line(draw, [(cx - 318, body_y + 18), (cx - 350, body_y - 8), (cx - 332, body_y - 42)], black, 9)
    elif variant % 4 == 2:
        rounded_rectangle(draw, (cx + 245, body_y - 12, cx + 326, body_y + 72), 38, cream, black, stroke)
        line(draw, [(cx + 292, body_y + 6), (cx + 342, body_y - 54)], black, 9)
    else:
        rounded_rectangle(draw, (cx - 326, body_y - 18, cx - 248, body_y + 58), 34, cream, black, stroke)
        line(draw, [(cx - 296, body_y - 18), (cx - 326, body_y - 64)], black, 8)

    for offset in (-54, 62):
        x = cx + offset + rng.randint(-5, 5)
        y = head_y + 88 + rng.randint(-3, 5)
        line(draw, [(x - 10, y + 18), (x + 8, y + 30)], blush, 5)


def make_print(text: str, language: str, seed: int, index: int) -> Image.Image:
    rng = random.Random(seed + index * 104729)
    canvas = Image.new("RGBA", (CANVAS_SIZE[0] * SCALE, CANVAS_SIZE[1] * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    text_bottom = draw_centered_text(draw, text, rng.randint(112, 142) * SCALE, language, rng)
    if text_bottom > 420 * SCALE:
        draw_centered_text(draw, text, 92 * SCALE, language, rng)
    draw_puppy(draw, rng, index)
    return canvas.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)


def make_checker_overview(paths: list[Path], output: Path) -> None:
    cols = 10
    tile_w, tile_h = 230, 275
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (242, 242, 242))
    label_font = font(["arial.ttf"], 12)
    for idx, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if bbox:
            img = img.crop(bbox)
        img.thumbnail((210, 220), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        td = ImageDraw.Draw(tile)
        for y in range(0, 230, 16):
            for x in range(0, tile_w, 16):
                fill = (232, 232, 232) if (x // 16 + y // 16) % 2 == 0 else (255, 255, 255)
                td.rectangle((x, y, x + 15, y + 15), fill=fill)
        tile.paste(img, ((tile_w - img.width) // 2, (230 - img.height) // 2), img)
        td.text((6, 240), path.stem, fill=(0, 0, 0), font=label_font)
        sheet.paste(tile, ((idx % cols) * tile_w, (idx // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def generate_batch(output_root: Path, count: int = 50, seed: int = 20260618) -> BatchResult:
    if count < 1:
        raise ValueError("count must be positive")
    final_dir = output_root / "最终透明底"
    test_dir = output_root / "测试"
    final_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    texts = [("ko", text) for text in KOREAN_TEXTS] + [("en", text) for text in ENGLISH_TEXTS]
    rng.shuffle(texts)
    selected = [texts[i % len(texts)] for i in range(count)]

    outputs: list[Path] = []
    manifest_lines = ["file\tlanguage\ttext"]
    for index, (language, text) in enumerate(selected, 1):
        image = make_print(text, language, seed, index)
        output = final_dir / f"dog_text_{index:02d}.png"
        image.save(output)
        outputs.append(output)
        manifest_lines.append(f"{output.name}\t{language}\t{text.replace(chr(10), ' / ')}")

    manifest_path = test_dir / "manifest.tsv"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    overview_path = test_dir / "_overview_checker.jpg"
    make_checker_overview(outputs, overview_path)
    return BatchResult(final_dir=final_dir, test_dir=test_dir, overview_path=overview_path, manifest_path=manifest_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 50 transparent dog text T-shirt print PNGs.")
    parser.add_argument("--output-root", type=Path, default=default_output_root())
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260618)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_batch(args.output_root, args.count, args.seed)
    print(f"final_dir={result.final_dir}")
    print(f"overview={result.overview_path}")
    print(f"manifest={result.manifest_path}")


if __name__ == "__main__":
    main()
