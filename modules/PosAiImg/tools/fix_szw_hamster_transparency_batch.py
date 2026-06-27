from __future__ import annotations

import argparse
import math
import re
from collections import deque
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
    ("ko", "왕 귀여움"), ("en", "MOOD: ROUND"), ("ko", "느려도 괜찮아"), ("en", "BE KIND"),
    ("ko", "나른한 하루"), ("en", "STAY SOFT"), ("ko", "괜찮아도 돼"), ("en", "COZY TODAY"),
    ("ko", "오늘은 쉬는 날"), ("en", "BRAVE LITTLE"), ("ko", "행복한 마음"), ("en", "HUG MODE"),
    ("ko", "몽글몽글"), ("en", "TINY JOY"), ("ko", "오늘은 맑음"), ("en", "ROUND AND READY"),
    ("ko", "간식 준비완료"), ("en", "PLEASE WAIT"), ("ko", "귀여운 하루 보내"), ("en", "NOT TODAY"),
    ("ko", "반짝 작은 나"), ("en", "SEND SNACKS"), ("ko", "나른한 오후"), ("en", "BIG FEELINGS"),
    ("ko", "마음이 포근"), ("en", "SOFT HEART"), ("ko", "오늘도 천천히"), ("en", "SLOW DAY"),
    ("ko", "나만의 속도"), ("en", "HAPPY LITTLE"), ("ko", "조금 졸려"), ("en", "CUTE BUT TIRED"),
    ("ko", "꿈은 크게"), ("en", "DREAM BIG"), ("ko", "사랑해요"), ("en", "LOVE YOU"),
    ("ko", "포근해 포근해"), ("en", "SMILE MORE"), ("ko", "나른한 귀여움"), ("en", "MAIN CHARACTER"),
    ("ko", "칭찬 주세요"), ("en", "GOOD JOB"), ("ko", "구름 낮잠"), ("en", "CLOUD NAP"),
    ("ko", "안녕 친구"), ("en", "HELLO FRIEND"), ("ko", "따뜻한 마음"), ("en", "COZY HEART"),
    ("ko", "간식 파티"), ("en", "PARTY MODE"), ("ko", "괜찮아"), ("en", "ALL GOOD"),
    ("ko", "귀여운 사고"), ("en", "TINY DRAMA"), ("ko", "조금 쉬어"), ("en", "REST WELL"),
    ("ko", "오늘도 몽글"), ("en", "SOFT DAYS"), ("ko", "마음이 행복"), ("en", "TREAT YOURSELF"),
    ("ko", "기분 최고"), ("en", "JUST CHILL"), ("ko", "나의 자리"), ("en", "CUTE CLUB"),
]


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


def split_sheet(path: Path, margin: int = 0) -> list[Image.Image]:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    w, h = img.size
    crops: list[Image.Image] = []
    for row in range(2):
        for col in range(2):
            x1 = col * w // 2
            y1 = row * h // 2
            x2 = (col + 1) * w // 2
            y2 = (row + 1) * h // 2
            crops.append(img.crop((x1 + margin, y1 + margin, x2 - margin, y2 - margin)))
    return crops


