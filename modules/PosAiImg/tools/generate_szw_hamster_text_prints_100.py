from __future__ import annotations

import argparse
import math
import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(r"C:\Windows\Fonts")
CANVAS_SIZE = (1400, 1400)
SCALE = 3

BATCH_TITLE = "韩系仓鼠短句印花"

SHORT_TEXTS = [
    ("ko", "간식 주세요"),
    ("en", "SNACK TIME"),
    ("ko", "오늘도 귀여워"),
    ("en", "NAP FIRST"),
    ("ko", "조금 쉬자"),
    ("en", "TOO CUTE"),
    ("ko", "기분 좋아"),
    ("en", "SOFT MOOD"),
    ("ko", "나 좀 봐줘"),
    ("en", "FEED ME"),
    ("ko", "잠깐만요"),
    ("en", "WAIT A SEC"),
    ("ko", "집에 갈래"),
    ("en", "GOOD VIBES"),
    ("ko", "혼자 있고 싶어"),
    ("en", "I AM FINE"),
    ("ko", "배고파요"),
    ("en", "LITTLE STAR"),
    ("ko", "행복 충전"),
    ("en", "CUTE ENERGY"),
    ("ko", "소중한 나"),
    ("en", "SMALL BUT LOUD"),
    ("ko", "잘했어요"),
    ("en", "HELLO CUTIE"),
    ("ko", "휴식 모드"),
    ("en", "LAZY MODE"),
    ("ko", "괜찮은 척"),
    ("en", "ROYAL MOOD"),
    ("ko", "칭찬 원해"),
    ("en", "LOOK AT ME"),
    ("ko", "오늘 휴무"),
    ("en", "BUSY BEING CUTE"),
    ("ko", "작고 소중해"),
    ("en", "NO RUSH"),
    ("ko", "귀여움 과다"),
    ("en", "TINY PAWS"),
    ("ko", "마음은 쿠키"),
    ("en", "ONE MORE SNACK"),
    ("ko", "조용히 응원"),
    ("en", "SLEEPY CLUB"),
    ("ko", "왕 귀여움"),
    ("en", "MOOD: ROUND"),
    ("ko", "좋은 하루"),
    ("en", "BE KIND"),
    ("ko", "나를 믿어"),
    ("en", "STAY SOFT"),
    ("ko", "천천히 가자"),
    ("en", "COZY TODAY"),
    ("ko", "꽃길만 걷자"),
    ("en", "BRAVE LITTLE"),
    ("ko", "하트 받아"),
    ("en", "HUG MODE"),
    ("ko", "말랑말랑"),
    ("en", "TINY JOY"),
    ("ko", "오늘은 느긋"),
    ("en", "ROUND AND READY"),
    ("ko", "간식 생각중"),
    ("en", "PLEASE WAIT"),
    ("ko", "귀여운 척 아님"),
    ("en", "NOT TODAY"),
    ("ko", "심장 조심"),
    ("en", "SEND SNACKS"),
    ("ko", "나도 몰라"),
    ("en", "BIG FEELINGS"),
    ("ko", "작은 용기"),
    ("en", "SOFT HEART"),
    ("ko", "오늘도 버팀"),
    ("en", "SLOW DAY"),
    ("ko", "달콤한 순간"),
    ("en", "HAPPY LITTLE"),
    ("ko", "쉬는 중"),
    ("en", "CUTE BUT TIRED"),
    ("ko", "볼 빵빵"),
    ("en", "DREAM BIG"),
    ("ko", "사랑해요"),
    ("en", "LOVE YOU"),
    ("ko", "좋아 좋아"),
    ("en", "SMILE MORE"),
    ("ko", "나는 귀해"),
    ("en", "MAIN CHARACTER"),
    ("ko", "칭찬 주세요"),
    ("en", "GOOD JOB"),
    ("ko", "매일 귀여움"),
    ("en", "CLOUD NAP"),
    ("ko", "슬쩍 등장"),
    ("en", "HELLO FRIEND"),
    ("ko", "포근한 날"),
    ("en", "COZY HEART"),
    ("ko", "간식 파티"),
    ("en", "PARTY MODE"),
    ("ko", "괜찮아"),
    ("en", "ALL GOOD"),
    ("ko", "귀여운 반항"),
    ("en", "TINY DRAMA"),
    ("ko", "쉬어도 돼"),
    ("en", "REST WELL"),
]

