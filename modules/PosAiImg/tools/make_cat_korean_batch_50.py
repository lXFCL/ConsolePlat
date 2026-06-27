from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tshirt_print_tool as tshirt  # noqa: E402
from make_cat_text_obvious_variants import (  # noqa: E402
    DEFAULT_SOURCE,
    FONT,
    draw_cap,
    draw_tiny_chain,
    make_base,
    remove_top_text,
    rounded_glasses,
)
from make_cat_text_simple_local_variants import cat_fill_mask, recolor_region  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PRINT_DIR = ROOT / "印花图_透明底" / "猫咪韩文风格50张_2026-06-15"
MOCKUP_DIR = ROOT / "批量贴图结果" / "猫咪韩文风格50张_2026-06-15"
MODEL_DIR = ROOT / "模特图-干净"


TEXTS = [
    "\uc624\ub298\uc740 \uc26c\ub294 \ub0a0",
    "\uad1c\ucc2e\uc544 \ucc9c\ucc9c\ud788",
    "\uc0dd\uac01\ubcf4\ub2e4 \uadc0\uc5ec\uc6c0",
    "\uc544\ubb34\ud2bc \ud589\ubcf5\ud574",
    "\ub300\ucda9 \uba4b\uc9c4 \ud558\ub8e8",
    "\ucee4\ud53c\ub294 \ud544\uc218",
    "\uc624\ub298\ub3c4 \uc0b4\uc544\ub0a8\uc74c",
    "\ub9d0\ubcf4\ub2e4 \ud589\ub3d9",
    "\ub098\ub984 \uc9c4\uc9c0\ud574",
    "\uc9c0\uae08\uc740 \uba4d\ud558\uac8c",
    "\uc791\uac8c \uc6c3\uc790",
    "\ub0b4\uc77c\uc740 \ub354 \uc88b\uc544",
    "\uae30\ubd84\uc740 \uad1c\ucc2e\uc74c",
    "\uc2a4\ud0c0\uc77c\uc740 \uc790\uc720",
    "\ub208\uce58\ubcf4\uc9c0 \ub9d0\uc790",
    "\uc870\uc6a9\ud55c \ud798",
    "\ubcc4\uc77c \uc544\ub2d8",
    "\uc624\ub298 \uc880 \uba4b\uc9d0",
    "\uc2dc\ud06c\ud55c \uace0\uc591\uc774",
    "\uace0\uae30\ubcf4\ub2e4 \uc0dd\uc120",
    "\uc9c0\uce5c \uc6c3\uc74c",
    "\ud558\ub8e8 \ud55c \uc785",
    "\uac00\ubccd\uac8c \uac00\uc790",
    "\uadc0\ucc2e\uc544\ub3c4 \uad1c\ucc2e\uc544",
    "\ubc14\ub78c\ucc98\ub7fc \uc0b4\uc790",
    "\uc624\ub298\uc758 \ud0dc\ub3c4",
    "\uc791\uc740 \ubc18\ud56d",
    "\uc6c3\uae34\ub370 \uc9c4\uc9c0",
    "\uc5ec\uc720\ub294 \uc2b5\uad00",
    "\ub098\ub9cc\uc758 \ubc15\uc790",
    "\uc0dd\uc120\uc740 \uc9c4\ub9ac",
    "\uc774\ub300\ub85c \uc88b\uc544",
    "\ub108\ubb34 \uc560\uc4f0\uc9c0 \ub9c8",
    "\uc5b4\ucc28\ud53c \uadc0\uc5ec\uc6c0",
    "\uc870\uae08\ub9cc \ub354",
    "\ud3ec\uae30\ub294 \uc544\uc9c1",
    "\ub098\ub294 \ub098\uc758 \ud3b8",
    "\uc798\ud558\uace0 \uc788\uc5b4",
    "\uc544\ubb34\ub3c4 \ubab0\ub77c",
    "\ub098\uc05c \uc0dd\uac01 \uc548\ud568",
    "\uc5b4\ub290\uc0c8 \ubc24",
    "\uc2ac\uc9dd \uba4b\uc788\uc5b4",
    "\ub290\ub9ac\uac8c \uc815\ud655\ud788",
    "\uc5ec\uae30\uae4c\uc9c0 \uc88b\uc544",
    "\ud558\ub098\ub9cc \ub354",
    "\uace0\uc591\uc774\ub294 \uc54c\uc544",
    "\uc624\ub298\uc740 \ub0b4 \ud398\uc774\uc2a4",
    "\uc7a0\uae50 \uc26c\uc5b4\uac00",
    "\ub09c \uadf8\ub0e5 \ub098",
    "\uadf8\ub7f0\ub300\ub85c \uba4b\uc9d0",
]


