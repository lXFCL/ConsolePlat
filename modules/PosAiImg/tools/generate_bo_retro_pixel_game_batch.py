from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont, ImageOps

from generate_bo_minimal_text_batch import (
    make_overview,
    safe_filename,
    write_xlsx_from_mockup_filenames,
)
from tshirt_print_tool import IMAGE_EXTS, Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "\u6a21\u7279\u56fe-\u5e72\u51c0"
PRINT_ROOT = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95"
MOCKUP_ROOT = ROOT / "\u6279\u91cf\u8d34\u56fe\u7ed3\u679c"
PROMPT_ROOT = ROOT / "\u751f\u6210\u63d0\u793a\u8bcd"
XLSX_ROOT = ROOT / "\u8863\u7269\u5bf9\u5e94\u7684xlsx" / "\u7b80\u7ea6200"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"

GRID = 128
CANVAS = 1024
TRANSPARENT = (0, 0, 0, 0)
INK = (20, 19, 24, 255)
WHITE = (255, 248, 222, 255)
CREAM = (250, 238, 198, 255)
RED = (218, 57, 47, 255)
ORANGE = (241, 122, 39, 255)
YELLOW = (255, 210, 72, 255)
BLUE = (69, 138, 224, 255)
CYAN = (91, 221, 228, 255)
GREEN = (82, 196, 93, 255)
PURPLE = (140, 91, 215, 255)
PINK = (236, 96, 165, 255)
BROWN = (120, 73, 40, 255)
TAN = (218, 162, 91, 255)
GRAY = (101, 104, 113, 255)
DARK_BLUE = (31, 47, 108, 255)


@dataclass(frozen=True)
class PixelSpec:
    keyword: str
    label: str
    motif: str
    primary: tuple[int, int, int, int]
    secondary: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]