PROPS = [
    "cookie",
    "strawberry",
    "flower",
    "book",
    "headphones",
    "heart",
    "umbrella",
    "cup",
    "backpack",
    "camera",
    "lollipop",
    "leaf",
    "microphone",
    "paint",
    "skateboard",
    "shopping_bag",
    "alarm",
    "gamepad",
    "letter",
    "sleep_mask",
    "crown",
    "chef_hat",
    "scarf",
    "donut",
    "pencil",
]

POSES = [
    "standing",
    "wave_left",
    "wave_right",
    "sit",
    "peek",
    "jump",
    "sleepy",
    "dance",
    "hug",
    "point",
    "kneel",
    "wide",
    "tiny_step",
    "lean",
    "arms_up",
    "shy",
    "side",
    "sniff",
    "hold_low",
    "hold_high",
]


@dataclass(frozen=True)
class BatchResult:
    batch_root: Path
    final_dir: Path
    test_dir: Path
    overview_path: Path
    manifest_path: Path


def parse_sku(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Za-z]+)-(\d+)", value.strip())
    if not match:
        raise ValueError(f"Invalid SKU start: {value}")
    return match.group(1).upper(), int(match.group(2))


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
    max_height: int,
    stroke_width: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(start_size, 30 * SCALE, -2 * SCALE):
        fnt = font(candidates, size)
        bboxes = [draw.textbbox((0, 0), line, font=fnt, stroke_width=stroke_width) for line in lines]
        widths = [bbox[2] - bbox[0] for bbox in bboxes]
        heights = [bbox[3] - bbox[1] for bbox in bboxes]
        total_height = sum(heights) + max(0, len(lines) - 1) * int(size * 0.12)
        if max(widths, default=0) <= max_width and total_height <= max_height:
            return fnt
    return font(candidates, 30 * SCALE)


def wrap_text(text: str, language: str) -> list[str]:
    if language == "ko":
        parts = text.split()
        if len(parts) <= 1:
            return [text]
        return [" ".join(parts[: math.ceil(len(parts) / 2)]), " ".join(parts[math.ceil(len(parts) / 2) :])]
    words = text.split()
    if len(words) <= 2:
        return [text]
    return [" ".join(words[: math.ceil(len(words) / 2)]), " ".join(words[math.ceil(len(words) / 2) :])]


def s(v: int | float) -> int:
    return int(round(v * SCALE))


def draw_ellipse(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    width: int,
) -> None:
    draw.ellipse(tuple(s(v) for v in box), fill=fill, outline=outline, width=s(width))


def draw_line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, width: int) -> None:
    draw.line([(s(x), s(y)) for x, y in points], fill=fill, width=s(width), joint="curve")


def draw_round_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline, width: int) -> None:
    draw.rounded_rectangle(tuple(s(v) for v in box), radius=s(radius), fill=fill, outline=outline, width=s(width))


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r1: int, r2: int, fill) -> None:
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = r1 if i % 2 == 0 else r2
        pts.append((s(cx + math.cos(angle) * radius), s(cy + math.sin(angle) * radius)))
    draw.polygon(pts, fill=fill)