@dataclass(frozen=True)
class VariantSpec:
    name: str
    text: str
    body: tuple[int, int, int] | None
    glasses: tuple[int, int, int, int]
    glasses_shape: str
    cap: tuple[int, int, int, int] | None
    chain: bool
    headwear: str
    torso: str
    accent: tuple[int, int, int, int]
    text_y: int


BODY_COLORS = [
    None,
    (96, 124, 111),
    (151, 128, 101),
    (125, 107, 146),
    (132, 132, 126),
    (108, 129, 154),
    (118, 139, 118),
    (155, 124, 116),
    (139, 136, 112),
    (112, 121, 142),
]
GLASSES = [
    ((18, 18, 18, 255), "wide"),
    ((196, 72, 64, 255), "round"),
    ((237, 189, 70, 255), "default"),
    ((58, 93, 188, 255), "star"),
    ((50, 145, 133, 255), "wide"),
    ((90, 90, 90, 255), "round"),
    ((231, 129, 63, 255), "default"),
    ((45, 105, 82, 255), "star"),
]
CAPS = [None, None, None, (42, 42, 42, 255), (90, 82, 64, 255), (52, 74, 112, 255)]
HEADWEAR = ["none", "cap", "beanie", "headband", "side_pin", "visor", "small_crown", "beret"]
TORSO = ["none", "scarf", "badge", "stripe", "dots", "necklace", "star_pin", "mini_panel"]
ACCENTS = [
    (18, 18, 18, 255),
    (196, 72, 64, 255),
    (237, 189, 70, 255),
    (58, 93, 188, 255),
    (50, 145, 133, 255),
    (120, 82, 156, 255),
    (231, 129, 63, 255),
    (45, 105, 82, 255),
    (230, 230, 220, 255),
    (88, 108, 130, 255),
]