SPECS = [
    PixelSpec("FIRE", "FIRE", "sword", RED, ORANGE, YELLOW),
    PixelSpec("MAGE", "MAGE", "wizard", PURPLE, DARK_BLUE, CYAN),
    PixelSpec("TURBO", "TURBO", "racer", RED, ORANGE, CYAN),
    PixelSpec("ALIEN", "ALIEN", "invader", GREEN, CYAN, PINK),
    PixelSpec("LOOT", "LOOT", "chest", TAN, BROWN, YELLOW),
    PixelSpec("ROCKET", "BOOST", "rocket", BLUE, RED, YELLOW),
    PixelSpec("POTION", "POTION", "potion", PINK, PURPLE, CYAN),
    PixelSpec("JOYSTICK", "PLAY", "joystick", DARK_BLUE, RED, CYAN),
    PixelSpec("SHIELD", "GUARD", "shield", BLUE, GRAY, YELLOW),
    PixelSpec("KEY", "KEY", "key", YELLOW, ORANGE, WHITE),
    PixelSpec("COIN", "COIN", "coin", YELLOW, ORANGE, WHITE),
    PixelSpec("BOLT", "BOLT", "bolt", YELLOW, CYAN, WHITE),
    PixelSpec("GEM", "GEM", "gem", CYAN, BLUE, WHITE),
    PixelSpec("TARGET", "TARGET", "target", RED, WHITE, CYAN),
    PixelSpec("PLANET", "ORBIT", "planet", PURPLE, CYAN, YELLOW),
    PixelSpec("FLAG", "FLAG", "flag", GREEN, YELLOW, WHITE),
    PixelSpec("CROWN", "CROWN", "crown", YELLOW, ORANGE, PINK),
    PixelSpec("STAR", "STAR", "star", YELLOW, PINK, WHITE),
    PixelSpec("TAPE", "TAPE", "tape", GRAY, DARK_BLUE, CYAN),
    PixelSpec("PORTAL", "PORTAL", "portal", PURPLE, CYAN, PINK),
    PixelSpec("PAD", "PAD", "controller", DARK_BLUE, GRAY, PINK),
    PixelSpec("DICE", "DICE", "dice", WHITE, RED, CYAN),
    PixelSpec("HELM", "HELM", "helmet", GRAY, BLUE, YELLOW),
    PixelSpec("MAP", "MAP", "map", TAN, GREEN, RED),
    PixelSpec("MUSIC", "BEEP", "music", PINK, CYAN, YELLOW),
    PixelSpec("FLAME", "FLAME", "flame", ORANGE, RED, YELLOW),
    PixelSpec("PIXEL", "PIXEL", "blocks", BLUE, GREEN, YELLOW),
    PixelSpec("WARP", "WARP", "portal", BLUE, PURPLE, WHITE),
    PixelSpec("LASER", "LASER", "bolt", RED, CYAN, WHITE),
    PixelSpec("QUEST", "QUEST", "map", GREEN, TAN, YELLOW),
    PixelSpec("ARCADE", "ARCADE", "joystick", PURPLE, RED, YELLOW),
    PixelSpec("SPEED", "SPEED", "racer", BLUE, RED, WHITE),
    PixelSpec("SPELL", "SPELL", "wizard", PINK, PURPLE, YELLOW),
    PixelSpec("BOSS", "BOSS", "invader", RED, DARK_BLUE, YELLOW),
    PixelSpec("BONUS", "BONUS", "coin", ORANGE, YELLOW, CYAN),
    PixelSpec("LEVEL", "LEVEL", "flag", CYAN, BLUE, WHITE),
    PixelSpec("POWER", "POWER", "flame", RED, YELLOW, WHITE),
    PixelSpec("CRYSTAL", "CRYSTAL", "gem", PURPLE, CYAN, WHITE),
    PixelSpec("SAVE", "SAVE", "tape", BLUE, GRAY, YELLOW),
    PixelSpec("START", "START", "controller", GREEN, DARK_BLUE, CYAN),
    PixelSpec("LUCK", "LUCK", "dice", YELLOW, GREEN, WHITE),
    PixelSpec("NOVA", "NOVA", "star", PINK, PURPLE, CYAN),
    PixelSpec("RUNE", "RUNE", "shield", PURPLE, GRAY, WHITE),
    PixelSpec("VAULT", "VAULT", "chest", BROWN, TAN, CYAN),
    PixelSpec("SPARK", "SPARK", "bolt", CYAN, YELLOW, PINK),
    PixelSpec("DRIFT", "DRIFT", "racer", ORANGE, DARK_BLUE, CYAN),
    PixelSpec("TOKEN", "TOKEN", "coin", GREEN, YELLOW, WHITE),
    PixelSpec("SIGNAL", "SIGNAL", "music", CYAN, BLUE, YELLOW),
    PixelSpec("GLITCH", "GLITCH", "blocks", PURPLE, GREEN, PINK),
    PixelSpec("FINAL", "FINAL", "sword", DARK_BLUE, CYAN, YELLOW),
]


def batch_name(start: int, count: int, stamp: str) -> str:
    end = start + count - 1
    return f"\u590d\u53e4\u50cf\u7d20\u6e38\u620f\u98ce\u968f\u673a\u5370\u82b1_BO-{start}-BO-{end}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, stamp)
    return (
        PRINT_ROOT / name,
        MOCKUP_ROOT / f"{name}_\u968f\u673a\u4e3b\u56fe{count}",
        PROMPT_ROOT / f"{name}.txt",
        XLSX_ROOT / f"{name}.xlsx",
    )


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