def draw_bubble(
    draw: ImageDraw.ImageDraw,
    text: str,
    language: str,
    rng: random.Random,
    variant: int,
    hamster_box: tuple[int, int, int, int],
) -> None:
    side = "left" if variant % 2 else "right"
    x1 = 130 if side == "left" else 830
    y1 = 130 + rng.randint(-18, 38)
    w = 405 + rng.randint(-28, 36)
    h = 210 + rng.randint(-18, 28)
    x2, y2 = x1 + w, y1 + h
    style = variant % 3
    white = (255, 255, 255, 255)
    black = (14, 14, 14, 255)

    if style == 0:
        spikes = 18
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        pts = []
        for i in range(spikes * 2):
            angle = i * math.tau / (spikes * 2)
            rx = w / 2 * (1.0 if i % 2 == 0 else 0.82)
            ry = h / 2 * (1.0 if i % 2 == 0 else 0.78)
            pts.append((s(cx + math.cos(angle) * rx), s(cy + math.sin(angle) * ry)))
        draw.polygon(pts, fill=white, outline=black)
        draw.line(pts + [pts[0]], fill=black, width=s(8))
    elif style == 1:
        draw.rounded_rectangle((s(x1), s(y1), s(x2), s(y2)), radius=s(82), fill=white, outline=black, width=s(8))
    else:
        for ox, oy, rw, rh in ((28, 24, 130, 98), (136, -5, 160, 118), (254, 30, 128, 100), (85, 90, 225, 92)):
            draw.ellipse((s(x1 + ox), s(y1 + oy), s(x1 + ox + rw), s(y1 + oy + rh)), fill=white, outline=black, width=s(7))

    tail_x = hamster_box[0] + 80 if side == "right" else hamster_box[2] - 80
    tail_y = hamster_box[1] + 145
    if side == "right":
        tail = [(x1 + 70, y2 - 18), (tail_x, tail_y), (x1 + 150, y2 - 24)]
    else:
        tail = [(x2 - 70, y2 - 18), (tail_x, tail_y), (x2 - 150, y2 - 24)]
    draw.polygon([(s(x), s(y)) for x, y in tail], fill=white, outline=black)
    draw.line([(s(x), s(y)) for x, y in tail + [tail[0]]], fill=black, width=s(7))

    lines = wrap_text(text, language)
    font_names = ["malgunbd.ttf", "malgun.ttf", "arialbd.ttf"] if language == "ko" else ["arialbd.ttf", "segoeuib.ttf", "segoeui.ttf"]
    fnt = fit_font(draw, lines, font_names, 58 * SCALE, s(w - 72), s(h - 56), s(2))
    bboxes = [draw.textbbox((0, 0), line, font=fnt, stroke_width=s(2)) for line in lines]
    heights = [bbox[3] - bbox[1] for bbox in bboxes]
    widths = [bbox[2] - bbox[0] for bbox in bboxes]
    gap = int(fnt.size * 0.12)
    total_h = sum(heights) + gap * (len(lines) - 1)
    current_y = s(y1 + h / 2) - total_h // 2
    for line, width, bbox in zip(lines, widths, bboxes):
        tx = s(x1 + w / 2) - width // 2
        draw.text(
            (tx, current_y - bbox[1]),
            line,
            font=fnt,
            fill=black,
            stroke_width=s(1),
            stroke_fill=white,
        )
        current_y += (bbox[3] - bbox[1]) + gap


