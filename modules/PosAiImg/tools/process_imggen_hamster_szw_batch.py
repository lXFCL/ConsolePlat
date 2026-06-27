from __future__ import annotations

import argparse
import math
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(r"C:\Windows\Fonts")

SHORT_TEXTS = [
    ("ko", "간식 주세요"), ("en", "SNACK TIME"), ("ko", "오늘도 귀여워"), ("en", "NAP FIRST"),
    ("ko", "조금 쉬자"), ("en", "TOO CUTE"), ("ko", "기분 좋아"), ("en", "SOFT MOOD"),
    ("ko", "나 좀 봐줘"), ("en", "FEED ME"), ("ko", "잠깐만요"), ("en", "WAIT A SEC"),
    ("ko", "집에 갈래"), ("en", "GOOD VIBES"), ("ko", "혼자 있고 싶어"), ("en", "I AM FINE"),
    ("ko", "배고파요"), ("en", "LITTLE STAR"), ("ko", "행복 충전"), ("en", "CUTE ENERGY"),
    ("ko", "소중한 나"), ("en", "SMALL BUT LOUD"), ("ko", "잘했어요"), ("en", "HELLO CUTIE"),
    ("ko", "휴식 모드"), ("en", "LAZY MODE"), ("ko", "괜찮은 척"), ("en", "ROYAL MOOD"),
    ("ko", "칭찬 원해"), ("en", "LOOK AT ME"), ("ko", "오늘 휴무"), ("en", "BUSY BEING CUTE"),
    ("ko", "작고 소중해"), ("en", "NO RUSH"), ("ko", "귀여움 과다"), ("en", "TINY PAWS"),
    ("ko", "마음은 쿠키"), ("en", "ONE MORE SNACK"), ("ko", "조용히 응원"), ("en", "SLEEPY CLUB"),
    ("ko", "왕 귀여움"), ("en", "MOOD: ROUND"), ("ko", "좋은 하루"), ("en", "BE KIND"),
    ("ko", "나를 믿어"), ("en", "STAY SOFT"), ("ko", "천천히 가자"), ("en", "COZY TODAY"),
    ("ko", "꽃길만 걷자"), ("en", "BRAVE LITTLE"), ("ko", "하트 받아"), ("en", "HUG MODE"),
    ("ko", "말랑말랑"), ("en", "TINY JOY"), ("ko", "오늘은 느긋"), ("en", "ROUND AND READY"),
    ("ko", "간식 생각중"), ("en", "PLEASE WAIT"), ("ko", "귀여운 척 아님"), ("en", "NOT TODAY"),
    ("ko", "심장 조심"), ("en", "SEND SNACKS"), ("ko", "나도 몰라"), ("en", "BIG FEELINGS"),
    ("ko", "작은 용기"), ("en", "SOFT HEART"), ("ko", "오늘도 버팀"), ("en", "SLOW DAY"),
    ("ko", "달콤한 순간"), ("en", "HAPPY LITTLE"), ("ko", "쉬는 중"), ("en", "CUTE BUT TIRED"),
    ("ko", "볼 빵빵"), ("en", "DREAM BIG"), ("ko", "사랑해요"), ("en", "LOVE YOU"),
    ("ko", "좋아 좋아"), ("en", "SMILE MORE"), ("ko", "나는 귀해"), ("en", "MAIN CHARACTER"),
    ("ko", "칭찬 주세요"), ("en", "GOOD JOB"), ("ko", "매일 귀여움"), ("en", "CLOUD NAP"),
    ("ko", "슬쩍 등장"), ("en", "HELLO FRIEND"), ("ko", "포근한 날"), ("en", "COZY HEART"),
    ("ko", "간식 파티"), ("en", "PARTY MODE"), ("ko", "괜찮아"), ("en", "ALL GOOD"),
    ("ko", "귀여운 반항"), ("en", "TINY DRAMA"), ("ko", "쉬어도 돼"), ("en", "REST WELL"),
    ("ko", "오늘도 말랑"), ("en", "SOFT DAYS"), ("ko", "작은 행복"), ("en", "TREAT YOURSELF"),
    ("ko", "기분 전환"), ("en", "JUST CHILL"), ("ko", "내가 최고"), ("en", "CUTE CLUB"),
]