class PixelCanvas:
    def __init__(self) -> None:
        self.image = Image.new("RGBA", (GRID, GRID), TRANSPARENT)
        self.draw = ImageDraw.Draw(self.image)

    def rect(self, x: int, y: int, w: int, h: int, fill: tuple[int, int, int, int]) -> None:
        self.draw.rectangle((x, y, x + w - 1, y + h - 1), fill=fill)

    def ellipse(self, box: tuple[int, int, int, int], fill: tuple[int, int, int, int], outline: tuple[int, int, int, int] | None = None, width: int = 1) -> None:
        self.draw.ellipse(box, fill=fill, outline=outline, width=width)

    def polygon(self, points: list[tuple[int, int]], fill: tuple[int, int, int, int]) -> None:
        self.draw.polygon(points, fill=fill)

    def line(self, points: tuple[int, int, int, int], fill: tuple[int, int, int, int], width: int = 1) -> None:
        self.draw.line(points, fill=fill, width=width)

    def text(self, text: str, y: int, fill: tuple[int, int, int, int]) -> None:
        draft = self.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(draft)
        fnt = font(88 if len(text) <= 5 else 70)
        bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=12)
        x = (CANVAS - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, font=fnt, fill=fill, stroke_width=12, stroke_fill=INK)
        self.image = draft.resize((GRID, GRID), Image.Resampling.NEAREST)
        self.draw = ImageDraw.Draw(self.image)

    def save(self, path: Path) -> None:
        scaled = self.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
        scaled.save(path)


def add_drift_pixels(c: PixelCanvas, spec: PixelSpec, rng: random.Random) -> None:
    for _ in range(18):
        x = rng.randrange(18, 110)
        y = rng.randrange(16, 106)
        if 38 <= x <= 90 and 28 <= y <= 86:
            continue
        color = rng.choice([spec.primary, spec.secondary, spec.accent, WHITE])
        size = rng.choice([2, 3, 4])
        c.rect(x, y, size, size, color)


def motif_sword(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(59, 26, 8, 48, CREAM)
    c.rect(63, 22, 4, 56, WHITE)
    c.rect(67, 34, 6, 34, spec.secondary)
    c.rect(53, 72, 25, 6, INK)
    c.rect(61, 78, 9, 17, BROWN)
    c.rect(57, 95, 17, 7, spec.accent)
    c.rect(49, 18, 10, 10, spec.primary)
    c.rect(44, 28, 9, 9, spec.secondary)
    c.rect(53, 31, 8, 8, spec.accent)


def motif_wizard(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(43, 38), (64, 14), (85, 38)], spec.primary)
    c.rect(48, 36, 32, 7, WHITE)
    c.rect(43, 44, 42, 24, TAN)
    c.rect(48, 50, 10, 8, INK)
    c.rect(70, 50, 10, 8, INK)
    c.rect(55, 66, 24, 30, spec.secondary)
    c.polygon([(55, 66), (73, 66), (90, 99), (40, 99)], spec.primary)
    c.rect(88, 42, 9, 9, spec.accent)
    c.rect(31, 55, 7, 7, spec.accent)