def draw_korean_text(img: Image.Image, text: str, y: int) -> Image.Image:
    out = img.copy().convert("RGBA")
    layer = Image.new("RGBA", out.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    font_size = 56
    font = ImageFont.truetype(str(FONT), font_size)
    while font_size > 38 and draw.textbbox((0, 0), text, font=font)[2] > 760:
        font_size -= 2
        font = ImageFont.truetype(str(FONT), font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (out.width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=(14, 14, 14, 255), stroke_width=4, stroke_fill=(255, 255, 255, 245))
    out.alpha_composite(layer)
    return out


def draw_beanie(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.pieslice((316, 214, 615, 354), 180, 360, fill=fill, outline=(18, 18, 18, 255), width=6)
    d.rounded_rectangle((333, 296, 598, 332), radius=14, fill=fill, outline=(18, 18, 18, 255), width=5)
    for x in range(354, 580, 36):
        d.line((x, 222, x + 8, 325), fill=(255, 255, 255, 80), width=4)
    return out


def draw_headband(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((312, 286, 630, 319), radius=14, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.polygon([(600, 304), (668, 286), (633, 340)], fill=fill, outline=(18, 18, 18, 255))
    d.line((330, 304, 586, 304), fill=(255, 255, 255, 95), width=4)
    return out


def draw_visor(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.arc((330, 220, 590, 348), 190, 340, fill=(18, 18, 18, 255), width=7)
    d.rounded_rectangle((360, 286, 592, 318), radius=14, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.polygon([(548, 292), (690, 306), (560, 332)], fill=fill, outline=(18, 18, 18, 255))
    return out


def draw_beret(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.ellipse((320, 225, 600, 326), fill=fill, outline=(18, 18, 18, 255), width=6)
    d.polygon([(476, 226), (505, 197), (520, 232)], fill=fill, outline=(18, 18, 18, 255))
    d.arc((360, 244, 560, 315), 185, 340, fill=(255, 255, 255, 90), width=5)
    return out


def draw_side_pin(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.ellipse((548, 280, 605, 337), fill=fill, outline=(18, 18, 18, 255), width=5)
    d.line((562, 307, 592, 307), fill=(255, 255, 255, 150), width=4)
    d.line((577, 292, 577, 322), fill=(255, 255, 255, 150), width=4)
    return out


def draw_small_crown(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    pts = [(360, 275), (386, 220), (420, 270), (460, 214), (501, 270), (536, 222), (560, 275)]
    d.polygon(pts, fill=fill, outline=(18, 18, 18, 255))
    d.line((360, 275, 560, 275), fill=(18, 18, 18, 255), width=6)
    return out


def apply_headwear(img: Image.Image, kind: str, accent: tuple[int, int, int, int], cap: tuple[int, int, int, int] | None) -> Image.Image:
    if kind == "cap":
        return draw_cap(img, cap or accent)
    if kind == "beanie":
        return draw_beanie(img, accent)
    if kind == "headband":
        return draw_headband(img, accent)
    if kind == "side_pin":
        return draw_side_pin(img, accent)
    if kind == "visor":
        return draw_visor(img, accent)
    if kind == "small_crown":
        return draw_small_crown(img, accent)
    if kind == "beret":
        return draw_beret(img, accent)
    return img


def draw_scarf(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((276, 522, 565, 570), radius=22, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.polygon([(478, 560), (540, 560), (512, 690), (462, 674)], fill=fill, outline=(18, 18, 18, 255))
    d.line((300, 545, 536, 545), fill=(255, 255, 255, 90), width=4)
    return out


def draw_badge(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((300, 592, 384, 650), radius=16, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.line((318, 620, 368, 620), fill=(255, 255, 255, 160), width=4)
    return out


def draw_stripe(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    for y in (612, 660, 708):
        d.line((250, y, 430, y + 18), fill=fill, width=14)
        d.line((250, y, 430, y + 18), fill=(18, 18, 18, 220), width=3)
    return out


def draw_dots(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    for row, y in enumerate((598, 638, 678)):
        for col in range(4):
            x = 285 + col * 42 + (row % 2) * 18
            d.ellipse((x, y, x + 18, y + 18), fill=fill, outline=(18, 18, 18, 255), width=3)
    return out


def draw_star_pin(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    cx, cy, radius = 335, 600, 34
    pts = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        a = -3.14159 / 2 + i * 3.14159 / 5
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(pts, fill=fill, outline=(18, 18, 18, 255))
    return out


def draw_mini_panel(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((282, 600, 430, 682), radius=18, fill=(255, 255, 255, 230), outline=(18, 18, 18, 255), width=5)
    d.rounded_rectangle((302, 620, 410, 645), radius=10, fill=fill, outline=(18, 18, 18, 255), width=3)
    d.line((306, 664, 402, 664), fill=(18, 18, 18, 255), width=4)
    return out


def apply_torso(img: Image.Image, kind: str, accent: tuple[int, int, int, int]) -> Image.Image:
    if kind == "scarf":
        return draw_scarf(img, accent)
    if kind == "badge":
        return draw_badge(img, accent)
    if kind == "stripe":
        return draw_stripe(img, accent)
    if kind == "dots":
        return draw_dots(img, accent)
    if kind == "necklace":
        return draw_tiny_chain(img)
    if kind == "star_pin":
        return draw_star_pin(img, accent)
    if kind == "mini_panel":
        return draw_mini_panel(img, accent)
    return img


def build_specs(count: int) -> list[VariantSpec]:
    specs: list[VariantSpec] = []
    for idx in range(count):
        glasses, shape = GLASSES[idx % len(GLASSES)]
        body = BODY_COLORS[(idx * 3) % len(BODY_COLORS)]
        cap = CAPS[(idx * 5) % len(CAPS)]
        headwear = HEADWEAR[(idx * 5 + idx // 8) % len(HEADWEAR)]
        torso = TORSO[(idx * 3 + idx // 5) % len(TORSO)]
        accent = ACCENTS[(idx * 7 + 2) % len(ACCENTS)]
        specs.append(
            VariantSpec(
                name=f"cat_korean_{idx + 1:02d}",
                text=TEXTS[idx % len(TEXTS)],
                body=body,
                glasses=glasses,
                glasses_shape=shape,
                cap=cap,
                chain=(idx % 7 in {4, 6}),
                headwear=headwear,
                torso=torso,
                accent=accent,
                text_y=76 + (idx % 3) * 5,
            )
        )
    return specs


def make_print(base: Image.Image, spec: VariantSpec) -> Image.Image:
    img = base.copy().convert("RGBA")
    if spec.body is not None:
        img = recolor_region(img, cat_fill_mask(img), spec.body, 0.84)
    img = apply_headwear(img, spec.headwear, spec.accent, spec.cap)
    img = rounded_glasses(img, spec.glasses, spec.glasses_shape)
    img = apply_torso(img, spec.torso, spec.accent)
    if spec.chain:
        img = draw_tiny_chain(img)
    img = draw_korean_text(img, spec.text, spec.text_y)
    return img


def make_overview(paths: list[Path], output: Path, columns: int = 10, thumb: int = 220) -> None:
    rows = (len(paths) + columns - 1) // columns
    label_h = 34
    sheet = Image.new("RGB", (columns * thumb, rows * (thumb + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (thumb - 12, thumb - 12), Image.Resampling.LANCZOS)
        x0 = (index % columns) * thumb
        y0 = (index // columns) * (thumb + label_h)
        sheet.paste(preview, (x0 + (thumb - preview.width) // 2, y0 + (thumb - preview.height) // 2))
        draw.text((x0 + 8, y0 + thumb + 8), path.stem[-14:], fill=(20, 20, 20))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def export_mockups(print_paths: list[Path], output_dir: Path) -> list[Path]:
    models = tshirt.list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    placement = tshirt.Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    rng = random.Random(20260615)
    shuffled = models[:]
    rng.shuffle(shuffled)
    for idx, print_path in enumerate(print_paths):
        model = shuffled[idx % len(shuffled)]
        output = output_dir / f"{idx + 1:02d}_{model.stem}_{print_path.stem}.png"
        tshirt.composite_one(model, print_path, output, placement)
        outputs.append(output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 50 controlled Korean cat print variants and one mockup each.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--print-dir", type=Path, default=PRINT_DIR)
    parser.add_argument("--mockup-dir", type=Path, default=MOCKUP_DIR)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--size", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.print_dir.mkdir(parents=True, exist_ok=True)
    args.mockup_dir.mkdir(parents=True, exist_ok=True)

    base = remove_top_text(make_base(args.source, args.size))
    base.save(args.print_dir / "_base_without_old_text.png")
    print_paths: list[Path] = []
    for spec in build_specs(args.count):
        path = args.print_dir / f"{spec.name}.png"
        make_print(base, spec).save(path)
        print_paths.append(path)
        print(f"saved print {path}")

    make_overview(print_paths, args.print_dir / "_overview.jpg")
    mockup_paths = export_mockups(print_paths, args.mockup_dir)
    make_overview(mockup_paths, args.mockup_dir / "_overview.jpg", columns=10, thumb=240)
    print(f"Print dir: {args.print_dir}")
    print(f"Mockup dir: {args.mockup_dir}")
    print(f"Print count: {len(print_paths)}")
    print(f"Mockup count: {len(mockup_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
