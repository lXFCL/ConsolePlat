from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "简约艺术字文字印花_200款_2026-06-09"
PROMPT_FILE = ROOT / "生成提示词" / "简约艺术字文字印花_200款_2026-06-09.txt"
FONT_DIR = Path("C:/Windows/Fonts")


@dataclass(frozen=True)
class Phrase:
    lang: str
    text: str


@dataclass(frozen=True)
class Style:
    font_path: Path
    fill: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int] | None
    accent: tuple[int, int, int, int]
    accent_style: str
    tracking: int
    line_gap: int


KOREAN = [
    "안녕", "좋아", "하루", "느긋", "산책", "바람", "여유", "소소", "달빛", "커피",
    "미소", "오늘", "별빛", "휴식", "맑음", "고요", "작은", "꿈", "순간", "마음",
    "봄날", "햇살", "평온", "기록", "낮잠", "새벽", "모래", "파도", "온기", "초록",
    "밤공기", "천천히", "우리", "가볍게", "선물", "조용히", "다시", "낭만", "귤빛", "담담",
    "웃자", "산들", "빛나", "로컬", "주말", "여름", "구름", "꽃길", "편안", "미니",
]

JAPANESE = [
    "いい日", "そよ風", "ゆっくり", "さんぽ", "小さな", "月夜", "きもち", "ひと息", "休日", "晴れ",
    "まどろみ", "余白", "朝", "夜", "花", "雲", "海", "森", "空", "夢",
    "静か", "今日", "明日", "光", "手紙", "純白", "青空", "旅", "喫茶", "音",
    "線", "柔らか", "きらり", "ほっと", "ことば", "まるい", "春", "夏", "秋", "冬",
    "日々", "風景", "淡い", "ねむい", "星", "水色", "こころ", "はじまり", "余韻", "日常",
]

CHINESE = [
    "慢慢来", "好天气", "小日子", "松弛感", "今天很好", "去散步", "微风", "晚安", "早安", "自在",
    "留白", "日常", "片刻", "温柔", "山海", "云朵", "夏天", "春日", "秋风", "冬夜",
    "小岛", "咖啡", "月光", "安静", "晴天", "慢生活", "去看海", "慢热", "轻轻", "呼吸",
    "远方", "花开", "旧时光", "平常心", "自由", "软软", "认真", "放空", "不赶路", "简单点",
    "有光", "微甜", "小确幸", "山野", "好好睡", "慢半拍", "向阳", "你好", "一起", "悠悠",
]

ENGLISH = [
    "SLOW DAY", "SOFT MOOD", "EASY NOW", "GOOD AIR", "HELLO", "WEEKEND", "DAY OFF", "TAKE TIME", "STAY SOFT", "QUIETLY",
    "SIMPLE", "LOW KEY", "FRESH AIR", "SMALL JOY", "COZY", "OPEN SKY", "LITTLE SUN", "WARM NOTE", "DAILY", "CALM DOWN",
    "NICE DAY", "WALK SLOW", "LIGHTLY", "SOFT LINE", "CAFE HOUR", "MOON NOTE", "STILL HERE", "EASY WALK", "GOOD DAY", "SOFT WAVE",
    "REST MODE", "SLOWLY", "TINY JOY", "MORNING", "AFTERNOON", "GOOD NIGHT", "LOCAL DAY", "DREAM ON", "BRIGHT", "NEAR HOME",
    "PURE TYPE", "ONE DAY", "MILD SUN", "HALF PACE", "KIND WORD", "FREE TIME", "SOFT ROAD", "NO RUSH", "SUNNY", "FEEL GOOD",
]


def all_phrases() -> list[Phrase]:
    return (
        [Phrase("korean", text) for text in KOREAN]
        + [Phrase("japanese", text) for text in JAPANESE]
        + [Phrase("chinese", text) for text in CHINESE]
        + [Phrase("english", text) for text in ENGLISH]
    )


def safe_slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text or "text"