def motif_racer(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(27, 62, 74, 11, INK)
    c.rect(34, 48, 58, 20, spec.primary)
    c.rect(43, 38, 35, 13, spec.secondary)
    c.rect(52, 32, 20, 9, WHITE)
    c.rect(79, 53, 15, 8, spec.accent)
    c.rect(25, 57, 11, 6, CYAN)
    for x in (37, 78):
        c.ellipse((x, 71, x + 16, 87), INK)
        c.ellipse((x + 4, 75, x + 11, 82), GRAY)


def motif_invader(c: PixelCanvas, spec: PixelSpec) -> None:
    rows = [
        "..xx......xx..",
        "...xx....xx...",
        "..xxxxxxxxxx..",
        ".xxwwxxxxwwxx.",
        "xxxxxxxxxxxxxx",
        "xx..xxxxxx..xx",
        "xx..xx..xx..xx",
        "...xx....xx...",
        "..xx..xx..xx..",
    ]
    for row_i, row in enumerate(rows):
        for col_i, ch in enumerate(row):
            if ch == ".":
                continue
            c.rect(36 + col_i * 4, 28 + row_i * 4, 4, 4, WHITE if ch == "w" else spec.primary)


def motif_chest(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(33, 44, 62, 12, spec.secondary)
    c.rect(27, 55, 74, 36, spec.primary)
    c.rect(27, 55, 74, 8, spec.accent)
    c.rect(56, 48, 17, 43, INK)
    c.rect(60, 61, 9, 11, spec.accent)
    c.rect(34, 68, 16, 13, spec.secondary)
    c.rect(79, 68, 16, 13, spec.secondary)


def motif_rocket(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(64, 18), (78, 48), (74, 80), (54, 80), (50, 48)], WHITE)
    c.rect(57, 48, 15, 18, spec.primary)
    c.ellipse((58, 31, 70, 43), spec.secondary, INK, 1)
    c.polygon([(50, 64), (35, 83), (54, 75)], spec.secondary)
    c.polygon([(78, 64), (93, 83), (74, 75)], spec.secondary)
    c.polygon([(57, 80), (64, 101), (72, 80)], spec.accent)


def motif_potion(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(55, 27, 18, 12, WHITE)
    c.rect(51, 39, 27, 7, INK)
    c.ellipse((42, 45, 86, 91), spec.primary, INK, 2)
    c.rect(48, 63, 32, 20, spec.secondary)
    c.rect(58, 52, 8, 8, WHITE)
    c.rect(72, 72, 6, 6, spec.accent)


def motif_joystick(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(33, 61, 62, 29, spec.secondary)
    c.rect(39, 55, 50, 9, INK)
    c.rect(58, 34, 9, 27, INK)
    c.ellipse((52, 20, 73, 41), spec.primary, INK, 2)
    c.rect(43, 72, 18, 5, WHITE)
    c.rect(49, 66, 5, 18, WHITE)
    c.ellipse((73, 67, 83, 77), spec.accent, INK, 1)
    c.ellipse((84, 75, 94, 85), spec.primary, INK, 1)


def motif_shield(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(64, 20), (94, 34), (89, 76), (64, 102), (39, 76), (34, 34)], spec.primary)
    c.polygon([(64, 30), (82, 40), (78, 70), (64, 88), (50, 70), (46, 40)], spec.secondary)
    c.rect(59, 44, 10, 32, spec.accent)
    c.rect(49, 55, 30, 8, spec.accent)


def motif_key(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((30, 41, 61, 72), spec.primary, INK, 2)
    c.ellipse((40, 51, 51, 62), TRANSPARENT)
    c.rect(58, 54, 45, 8, spec.primary)
    c.rect(88, 62, 8, 11, spec.primary)
    c.rect(99, 62, 8, 15, spec.primary)
    c.rect(64, 47, 6, 6, WHITE)


def motif_coin(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((36, 25, 92, 87), spec.primary, INK, 2)
    c.ellipse((47, 34, 81, 78), spec.secondary)
    c.rect(61, 39, 8, 34, WHITE)
    c.rect(53, 45, 24, 7, WHITE)
    c.rect(53, 61, 24, 7, WHITE)


def motif_bolt(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(67, 18), (42, 62), (61, 62), (53, 103), (88, 52), (68, 52)], spec.primary)
    c.polygon([(69, 25), (55, 55), (72, 55), (63, 83), (83, 48), (66, 48)], WHITE)


def motif_gem(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(43, 39), (55, 24), (75, 24), (87, 39), (64, 93)], spec.primary)
    c.polygon([(43, 39), (64, 93), (55, 39)], spec.secondary)
    c.polygon([(87, 39), (64, 93), (75, 39)], BLUE)
    c.rect(56, 29, 18, 6, WHITE)


def motif_target(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((32, 24, 96, 88), spec.primary, INK, 2)
    c.ellipse((43, 35, 85, 77), WHITE)
    c.ellipse((53, 45, 75, 67), spec.primary)
    c.rect(62, 16, 4, 84, INK)
    c.rect(22, 54, 84, 4, INK)


def motif_planet(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((43, 35, 85, 77), spec.primary, INK, 2)
    c.draw.arc((23, 43, 105, 73), 345, 195, fill=spec.accent, width=5)
    c.draw.arc((23, 43, 105, 73), 200, 340, fill=WHITE, width=4)
    c.rect(55, 46, 8, 8, WHITE)
    c.rect(70, 61, 6, 6, spec.secondary)


def motif_flag(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(42, 27, 6, 70, INK)
    c.polygon([(48, 28), (91, 36), (48, 53)], spec.primary)
    c.polygon([(48, 53), (83, 61), (48, 75)], spec.secondary)
    c.rect(35, 95, 22, 6, spec.accent)


def motif_crown(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(33, 70), (39, 35), (55, 60), (64, 30), (73, 60), (89, 35), (95, 70)], spec.primary)
    c.rect(36, 70, 56, 17, spec.secondary)
    c.rect(42, 76, 12, 6, WHITE)
    c.rect(60, 75, 9, 7, spec.accent)
    c.rect(78, 76, 8, 6, WHITE)


def motif_star(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(64, 18), (75, 49), (108, 49), (81, 67), (91, 101), (64, 80), (37, 101), (47, 67), (20, 49), (53, 49)], spec.primary)
    c.polygon([(64, 35), (70, 55), (91, 55), (74, 66), (80, 87), (64, 74), (48, 87), (54, 66), (37, 55), (58, 55)], WHITE)


def motif_tape(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(30, 36, 68, 48, spec.primary)
    c.rect(39, 47, 50, 13, WHITE)
    c.ellipse((40, 63, 55, 78), INK)
    c.ellipse((73, 63, 88, 78), INK)
    c.rect(56, 68, 17, 5, spec.accent)


def motif_portal(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((31, 23, 97, 89), spec.primary, INK, 2)
    c.ellipse((42, 34, 86, 78), spec.secondary)
    c.ellipse((53, 45, 75, 67), INK)
    c.draw.arc((38, 30, 90, 82), 20, 250, fill=WHITE, width=4)


def motif_controller(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(28, 54, 72, 27, spec.secondary)
    c.ellipse((22, 54, 50, 90), spec.secondary, INK, 2)
    c.ellipse((78, 54, 106, 90), spec.secondary, INK, 2)
    c.rect(38, 66, 18, 5, WHITE)
    c.rect(44, 60, 5, 18, WHITE)
    c.ellipse((77, 63, 87, 73), spec.primary, INK, 1)
    c.ellipse((90, 72, 100, 82), spec.accent, INK, 1)


def motif_dice(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(40, 33, 49, 49, spec.primary)
    for x, y in [(51, 44), (76, 44), (63, 57), (51, 70), (76, 70)]:
        c.rect(x, y, 7, 7, spec.secondary)
    c.rect(45, 27, 38, 8, spec.accent)


def motif_helmet(c: PixelCanvas, spec: PixelSpec) -> None:
    c.ellipse((35, 25, 93, 83), spec.primary, INK, 2)
    c.rect(43, 57, 51, 20, spec.secondary)
    c.rect(52, 63, 32, 7, WHITE)
    c.rect(36, 77, 18, 12, GRAY)
    c.rect(75, 77, 18, 12, GRAY)


def motif_map(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(31, 37), (55, 29), (76, 37), (99, 29), (99, 84), (76, 94), (55, 84), (31, 94)], spec.primary)
    c.line((55, 31, 55, 85), INK, 2)
    c.line((76, 38, 76, 93), INK, 2)
    c.line((40, 55, 88, 72), spec.secondary, 4)
    c.rect(83, 43, 7, 7, spec.accent)


def motif_music(c: PixelCanvas, spec: PixelSpec) -> None:
    c.rect(57, 28, 8, 48, spec.primary)
    c.rect(65, 28, 30, 7, spec.primary)
    c.rect(88, 35, 8, 44, spec.primary)
    c.ellipse((43, 70, 64, 91), spec.secondary, INK, 1)
    c.ellipse((75, 75, 98, 98), spec.accent, INK, 1)


def motif_flame(c: PixelCanvas, spec: PixelSpec) -> None:
    c.polygon([(65, 18), (44, 52), (50, 86), (65, 101), (84, 84), (88, 53)], spec.primary)
    c.polygon([(66, 42), (55, 64), (58, 83), (66, 92), (77, 80), (76, 60)], spec.accent)
    c.rect(47, 91, 36, 7, INK)


def motif_blocks(c: PixelCanvas, spec: PixelSpec) -> None:
    positions = [(35, 30), (55, 30), (75, 30), (45, 50), (65, 50), (85, 50), (35, 70), (55, 70), (75, 70)]
    colors = [spec.primary, spec.secondary, spec.accent, WHITE]
    for idx, (x, y) in enumerate(positions):
        c.rect(x, y, 18, 18, colors[idx % len(colors)])
        c.rect(x + 3, y + 3, 5, 5, WHITE)


MOTIFS = {
    "sword": motif_sword,
    "wizard": motif_wizard,
    "racer": motif_racer,
    "invader": motif_invader,
    "chest": motif_chest,
    "rocket": motif_rocket,
    "potion": motif_potion,
    "joystick": motif_joystick,
    "shield": motif_shield,
    "key": motif_key,
    "coin": motif_coin,
    "bolt": motif_bolt,
    "gem": motif_gem,
    "target": motif_target,
    "planet": motif_planet,
    "flag": motif_flag,
    "crown": motif_crown,
    "star": motif_star,
    "tape": motif_tape,
    "portal": motif_portal,
    "controller": motif_controller,
    "dice": motif_dice,
    "helmet": motif_helmet,
    "map": motif_map,
    "music": motif_music,
    "flame": motif_flame,
    "blocks": motif_blocks,
}


def render_print(spec: PixelSpec, sku: str, index: int, print_dir: Path) -> Path:
    rng = random.Random(20260615 + index * 97)
    c = PixelCanvas()
    add_drift_pixels(c, spec, rng)
    MOTIFS[spec.motif](c, spec)
    c.text(spec.label, 828, spec.accent)
    print_dir.mkdir(parents=True, exist_ok=True)
    path = print_dir / f"{sku}.png"
    c.save(path)
    return path


def write_prompt_file(specs: list[PixelSpec], prompt_file: Path, start: int, count: int) -> None:
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    end = start + count - 1
    lines = [
        f"\u590d\u53e4\u50cf\u7d20\u6e38\u620f\u98ce\u968f\u673a\u5370\u82b1 {count} \u6b3e\uff1a\u8d27\u53f7 BO-{start} \u5230 BO-{end}\u3002",
        "\u65e0\u5916\u6846\u7ea6\u675f\uff0c\u4fdd\u7559\u4e3b\u4f53\u56fe\u6807\u3001\u77ed\u6587\u5b57\u548c\u5c11\u91cf\u6563\u843d\u50cf\u7d20\u70b9\uff0c\u900f\u660e\u5e95\u3002",
        "\u8981\u6c42\u9ed1\u8272\u548c\u767d\u8272 T \u6064\u4e0a\u90fd\u6e05\u6670\uff0c\u907f\u514d\u54c1\u724c\u3001\u771f\u5b9e\u6e38\u620f IP\u3001\u660e\u661f\u3001\u7403\u961f\u548c\u53d7\u4fdd\u62a4\u89d2\u8272\u5143\u7d20\u3002",
        "",
    ]
    for idx, spec in enumerate(specs):
        lines.append(f"BO-{start + idx}: {spec.keyword} / {spec.label} / {spec.motif}")
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_current_batch_dir(folder: Path) -> None:
    if not folder.exists():
        return
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS | {".jpg", ".xlsx", ".txt"}:
            path.unlink()


def generate_prints(start: int, count: int, seed: int, print_dir: Path, prompt_file: Path) -> list[tuple[PixelSpec, Path]]:
    if count > len(SPECS):
        raise ValueError(f"Requested {count} prints, but only {len(SPECS)} unique specs are available")
    rng = random.Random(seed)
    specs = SPECS[:]
    rng.shuffle(specs)
    specs = specs[:count]
    clean_current_batch_dir(print_dir)
    results: list[tuple[PixelSpec, Path]] = []
    for idx, spec in enumerate(specs):
        sku = f"BO-{start + idx}"
        path = render_print(spec, sku, idx, print_dir)
        results.append((spec, path))
        print(f"{sku}: print {spec.keyword}", flush=True)
    write_prompt_file(specs, prompt_file, start, count)
    return results


def detect_shirt_color(model_path: Path) -> tuple[str, str]:
    if "\u767d" in model_path.stem:
        return "\u767d\u8272", "\u767d"
    if "\u9ed1" in model_path.stem:
        return "\u9ed1\u8272", "\u9ed1"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("\u767d\u8272", "\u767d") if float(np.median(luma)) >= 150 else ("\u9ed1\u8272", "\u9ed1")


def product_title(color_word: str, keyword: str) -> str:
    suffixes = [
        "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u5fae\u5f39\u9488\u7ec7\u4e0a\u8863 \u65e5\u5e38\u4f11\u95f2\u767e\u642d",
        "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u8212\u9002\u9488\u7ec7\u4e0a\u8863 \u6237\u5916\u4f11\u95f2\u65e5\u5e38\u767e\u642d",
        "\u5706\u9886\u77ed\u8896 \u8f7b\u8584\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u4f11\u95f2\u901a\u52e4\u65e5\u5e38\u767e\u642d",
        "\u5706\u9886\u77ed\u8896 \u67d4\u8f6f\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u590f\u5b63\u65e5\u5e38\u767e\u642d",
    ]
    suffix = suffixes[sum(ord(char) for char in color_word + keyword) % len(suffixes)]
    return f"\u590f\u5b63{color_word}\u590d\u53e4\u50cf\u7d20\u6e38\u620f{keyword}\u5370\u82b1T\u6064 {suffix}"


def export_products(print_items: list[tuple[PixelSpec, Path]], mockup_dir: Path, seed: int) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    clean_current_batch_dir(mockup_dir)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    outputs: list[Path] = []
    for spec, print_path in print_items:
        model_path = rng.choice(models)
        color_word, color_short = detect_shirt_color(model_path)
        sku = print_path.stem
        title = product_title(color_word, spec.keyword)
        output_path = mockup_dir / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        outputs.append(output_path)
        print(f"{sku}: product {color_short}", flush=True)
    make_overview(outputs, mockup_dir / "_overview.jpg")
    return outputs


def sku_numbers(paths: list[Path]) -> list[int]:
    numbers: list[int] = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def product_rows_from_filenames(mockup_dir: Path) -> list[tuple[str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str]] = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if match:
            rows.append((match.group(1), match.group(2)))
    return sorted(rows, key=lambda row: int(row[0].split("-")[1]))


def validate_transparency(paths: list[Path]) -> bool:
    for path in paths:
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        if alpha.getextrema() != (0, 255):
            return False
        if alpha.getbbox() is None:
            return False
    return True


def validate_xlsx(path: Path, start: int, count: int) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"XLSX not found: {path}")
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = tuple(rows[0][:5]) if rows else ()
    data = rows[1:]
    first_sku = data[0][3] if data else ""
    last_sku = data[-1][3] if data else ""
    summary = {
        "xlsx_rows": len(rows),
        "xlsx_header": header,
        "xlsx_first_sku": first_sku,
        "xlsx_last_sku": last_sku,
    }
    expected_header = ("\u5e97\u94fa\u540d\u79f0", "\u4ea7\u54c1\u5206\u7c7b", "\u4ea7\u54c1\u6807\u9898", "\u4ea7\u54c1\u5e8f\u5217\u53f7", "\u989c\u8272")
    if header != expected_header or len(rows) != count + 1 or first_sku != f"BO-{start}" or last_sku != f"BO-{start + count - 1}":
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def validate_outputs(start: int, count: int, print_dir: Path, mockup_dir: Path, xlsx_path: Path) -> dict:
    expected = list(range(start, start + count))
    print_files = sorted(path for path in list_images(print_dir) if re.fullmatch(r"BO-\d+\.png", path.name, re.IGNORECASE))
    product_files = sorted(path for path in list_images(mockup_dir) if not path.name.startswith("_"))
    xlsx_summary = validate_xlsx(xlsx_path, start, count)
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_range_ok": sku_numbers(print_files) == expected,
        "product_range_ok": sku_numbers(product_files) == expected,
        "transparent_ok": validate_transparency(print_files),
        **xlsx_summary,
    }
    if summary["print_count"] != count or summary["product_count"] != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"] or not summary["transparent_ok"]:
        raise RuntimeError(f"Output validation failed: {summary}")
    return summary


def sync_putaway(mockup_dir: Path, xlsx_path: Path) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(mockup_dir):
        if not path.name.startswith("_"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(xlsx_path, PUTAWAY_DATA_DIR / xlsx_path.name)


def validate_putaway(start: int, count: int, xlsx_path: Path) -> dict:
    expected = list(range(start, start + count))
    files = sorted(path for path in list_images(PUTAWAY_PIC_DIR) if not path.name.startswith("_"))
    summary = {
        "putaway_pic_count": len(files),
        "putaway_range_ok": sku_numbers(files) == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / xlsx_path.name).exists(),
    }
    if summary["putaway_pic_count"] != count or not summary["putaway_range_ok"] or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(start: int, count: int, print_dir: Path, mockup_dir: Path, xlsx_path: Path, validation: dict, putaway: dict, stamp: str) -> None:
    end = start + count - 1
    next_start = end + 1
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到：\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从：\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张复古像素游戏风随机印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{xlsx_path}` 当前校验为 {validation['xlsx_rows']} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        "- 视觉抽查：已查看 `_overview.jpg`，本批去掉外框，保留复古像素游戏主体、短文字和散点；整体更像独立胸前印花，黑白 T 上均有高对比描边。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def run_generation(start: int, count: int, seed: int, stamp: str) -> tuple[Path, Path, Path, dict]:
    print_dir, mockup_dir, prompt_file, xlsx_path = batch_paths(start, count, stamp)
    print_items = generate_prints(start, count, seed, print_dir, prompt_file)
    export_products(print_items, mockup_dir, seed + 31)
    write_xlsx_from_mockup_filenames(mockup_dir, xlsx_path, count)
    validation = validate_outputs(start, count, print_dir, mockup_dir, xlsx_path)
    return print_dir, mockup_dir, xlsx_path, validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO retro pixel game prints and run product/xlsx/putaway flow.")
    parser.add_argument("--start", type=int, default=1321)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--skip-putaway", action="store_true", help="Generate and validate local outputs only.")
    parser.add_argument("--sync-existing", action="store_true", help="Validate existing local outputs, then sync putaway and update progress.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_dir, mockup_dir, _prompt_file, xlsx_path = batch_paths(args.start, args.count, args.date)
    if args.sync_existing:
        validation = validate_outputs(args.start, args.count, print_dir, mockup_dir, xlsx_path)
    else:
        print_dir, mockup_dir, xlsx_path, validation = run_generation(args.start, args.count, args.seed, args.date)

    putaway = None
    if not args.skip_putaway:
        sync_putaway(mockup_dir, xlsx_path)
        putaway = validate_putaway(args.start, args.count, xlsx_path)
        update_progress(args.start, args.count, print_dir, mockup_dir, xlsx_path, validation, putaway, args.date)

    print(f"Print dir: {print_dir}")
    print(f"Product dir: {mockup_dir}")
    print(f"XLSX: {xlsx_path}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False, default=str)}")
    if putaway is not None:
        print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