def draw_prop(draw: ImageDraw.ImageDraw, prop: str, cx: int, cy: int, rng: random.Random) -> None:
    black = (18, 18, 18, 255)
    pink = (255, 150, 176, 255)
    red = (230, 72, 80, 255)
    green = (84, 157, 90, 255)
    yellow = (255, 211, 88, 255)
    blue = (100, 162, 216, 255)
    cream = (255, 241, 205, 255)
    brown = (143, 93, 55, 255)
    white = (255, 255, 255, 255)
    if prop == "cookie":
        draw_ellipse(draw, (cx - 62, cy - 50, cx + 62, cy + 50), brown, black, 7)
        for ox, oy in ((-22, -12), (20, -18), (4, 17), (-35, 22)):
            draw_ellipse(draw, (cx + ox - 7, cy + oy - 7, cx + ox + 7, cy + oy + 7), (76, 45, 30, 255), (76, 45, 30, 255), 1)
    elif prop == "strawberry":
        draw_ellipse(draw, (cx - 55, cy - 50, cx + 55, cy + 68), red, black, 7)
        draw.polygon([(s(cx - 42), s(cy - 42)), (s(cx), s(cy - 88)), (s(cx + 42), s(cy - 42))], fill=green, outline=black)
        for ox, oy in ((-22, -12), (12, -8), (0, 22), (28, 28), (-28, 30)):
            draw_ellipse(draw, (cx + ox - 4, cy + oy - 4, cx + ox + 4, cy + oy + 4), yellow, yellow, 1)
    elif prop == "flower":
        for a in range(8):
            px = cx + math.cos(a * math.tau / 8) * 48
            py = cy + math.sin(a * math.tau / 8) * 48
            draw_ellipse(draw, (px - 26, py - 26, px + 26, py + 26), pink, black, 5)
        draw_ellipse(draw, (cx - 24, cy - 24, cx + 24, cy + 24), yellow, black, 5)
        draw_line(draw, [(cx, cy + 42), (cx + 20, cy + 130)], green, 10)
    elif prop == "book":
        draw_round_rect(draw, (cx - 102, cy - 66, cx - 2, cy + 66), 14, (149, 190, 130, 255), black, 6)
        draw_round_rect(draw, (cx + 2, cy - 66, cx + 102, cy + 66), 14, (184, 216, 156, 255), black, 6)
        draw_line(draw, [(cx, cy - 58), (cx, cy + 60)], black, 4)
    elif prop == "headphones":
        draw.arc((s(cx - 128), s(cy - 122), s(cx + 128), s(cy + 126)), 205, 335, fill=black, width=s(11))
        draw_round_rect(draw, (cx - 128, cy - 5, cx - 78, cy + 100), 24, blue, black, 7)
        draw_round_rect(draw, (cx + 78, cy - 5, cx + 128, cy + 100), 24, blue, black, 7)
    elif prop == "heart":
        draw_ellipse(draw, (cx - 80, cy - 60, cx, cy + 20), pink, black, 7)
        draw_ellipse(draw, (cx, cy - 60, cx + 80, cy + 20), pink, black, 7)
        draw.polygon([(s(cx - 78), s(cy - 12)), (s(cx + 78), s(cy - 12)), (s(cx), s(cy + 105))], fill=pink, outline=black)
    elif prop == "umbrella":
        draw.pieslice((s(cx - 130), s(cy - 120), s(cx + 130), s(cy + 120)), 180, 360, fill=(255, 173, 191, 255), outline=black, width=s(7))
        for ox in (-65, 0, 65):
            draw_line(draw, [(cx, cy), (cx + ox, cy - 18)], black, 4)
        draw_line(draw, [(cx, cy), (cx, cy + 150)], black, 8)
        draw.arc((s(cx - 4), s(cy + 120), s(cx + 62), s(cy + 188)), 0, 150, fill=black, width=s(7))
    elif prop == "cup":
        draw_round_rect(draw, (cx - 72, cy - 86, cx + 72, cy + 88), 26, (214, 166, 108, 255), black, 7)
        draw_round_rect(draw, (cx - 88, cy - 112, cx + 88, cy - 78), 16, white, black, 6)
        draw_line(draw, [(cx - 35, cy - 28), (cx + 35, cy - 28)], white, 6)
    elif prop == "backpack":
        draw_round_rect(draw, (cx - 80, cy - 98, cx + 80, cy + 98), 38, (83, 132, 178, 255), black, 7)
        draw_round_rect(draw, (cx - 52, cy - 15, cx + 52, cy + 60), 24, (255, 201, 111, 255), black, 5)
        draw_line(draw, [(cx - 65, cy - 45), (cx + 65, cy - 45)], black, 5)
    elif prop == "camera":
        draw_round_rect(draw, (cx - 95, cy - 60, cx + 95, cy + 60), 20, (54, 63, 72, 255), black, 7)
        draw_ellipse(draw, (cx - 38, cy - 38, cx + 38, cy + 38), (132, 185, 217, 255), black, 6)
        draw_round_rect(draw, (cx - 62, cy - 88, cx, cy - 58), 10, (54, 63, 72, 255), black, 5)
    elif prop == "lollipop":
        draw_line(draw, [(cx + 10, cy + 42), (cx + 74, cy + 150)], black, 7)
        draw_ellipse(draw, (cx - 60, cy - 60, cx + 60, cy + 60), (255, 130, 178, 255), black, 7)
        draw.arc((s(cx - 44), s(cy - 44), s(cx + 44), s(cy + 44)), 15, 330, fill=white, width=s(12))
    elif prop == "leaf":
        draw_ellipse(draw, (cx - 92, cy - 130, cx + 92, cy + 130), green, black, 7)
        draw_line(draw, [(cx - 72, cy + 94), (cx + 72, cy - 94)], (39, 105, 53, 255), 5)
    elif prop == "microphone":
        draw_round_rect(draw, (cx - 38, cy - 98, cx + 38, cy + 18), 38, (75, 74, 82, 255), black, 7)
        draw_line(draw, [(cx, cy + 18), (cx, cy + 130)], black, 10)
        draw_line(draw, [(cx - 52, cy + 130), (cx + 52, cy + 130)], black, 8)
    elif prop == "paint":
        draw_ellipse(draw, (cx - 105, cy - 68, cx + 105, cy + 68), cream, black, 7)
        for ox, color in [(-50, red), (0, blue), (48, green), (25, yellow)]:
            draw_ellipse(draw, (cx + ox - 15, cy - 12, cx + ox + 15, cy + 18), color, color, 1)
        draw_line(draw, [(cx + 70, cy - 80), (cx + 150, cy - 145)], brown, 10)
    elif prop == "skateboard":
        draw_round_rect(draw, (cx - 160, cy + 38, cx + 160, cy + 86), 28, (245, 140, 84, 255), black, 7)
        draw_ellipse(draw, (cx - 92, cy + 75, cx - 50, cy + 117), black, black, 1)
        draw_ellipse(draw, (cx + 50, cy + 75, cx + 92, cy + 117), black, black, 1)
    elif prop == "shopping_bag":
        draw_round_rect(draw, (cx - 82, cy - 72, cx + 82, cy + 100), 12, (255, 174, 191, 255), black, 7)
        draw.arc((s(cx - 42), s(cy - 96), s(cx + 42), s(cy - 18)), 180, 360, fill=black, width=s(7))
        draw_ellipse(draw, (cx - 18, cy - 8, cx + 18, cy + 28), white, white, 1)
    elif prop == "alarm":
        draw_ellipse(draw, (cx - 78, cy - 78, cx + 78, cy + 78), (255, 126, 126, 255), black, 7)
        draw_line(draw, [(cx, cy), (cx, cy - 45), (cx + 38, cy - 12)], black, 6)
        draw_ellipse(draw, (cx - 100, cy - 112, cx - 36, cy - 64), red, black, 6)
        draw_ellipse(draw, (cx + 36, cy - 112, cx + 100, cy - 64), red, black, 6)
    elif prop == "gamepad":
        draw_round_rect(draw, (cx - 125, cy - 54, cx + 125, cy + 62), 48, (93, 126, 209, 255), black, 7)
        draw_line(draw, [(cx - 75, cy - 15), (cx - 75, cy + 26)], black, 6)
        draw_line(draw, [(cx - 96, cy + 6), (cx - 54, cy + 6)], black, 6)
        draw_ellipse(draw, (cx + 52, cy - 10, cx + 74, cy + 12), pink, black, 4)
        draw_ellipse(draw, (cx + 86, cy + 10, cx + 108, cy + 32), yellow, black, 4)
    elif prop == "letter":
        draw_round_rect(draw, (cx - 105, cy - 70, cx + 105, cy + 70), 10, white, black, 7)
        draw_line(draw, [(cx - 96, cy - 56), (cx, cy + 12), (cx + 96, cy - 56)], (230, 115, 145, 255), 5)
        draw_ellipse(draw, (cx - 20, cy - 8, cx + 20, cy + 30), pink, pink, 1)
    elif prop == "sleep_mask":
        draw_round_rect(draw, (cx - 110, cy - 38, cx + 110, cy + 38), 35, (130, 185, 229, 255), black, 7)
        draw_line(draw, [(cx - 52, cy - 2), (cx - 18, cy - 2)], black, 5)
        draw_line(draw, [(cx + 18, cy - 2), (cx + 52, cy - 2)], black, 5)
    elif prop == "crown":
        pts = [(cx - 100, cy + 42), (cx - 80, cy - 58), (cx - 30, cy + 2), (cx, cy - 82), (cx + 30, cy + 2), (cx + 80, cy - 58), (cx + 100, cy + 42)]
        draw.polygon([(s(x), s(y)) for x, y in pts], fill=yellow, outline=black)
        draw_line(draw, pts + [pts[0]], black, 7)
    elif prop == "chef_hat":
        for ox in (-58, 0, 58):
            draw_ellipse(draw, (cx + ox - 50, cy - 95, cx + ox + 50, cy + 5), white, black, 6)
        draw_round_rect(draw, (cx - 92, cy - 10, cx + 92, cy + 72), 22, white, black, 6)
    elif prop == "scarf":
        draw_round_rect(draw, (cx - 120, cy - 40, cx + 120, cy + 34), 32, (255, 157, 172, 255), black, 6)
        draw_round_rect(draw, (cx + 35, cy + 20, cx + 88, cy + 142), 20, (255, 157, 172, 255), black, 6)
        draw_line(draw, [(cx - 90, cy - 4), (cx + 95, cy - 4)], white, 4)
    elif prop == "donut":
        draw_ellipse(draw, (cx - 88, cy - 88, cx + 88, cy + 88), (236, 166, 92, 255), black, 7)
        draw_ellipse(draw, (cx - 38, cy - 38, cx + 38, cy + 38), (0, 0, 0, 0), black, 7)
        draw.arc((s(cx - 72), s(cy - 68), s(cx + 70), s(cy + 70)), 15, 235, fill=pink, width=s(18))
    else:
        draw_line(draw, [(cx - 70, cy + 90), (cx + 90, cy - 95)], brown, 11)
        draw.polygon([(s(cx + 90), s(cy - 95)), (s(cx + 125), s(cy - 122)), (s(cx + 108), s(cy - 78))], fill=(45, 45, 45, 255), outline=black)