def font_for(lang: str, variant: int) -> Path:
    if lang == "korean":
        return [FONT_DIR / "malgunbd.ttf", FONT_DIR / "malgun.ttf"][variant % 2]
    if lang == "japanese":
        return [FONT_DIR / "YuGothB.ttc", FONT_DIR / "msgothic.ttc"][variant % 2]
    if lang == "chinese":
        return [FONT_DIR / "STKAITI.TTF", FONT_DIR / "msyhbd.ttc", FONT_DIR / "simhei.ttf"][variant % 3]
    return [FONT_DIR / "GOTHICB.TTF", FONT_DIR / "GOTHIC.TTF"][variant % 2]


def make_style(phrase: Phrase, index: int) -> Style:
    dark = [
        (17, 17, 17, 255),
        (28, 31, 34, 255),
        (35, 29, 27, 255),
        (21, 37, 34, 255),
    ]
    strokes = [
        (248, 244, 233, 255),
        (242, 244, 239, 255),
        (238, 232, 222, 255),
        (250, 250, 245, 255),
    ]
    accents = [
        (174, 55, 50, 255),
        (68, 105, 91, 255),
        (84, 101, 142, 255),
        (178, 132, 84, 255),
        (134, 73, 93, 255),
    ]
    accent_styles = ["underline", "dots", "thin_frame", "side_marks", "corner_marks", "small_slash"]
    return Style(
        font_path=font_for(phrase.lang, index),
        fill=dark[index % len(dark)],
        stroke=strokes[index % len(strokes)],
        accent=accents[index % len(accents)],
        accent_style=accent_styles[index % len(accent_styles)],
        tracking=(index % 7) * 2 - 4,
        line_gap=4 + (index % 4) * 5,
    )


def fit_font_size(text: str, lang: str, line_count: int) -> int:
    length = max(len(text.replace(" ", "")), 1)
    if lang == "english":
        return 210 if length <= 6 else 175 if length <= 9 else 145
    if lang == "chinese":
        return 300 if length <= 3 else 245 if length <= 4 else 205
    if lang == "japanese":
        return 285 if length <= 3 else 235 if length <= 4 else 195
    return 300 if length <= 2 else 245 if length <= 4 else 200


def split_lines(text: str, lang: str) -> tuple[str, ...]:
    if lang == "english" and " " in text:
        words = text.split()
        if len(words) == 2:
            return words[0], words[1]
    if len(text) >= 5 and lang in {"chinese", "japanese", "korean"}:
        mid = len(text) // 2
        return text[:mid], text[mid:]
    return (text,)


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(str(path), size=size)


def tracked_size(
    draw: ImageDraw.ImageDraw,
    line: str,
    font: ImageFont.FreeTypeFont,
    tracking: int,
    stroke_width: int,
) -> tuple[int, int]:
    widths: list[int] = []
    heights: list[int] = []
    for char in line:
        box = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    return sum(widths) + max(0, len(line) - 1) * tracking, max(heights or [0])


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    line: str,
    font: ImageFont.FreeTypeFont,
    style: Style,
    stroke_width: int,
) -> None:
    for char in line:
        draw.text(
            (x, y),
            char,
            font=font,
            fill=style.fill,
            stroke_width=stroke_width,
            stroke_fill=style.stroke,
        )
        box = draw.textbbox((x, y), char, font=font, stroke_width=stroke_width)
        x += box[2] - box[0] + style.tracking