def trim_outer_light_frame(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGBA"))
    rgb = arr[..., :3]
    alpha = arr[..., 3]
    light = (rgb[..., 0] > 235) & (rgb[..., 1] > 235) & (rgb[..., 2] > 235) & (alpha > 0)
    frame = edge_connected(light)
    keep = ~frame
    ys, xs = np.where(keep)
    if len(xs) == 0 or len(ys) == 0:
        return img
    x1, x2 = int(xs.min()), int(xs.max()) + 1
    y1, y2 = int(ys.min()), int(ys.max()) + 1
    # Do not keep the outer white frame, otherwise the green backdrop is no
    # longer edge-connected and cannot be removed safely.
    pad = 0
    return img.crop((max(0, x1 - pad), max(0, y1 - pad), min(img.width, x2 + pad), min(img.height, y2 + pad)))


def crop_inset(img: Image.Image, inset: int) -> Image.Image:
    if img.width <= inset * 2 or img.height <= inset * 2:
        return img
    return img.crop((inset, inset, img.width - inset, img.height - inset))


def find_bubble(img: Image.Image) -> tuple[int, int, int, int] | None:
    rgb = np.asarray(img.convert("RGB"))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    white = (r > 228) & (g > 228) & (b > 228)
    white[int(white.shape[0] * 0.58):, :] = False
    comps = connected_components(white, min_area=max(300, white.size // 400))
    for area, bbox in comps:
        x1, y1, x2, y2 = bbox
        bw, bh = x2 - x1, y2 - y1
        if bw >= img.width * 0.14 and bh >= img.height * 0.08 and area >= bw * bh * 0.30:
            return bbox
    return None


def wrap_text(text: str) -> list[str]:
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
        x1, y1, x2, y2 = bubble
    pad_x = int((x2 - x1) * 0.16)
    pad_y = int((y2 - y1) * 0.18)
    lines = wrap_text(text)
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


def remove_deep_green_background(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGBA")).copy()
    rgb = arr[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Keep this intentionally narrow: it should match the imgGen backdrop,
    # not green props such as SZW-3025's leaf.
    deep_bg = (g > r + 14) & (g > b + 5) & (r < 34) & (g < 88) & (b < 62)
    bg = edge_connected(deep_bg)
    alpha = arr[..., 3].astype(np.float32)
    alpha[bg] = 0
    alpha_img = Image.fromarray(alpha.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.25))
    arr[..., 3] = np.asarray(alpha_img)
    out = Image.fromarray(arr, "RGBA")
    return crop_alpha(out, pad=18)


def strip_edge_white_lines(img: Image.Image, width: int = 8) -> Image.Image:
    arr = np.asarray(img.convert("RGBA")).copy()
    rgb = arr[..., :3]
    alpha = arr[..., 3]
    h, w = alpha.shape
    near_white = (rgb[..., 0] > 235) & (rgb[..., 1] > 235) & (rgb[..., 2] > 235) & (alpha > 0)
    edge_band = np.zeros_like(near_white, dtype=bool)
    edge_band[:width, :] = True
    edge_band[-width:, :] = True
    edge_band[:, :width] = True
    edge_band[:, -width:] = True
    remove = edge_connected(near_white & edge_band)
    alpha[remove] = 0
    arr[..., 3] = alpha
    return crop_alpha(Image.fromarray(arr, "RGBA"), pad=18)


def crop_alpha(img: Image.Image, pad: int) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    return img.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad)))


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


def process(batch_root: Path, start_sku: str, count: int, rebuild_all: bool) -> None:
    prefix, start = parse_sku(start_sku)
    test_dir = next(p for p in batch_root.iterdir() if p.is_dir() and any(p.glob("imggen_source_*.png")))
    final_dir = next(p for p in batch_root.iterdir() if p.is_dir() and any(p.glob(f"{prefix}-*.png")))
    sources = sorted(test_dir.glob("imggen_source_*.png"))
    rebuilt = 0
    cleaned = 0
    for source in sources:
        for q, crop in enumerate(split_sheet(source, margin=0)):
            idx = rebuilt + cleaned
            absolute_idx = (int(source.stem.rsplit("_", 1)[1]) - 1) * 4 + q
            if absolute_idx >= count:
                continue
            sku = f"{prefix}-{start + absolute_idx}"
            out_path = final_dir / f"{sku}.png"
            if rebuild_all or sku == "SZW-3025":
                language, text = SHORT_TEXTS[absolute_idx % len(SHORT_TEXTS)]
                prepared = crop_inset(trim_outer_light_frame(crop), 2)
                fixed = remove_deep_green_background(add_centered_text(prepared, text, language))
                fixed = strip_edge_white_lines(fixed)
                fixed.save(out_path)
                rebuilt += 1
            elif out_path.exists():
                fixed = strip_edge_white_lines(Image.open(out_path).convert("RGBA"))
                fixed.save(out_path)
                cleaned += 1
    outputs = sorted(final_dir.glob(f"{prefix}-*.png"))
    make_overview(outputs, test_dir / "_transparent_overview_checker.jpg")
    print(f"rebuilt={rebuilt}")
    print(f"edge_cleaned={cleaned}")
    print(f"outputs={len(outputs)}")
    print(f"overview={test_dir / '_transparent_overview_checker.jpg'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair SZW imgGen hamster transparent PNG edges and green-prop loss.")
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--start-sku", default="SZW-3013")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--rebuild-all", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    process(args.batch_root, args.start_sku, args.count, args.rebuild_all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