def draw_hamster(draw: ImageDraw.ImageDraw, rng: random.Random, pose: str, prop: str, variant: int) -> tuple[int, int, int, int]:
    fur = (232, 177, 103, 255)
    fur_light = (255, 222, 166, 255)
    fur_shadow = (191, 126, 62, 255)
    blush = (255, 137, 159, 180)
    black = (15, 15, 15, 255)
    pink = (255, 174, 184, 255)
    cx = 700 + rng.randint(-26, 26)
    cy = 805 + rng.randint(-16, 24)
    if pose in {"jump", "arms_up"}:
        cy -= 48
    if pose == "sleepy":
        cy += 18
    body_w = 380 + rng.randint(-18, 34)
    body_h = 440 + rng.randint(-12, 36)
    head_w = 410 + rng.randint(-16, 28)
    head_h = 330 + rng.randint(-16, 18)
    head_y = cy - 190
    body_y = cy + 80

    if prop == "skateboard":
        draw_prop(draw, prop, cx, body_y + 250, rng)

    draw_ellipse(draw, (cx - body_w // 2, body_y - body_h // 2, cx + body_w // 2, body_y + body_h // 2), fur, black, 10)
    draw_ellipse(draw, (cx - 145, body_y - 120, cx + 145, body_y + 180), fur_light, fur_light, 1)
    draw_ellipse(draw, (cx - head_w // 2, head_y - head_h // 2, cx + head_w // 2, head_y + head_h // 2), fur, black, 10)
    draw_ellipse(draw, (cx - head_w // 2 - 18, head_y - 150, cx - head_w // 2 + 112, head_y - 28), fur, black, 10)
    draw_ellipse(draw, (cx + head_w // 2 - 112, head_y - 150, cx + head_w // 2 + 18, head_y - 28), fur, black, 10)
    draw_ellipse(draw, (cx - head_w // 2 + 18, head_y - 124, cx - head_w // 2 + 88, head_y - 56), (255, 198, 174, 255), fur_shadow, 4)
    draw_ellipse(draw, (cx + head_w // 2 - 88, head_y - 124, cx + head_w // 2 - 18, head_y - 56), (255, 198, 174, 255), fur_shadow, 4)

    eye_y = head_y - 4 + rng.randint(-7, 7)
    if pose == "sleepy":
        draw.arc((s(cx - 122), s(eye_y - 18), s(cx - 78), s(eye_y + 26)), 12, 168, fill=black, width=s(7))
        draw.arc((s(cx + 78), s(eye_y - 18), s(cx + 122), s(eye_y + 26)), 12, 168, fill=black, width=s(7))
    elif pose == "shy":
        draw.arc((s(cx - 124), s(eye_y - 18), s(cx - 78), s(eye_y + 20)), 15, 165, fill=black, width=s(7))
        draw_ellipse(draw, (cx + 84, eye_y - 20, cx + 118, eye_y + 20), black, black, 1)
    else:
        draw_ellipse(draw, (cx - 120, eye_y - 24, cx - 82, eye_y + 24), black, black, 1)
        draw_ellipse(draw, (cx + 82, eye_y - 24, cx + 120, eye_y + 24), black, black, 1)
        draw_ellipse(draw, (cx - 108, eye_y - 16, cx - 96, eye_y - 4), (255, 255, 255, 230), (255, 255, 255, 230), 1)
        draw_ellipse(draw, (cx + 94, eye_y - 16, cx + 106, eye_y - 4), (255, 255, 255, 230), (255, 255, 255, 230), 1)

    draw_ellipse(draw, (cx - 38, head_y + 58, cx + 38, head_y + 108), pink, black, 5)
    draw_line(draw, [(cx, head_y + 108), (cx, head_y + 126)], black, 5)
    if pose == "sniff":
        draw.arc((s(cx - 54), s(head_y + 110), s(cx + 8), s(head_y + 168)), 200, 345, fill=black, width=s(6))
        draw.arc((s(cx - 8), s(head_y + 110), s(cx + 54), s(head_y + 168)), 195, 340, fill=black, width=s(6))
    else:
        draw.arc((s(cx - 56), s(head_y + 104), s(cx + 0), s(head_y + 164)), 15, 150, fill=black, width=s(6))
        draw.arc((s(cx + 0), s(head_y + 104), s(cx + 56), s(head_y + 164)), 30, 165, fill=black, width=s(6))
    draw_ellipse(draw, (cx - 170, head_y + 66, cx - 92, head_y + 126), blush, blush, 1)
    draw_ellipse(draw, (cx + 92, head_y + 66, cx + 170, head_y + 126), blush, blush, 1)

    arm_y = body_y - 54
    if pose in {"wave_left", "arms_up"}:
        draw_line(draw, [(cx - 168, arm_y), (cx - 276, arm_y - 178)], fur_shadow, 24)
        draw_ellipse(draw, (cx - 310, arm_y - 222, cx - 248, arm_y - 160), fur, black, 7)
    else:
        draw_line(draw, [(cx - 158, arm_y), (cx - 250, arm_y + 38)], fur_shadow, 22)
        draw_ellipse(draw, (cx - 282, arm_y + 18, cx - 220, arm_y + 80), fur, black, 7)
    if pose in {"wave_right", "arms_up", "point"}:
        draw_line(draw, [(cx + 168, arm_y), (cx + 282, arm_y - 170 if pose != "point" else arm_y - 72)], fur_shadow, 24)
        draw_ellipse(draw, (cx + 250, arm_y - 212 if pose != "point" else arm_y - 104, cx + 314, arm_y - 150 if pose != "point" else arm_y - 42), fur, black, 7)
    else:
        draw_line(draw, [(cx + 158, arm_y), (cx + 250, arm_y + 38)], fur_shadow, 22)
        draw_ellipse(draw, (cx + 220, arm_y + 18, cx + 282, arm_y + 80), fur, black, 7)

    draw_ellipse(draw, (cx - 144, body_y + 174, cx - 62, body_y + 250), (246, 166, 150, 255), black, 7)
    draw_ellipse(draw, (cx + 62, body_y + 174, cx + 144, body_y + 250), (246, 166, 150, 255), black, 7)

    prop_x = cx + rng.choice([-148, -118, 118, 148, 0])
    prop_y = body_y + rng.choice([12, 62, 108])
    if prop in {"headphones", "crown", "chef_hat", "sleep_mask", "scarf"}:
        prop_x = cx
        prop_y = head_y - 82 if prop in {"crown", "chef_hat"} else head_y + 10
    elif prop == "leaf":
        prop_x = cx - 190
        prop_y = head_y + 120
    elif prop == "umbrella":
        prop_x = cx + 176
        prop_y = head_y - 72
    elif prop == "skateboard":
        prop_x = cx
        prop_y = body_y + 250
    draw_prop(draw, prop, prop_x, prop_y, rng)

    if variant % 5 in (0, 2):
        for dx, dy in [(-388, -26), (382, 76), (-282, 254), (318, -166)]:
            draw_star(draw, cx + dx + rng.randint(-12, 12), head_y + dy + rng.randint(-12, 12), 23, 10, (255, 213, 91, 255))
    if variant % 4 == 1:
        for dx, dy in [(-348, 130), (340, 210)]:
            draw_ellipse(draw, (cx + dx - 13, head_y + dy - 13, cx + dx + 13, head_y + dy + 13), (255, 255, 255, 255), black, 3)

    return (cx - max(body_w, head_w) // 2 - 330, head_y - head_h // 2 - 230, cx + max(body_w, head_w) // 2 + 330, body_y + body_h // 2 + 170)


def make_print(text: str, language: str, seed: int, index: int) -> Image.Image:
    rng = random.Random(seed + index * 7919)
    canvas = Image.new("RGBA", (CANVAS_SIZE[0] * SCALE, CANVAS_SIZE[1] * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    pose = POSES[(index - 1) % len(POSES)]
    prop = PROPS[((index - 1) * 7 + index // 3) % len(PROPS)]
    box = draw_hamster(draw, rng, pose, prop, index)
    draw_bubble(draw, text, language, rng, index, box)
    return canvas.resize(CANVAS_SIZE, Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=0.6, percent=70, threshold=3))


def make_checker_overview(paths: list[Path], output: Path) -> None:
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
        img.thumbnail((218, 228), Image.Resampling.LANCZOS)
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


def generate_batch(start_sku: str, count: int, seed: int, batch_date: str) -> BatchResult:
    prefix, start_num = parse_sku(start_sku)
    end_num = start_num + count - 1
    batch_name = f"{BATCH_TITLE}_{prefix}-{start_num}-{prefix}-{end_num}_{batch_date}"
    batch_root = ROOT / "图库" / prefix / "2026" / "6月" / batch_name
    final_dir = batch_root / "最终透明底"
    test_dir = batch_root / "测试"
    final_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    text_pool = SHORT_TEXTS.copy()
    rng.shuffle(text_pool)
    selected = [text_pool[i % len(text_pool)] for i in range(count)]

    outputs: list[Path] = []
    manifest_lines = ["sku\tlanguage\ttext\tpose\tprop"]
    for offset, (language, text) in enumerate(selected):
        sku = f"{prefix}-{start_num + offset}"
        index = offset + 1
        image = make_print(text, language, seed, index)
        output = final_dir / f"{sku}.png"
        image.save(output)
        outputs.append(output)
        pose = POSES[(index - 1) % len(POSES)]
        prop = PROPS[((index - 1) * 7 + index // 3) % len(PROPS)]
        manifest_lines.append(f"{sku}\t{language}\t{text}\t{pose}\t{prop}")
        print(f"{sku}: {language} {text} / {pose} / {prop}")

    manifest_path = test_dir / "manifest.tsv"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    overview_path = test_dir / "_transparent_overview_checker.jpg"
    make_checker_overview(outputs, overview_path)
    return BatchResult(batch_root=batch_root, final_dir=final_dir, test_dir=test_dir, overview_path=overview_path, manifest_path=manifest_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 100 transparent SZW hamster text print PNGs.")
    parser.add_argument("--start-sku", default="SZW-3013")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260618)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_batch(args.start_sku, args.count, args.seed, args.date)
    print(f"batch_root={result.batch_root}")
    print(f"final_dir={result.final_dir}")
    print(f"overview={result.overview_path}")
    print(f"manifest={result.manifest_path}")


if __name__ == "__main__":
    main()