def add_accent(draw: ImageDraw.ImageDraw, accent_style: str, bbox: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = bbox
    cx = (left + right) // 2
    if accent_style == "underline":
        draw.rounded_rectangle((left + 18, bottom + 38, right - 18, bottom + 50), radius=6, fill=color)
    elif accent_style == "dots":
        for offset in (-56, 0, 56):
            draw.ellipse((cx + offset - 10, bottom + 34, cx + offset + 10, bottom + 54), fill=color)
    elif accent_style == "thin_frame":
        draw.rounded_rectangle((left - 42, top - 26, right + 42, bottom + 34), radius=34, outline=color, width=7)
        draw.line((left - 12, bottom + 54, right + 12, bottom + 54), fill=color, width=7)
    elif accent_style == "side_marks":
        draw.rounded_rectangle((left - 54, top + 22, left - 37, bottom - 8), radius=8, fill=color)
        draw.rounded_rectangle((right + 37, top + 22, right + 54, bottom - 8), radius=8, fill=color)
    elif accent_style == "corner_marks":
        s = 38
        draw.line((left - 48, top - 24, left - 48 + s, top - 24), fill=color, width=8)
        draw.line((left - 48, top - 24, left - 48, top - 24 + s), fill=color, width=8)
        draw.line((right + 48, bottom + 24, right + 48 - s, bottom + 24), fill=color, width=8)
        draw.line((right + 48, bottom + 24, right + 48, bottom + 24 - s), fill=color, width=8)
    elif accent_style == "small_slash":
        draw.line((cx - 78, top - 34, cx - 48, top - 68), fill=color, width=10)
        draw.line((cx + 48, bottom + 68, cx + 78, bottom + 34), fill=color, width=10)


def render_print(index: int, phrase: Phrase) -> Path:
    style = make_style(phrase, index)
    lines = split_lines(phrase.text, phrase.lang)
    font_size = fit_font_size(phrase.text, phrase.lang, len(lines))
    stroke_width = 9 if style.stroke else 0
    font = load_font(style.font_path, font_size)

    canvas = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    sizes = [tracked_size(draw, line, font, style.tracking, stroke_width) for line in lines]
    total_h = sum(height for _, height in sizes) + max(0, len(lines) - 1) * style.line_gap
    y = (canvas.height - total_h) // 2
    boxes: list[tuple[int, int, int, int]] = []

    for line, (line_w, line_h) in zip(lines, sizes):
        x = (canvas.width - line_w) // 2
        draw_tracked(draw, x, y, line, font, style, stroke_width)
        boxes.append((x, y, x + line_w, y + line_h))
        y += line_h + style.line_gap

    bbox = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    add_accent(draw, style.accent_style, bbox, style.accent)

    crop = canvas.getbbox()
    if crop:
        pad = 100
        canvas = canvas.crop((
            max(0, crop[0] - pad),
            max(0, crop[1] - pad),
            min(canvas.width, crop[2] + pad),
            min(canvas.height, crop[3] + pad),
        ))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{index:03d}_{phrase.lang}_{safe_slug(phrase.text)}.png"
    path = OUT_DIR / filename
    canvas.save(path)
    return path


def make_overview(paths: list[Path]) -> None:
    tile_w, tile_h = 220, 270
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (236, 236, 232))
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((180, 170), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), (249, 249, 246))
        tile.paste(img, ((tile_w - img.width) // 2, 34 + (170 - img.height) // 2), img)
        draw = ImageDraw.Draw(tile)
        draw.text((10, 235), path.stem[:28], fill=(40, 40, 40))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    sheet.save(OUT_DIR / "_overview.jpg", quality=92)


def write_prompt_file(phrases: list[Phrase]) -> None:
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "简约艺术字文字印花 200 款：主体只保留文字，辅以少量下划线、点、细框、角标。",
        "所有印花必须贴在黑色、白色或深浅不同 T 恤上都清晰可见：使用高对比文字、浅色描边或深色描边，避免纯深色、纯浅色、低对比度。",
    ]
    lines.extend(f"{index:03d}. {phrase.lang}: {phrase.text}" for index, phrase in enumerate(phrases, 1))
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    phrases = all_phrases()
    if len(phrases) != 200:
        raise RuntimeError(f"Expected 200 phrases, got {len(phrases)}")
    rng = random.Random(20260609)
    rng.shuffle(phrases)
    paths = [render_print(index, phrase) for index, phrase in enumerate(phrases, 1)]
    make_overview(paths)
    write_prompt_file(phrases)
    print(f"created {len(paths)} minimal text prints")
    print(str(OUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