@dataclass(frozen=True)
class Bubble:
    bbox: tuple[int, int, int, int]
    area: int


def parse_sku(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Za-z]+)-(\d+)", value.strip())
    if not match:
        raise ValueError(f"Invalid SKU: {value}")
    return match.group(1).upper(), int(match.group(2))


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in candidates:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def connected_components(mask: np.ndarray, min_area: int = 150) -> list[tuple[int, tuple[int, int, int, int]]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out: list[tuple[int, tuple[int, int, int, int]]] = []
    for sy in range(h):
        xs = np.flatnonzero(mask[sy] & ~seen[sy])
        for sx in xs:
            if seen[sy, sx] or not mask[sy, sx]:
                continue
            q: deque[tuple[int, int]] = deque([(int(sx), sy)])
            seen[sy, sx] = True
            area = 0
            min_x = max_x = int(sx)
            min_y = max_y = sy
            while q:
                x, y = q.popleft()
                area += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            if area >= min_area:
                out.append((area, (min_x, min_y, max_x + 1, max_y + 1)))
    out.sort(reverse=True, key=lambda item: item[0])
    return out


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        if mask[0, x]:
            q.append((x, 0))
        if mask[h - 1, x]:
            q.append((x, h - 1))
    for y in range(h):
        if mask[y, 0]:
            q.append((0, y))
        if mask[y, w - 1]:
            q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if seen[y, x] or not mask[y, x]:
            continue
        seen[y, x] = True
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                q.append((nx, ny))
    return seen


def split_sheet(path: Path) -> list[Image.Image]:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    w, h = img.size
    crops = []
    for row in range(2):
        for col in range(2):
            x1 = col * w // 2
            y1 = row * h // 2
            x2 = (col + 1) * w // 2
            y2 = (row + 1) * h // 2
            margin = max(8, min(w, h) // 120)
            crops.append(img.crop((x1 + margin, y1 + margin, x2 - margin, y2 - margin)))
    return crops


def find_bubble(img: Image.Image) -> Bubble | None:
    rgb = np.asarray(img.convert("RGB"))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    white = (r > 228) & (g > 228) & (b > 228)
    upper = np.zeros(white.shape, dtype=bool)
    upper[: int(white.shape[0] * 0.58), :] = True
    white &= upper
    comps = connected_components(white, min_area=max(300, white.size // 400))
    candidates: list[Bubble] = []
    for area, bbox in comps:
        x1, y1, x2, y2 = bbox
        bw, bh = x2 - x1, y2 - y1
        if bw < img.width * 0.14 or bh < img.height * 0.08:
            continue
        if area < bw * bh * 0.30:
            continue
        candidates.append(Bubble(bbox=bbox, area=area))
    return candidates[0] if candidates else None


def wrap_text(text: str, language: str) -> list[str]:
    words = text.split()
    if len(words) <= 2:
        return [text]
    half = math.ceil(len(words) / 2)
    return [" ".join(words[:half]), " ".join(words[half:])]


def fit_text_font(draw: ImageDraw.ImageDraw, lines: list[str], language: str, max_w: int, max_h: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["malgunbd.ttf", "malgun.ttf", "arialbd.ttf"] if language == "ko" else ["arialbd.ttf", "segoeuib.ttf", "segoeui.ttf"]
    for size in range(72, 18, -2):
        fnt = font(names, size)
        boxes = [draw.textbbox((0, 0), line, font=fnt, stroke_width=1) for line in lines]
        widths = [box[2] - box[0] for box in boxes]
        heights = [box[3] - box[1] for box in boxes]
        gap = max(4, int(size * 0.15))
        if max(widths, default=0) <= max_w and sum(heights) + gap * (len(lines) - 1) <= max_h:
            return fnt
    return font(names, 18)


def add_centered_text(img: Image.Image, text: str, language: str) -> Image.Image:
    out = img.convert("RGBA")
    draw = ImageDraw.Draw(out)
    bubble = find_bubble(out)
    if not bubble:
        x1, y1, x2, y2 = int(out.width * 0.58), int(out.height * 0.08), int(out.width * 0.94), int(out.height * 0.28)
    else:
        x1, y1, x2, y2 = bubble.bbox
    pad_x = int((x2 - x1) * 0.16)
    pad_y = int((y2 - y1) * 0.18)
    lines = wrap_text(text, language)
    fnt = fit_text_font(draw, lines, language, max(24, x2 - x1 - pad_x * 2), max(24, y2 - y1 - pad_y * 2))
    boxes = [draw.textbbox((0, 0), line, font=fnt, stroke_width=1) for line in lines]
    heights = [box[3] - box[1] for box in boxes]
    widths = [box[2] - box[0] for box in boxes]
    gap = max(4, int(getattr(fnt, "size", 24) * 0.14))
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) // 2
    for line, box, width, height in zip(lines, boxes, widths, heights):
        x = x1 + (x2 - x1 - width) // 2
        draw.text((x, y - box[1]), line, font=fnt, fill=(14, 14, 14, 255), stroke_width=1, stroke_fill=(255, 255, 255, 255))
        y += height + gap
    return out


def remove_green_background(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGBA")).copy()
    rgb = arr[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # The generated background is dark green, sometimes with a gentle vignette.
    greenish = (g > r + 18) & (g > b + 6) & (g > 28) & (r < 80) & (b < 95)
    bg = edge_connected(greenish)
    alpha = arr[..., 3].astype(np.float32)
    alpha[bg] = 0
    # Fade antialiasing only near the detected background boundary.
    alpha_img = Image.fromarray(alpha.astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.45))
    arr[..., 3] = np.asarray(alpha_img)
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getbbox()
    if bbox:
        pad = 24
        out = out.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(out.width, bbox[2] + pad), min(out.height, bbox[3] + pad)))
    return out


def make_overview(paths: list[Path], output: Path) -> None:
    cols = 10
    tile_w, tile_h = 238, 286
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (242, 242, 242))
    label_font = font(["arial.ttf", "segoeui.ttf"], 13)
    for idx, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if bbox:
            img = img.crop(bbox)
        img.thumbnail((218, 226), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        td = ImageDraw.Draw(tile)
        for y in range(0, 236, 16):
            for x in range(0, tile_w, 16):
                fill = (232, 232, 232) if (x // 16 + y // 16) % 2 == 0 else (255, 255, 255)
                td.rectangle((x, y, x + 15, y + 15), fill=fill)
        tile.paste(img, ((tile_w - img.width) // 2, (236 - img.height) // 2), img)
        td.text((8, 248), path.stem, fill=(0, 0, 0), font=label_font)
        sheet.paste(tile, ((idx % cols) * tile_w, (idx // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def process_batch(batch_root: Path, start_sku: str, count: int) -> list[Path]:
    prefix, start = parse_sku(start_sku)
    test_dir = batch_root / "测试"
    final_dir = batch_root / "最终透明底"
    final_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(test_dir.glob("imggen_source_*.png"))
    outputs: list[Path] = []
    manifest = ["sku\tsource\tquadrant\tlanguage\ttext"]
    for source in sources:
        crops = split_sheet(source)
        for q, crop in enumerate(crops):
            idx = len(outputs)
            if idx >= count:
                break
            sku = f"{prefix}-{start + idx}"
            language, text = SHORT_TEXTS[idx % len(SHORT_TEXTS)]
            with_text = add_centered_text(crop, text, language)
            transparent = remove_green_background(with_text)
            out_path = final_dir / f"{sku}.png"
            transparent.save(out_path)
            outputs.append(out_path)
            manifest.append(f"{sku}\t{source.name}\t{q + 1}\t{language}\t{text}")
        if len(outputs) >= count:
            break
    (test_dir / "manifest.tsv").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    make_overview(outputs, test_dir / "_transparent_overview_checker.jpg")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process imgGen hamster sheets into SZW transparent print PNGs.")
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--start-sku", default="SZW-3013")
    parser.add_argument("--count", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = process_batch(args.batch_root, args.start_sku, args.count)
    print(f"processed={len(outputs)}")
    if outputs:
        print(f"first={outputs[0]}")
        print(f"last={outputs[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
