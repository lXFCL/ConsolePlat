from __future__ import annotations

import math
import re
import shutil
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import generate_bo_retro_nature_batch as base
import generate_bo_vaporwave_batch as vapor


START = 956
COUNT = 50
STAMP = "2026-06-14"
BAD_SKUS = {
    "BO-971": "合成海浪",
    "BO-975": "复古光盘",
    "BO-980": "像素月亮",
    "BO-991": "霓虹贝壳",
    "BO-992": "棕榈海平线",
    "BO-1001": "像素太阳",
    "BO-1002": "霓虹旋涡",
    "BO-1003": "电子云海",
    "BO-1004": "电子海面",
}


def neon_line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: tuple[int, int, int, int], width: int) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")


def add_palm(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int, int]) -> None:
    trunk_w = max(3, int(8 * scale))
    draw.line((x, y, x + int(20 * scale), y - int(118 * scale)), fill=color, width=trunk_w)
    top = (x + int(20 * scale), y - int(118 * scale))
    for angle in (-150, -120, -92, -62, -34, 8, 42):
        length = int(86 * scale)
        rad = math.radians(angle)
        end = (top[0] + int(math.cos(rad) * length), top[1] + int(math.sin(rad) * length))
        draw.line((top, end), fill=color, width=max(3, int(7 * scale)))


def gradient_disc(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pix = img.load()
    r = size / 2
    for y in range(size):
        t = y / max(1, size - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(size):
            if (x - r) ** 2 + (y - r) ** 2 <= r**2:
                pix[x, y] = (*color, 255)
    return img


def draw_grid(draw: ImageDraw.ImageDraw, y0: int, y1: int, color: tuple[int, int, int, int]) -> None:
    for i in range(11):
        y = y0 + i * (y1 - y0) // 10
        draw.line((230, y, 794, y), fill=color, width=4)
    for x in range(250, 795, 58):
        draw.line((512, y0, x, y1), fill=color, width=3)


def render_replacement(sku: str, keyword: str, target: Path) -> None:
    img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    draw = ImageDraw.Draw(img)

    cyan = (0, 232, 230, 255)
    pink = (255, 29, 190, 255)
    purple = (95, 42, 220, 255)
    navy = (17, 19, 48, 255)
    cream = (248, 246, 238, 255)
    black = (18, 18, 26, 255)

    if sku in {"BO-971", "BO-992", "BO-1004"}:
        disc = gradient_disc(430, (255, 44, 191), (0, 220, 228))
        mask = disc.getchannel("A")
        img.alpha_composite(disc, (297, 220))
        draw_grid(draw, 550, 760, cyan)
        add_palm(draw, 355, 730, 1.12, black)
        add_palm(draw, 438, 748, 0.82, black)
        draw.arc((258, 178, 766, 686), 210, 510, fill=cream, width=18)
        draw.arc((280, 200, 744, 664), 210, 510, fill=pink, width=7)
        gdraw.bitmap((297, 220), mask, fill=(255, 0, 170, 80))
    elif sku in {"BO-975", "BO-991"}:
        for r, color in [(330, cream), (300, pink), (260, cyan), (220, purple)]:
            draw.ellipse((512 - r // 2, 512 - r // 2, 512 + r // 2, 512 + r // 2), outline=color, width=18)
        draw.pieslice((318, 318, 706, 706), 28, 152, fill=(0, 224, 226, 255))
        draw.pieslice((318, 318, 706, 706), 152, 278, fill=(255, 37, 190, 255))
        draw.pieslice((318, 318, 706, 706), 278, 388, fill=(38, 34, 96, 255))
        draw.ellipse((444, 444, 580, 580), fill=(255, 255, 255, 0), outline=cream, width=16)
        for y in range(382, 650, 24):
            draw.line((340, y, 684, y), fill=(20, 18, 42, 100), width=4)
    elif sku == "BO-980":
        disc = gradient_disc(430, (0, 236, 232), (255, 35, 190))
        img.alpha_composite(disc, (297, 238))
        draw.pieslice((350, 238, 782, 670), 82, 278, fill=(255, 255, 255, 245))
        draw.ellipse((438, 404, 590, 556), fill=pink)
        for y in range(260, 646, 28):
            draw.line((320, y, 704, y), fill=(26, 24, 62, 150), width=5)
        draw.arc((296, 234, 730, 668), 75, 285, fill=cream, width=12)
    elif sku == "BO-1001":
        for i, y in enumerate(range(288, 696, 26)):
            pad = abs(i - 8) * 17
            color = pink if i < 9 else (255, 190, 34, 255)
            draw.rectangle((300 + pad, y, 724 - pad, y + 16), fill=color)
        draw.ellipse((444, 440, 580, 576), fill=(255, 232, 54, 255))
        draw.rectangle((280, 274, 744, 710), outline=cream, width=12)
        draw.rectangle((292, 286, 732, 698), outline=cyan, width=5)
    elif sku == "BO-1002":
        center = (512, 512)
        for i in range(70):
            angle = i * 0.42
            r0 = 34 + i * 4
            r1 = r0 + 120
            c = cyan if i % 2 == 0 else pink
            p0 = (center[0] + int(math.cos(angle) * r0), center[1] + int(math.sin(angle) * r0))
            p1 = (center[0] + int(math.cos(angle + 0.55) * r1), center[1] + int(math.sin(angle + 0.55) * r1))
            neon_line(draw, [p0, p1], c, 5)
        draw.ellipse((360, 360, 664, 664), outline=cream, width=14)
        draw.ellipse((432, 432, 592, 592), fill=navy, outline=pink, width=8)
    elif sku == "BO-1003":
        draw.rounded_rectangle((250, 260, 774, 714), radius=38, fill=navy, outline=cream, width=12)
        for y in range(330, 690, 36):
            draw.line((284, y, 740, y), fill=(255, 35, 190, 145), width=4)
        draw.ellipse((360, 445, 664, 749), fill=(255, 35, 190, 255))
        draw.rectangle((260, 585, 764, 715), fill=(22, 20, 64, 255))
        for y in range(606, 704, 20):
            draw.line((300, y, 724, y), fill=cyan, width=4)
        for box in [(296, 430, 430, 500), (452, 382, 598, 462), (560, 488, 736, 568)]:
            draw.ellipse(box, fill=(0, 225, 226, 255))

    glow.alpha_composite(img)
    glow = glow.filter(ImageFilter.GaussianBlur(8))
    out = Image.alpha_composite(glow, img)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target)


def load_items(print_dir: Path, prompt_file: Path) -> list[base.PrintItem]:
    items: list[base.PrintItem] = []
    for line in prompt_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sku, keyword, prompt = line.split("\t", 2)
        items.append(base.PrintItem(sku=sku, keyword=keyword, prompt=prompt, path=print_dir / f"{sku}.png"))
    return items


def update_prompt_file(prompt_file: Path) -> None:
    lines = prompt_file.read_text(encoding="utf-8").splitlines()
    fixed: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        sku, keyword, prompt = line.split("\t", 2)
        if sku in BAD_SKUS:
            prompt = f"local vector vaporwave replacement, no shirt silhouette, no apparel, clean printable decal, {keyword}"
        fixed.append(f"{sku}\t{keyword}\t{prompt}")
    prompt_file.write_text("\n".join(fixed) + "\n", encoding="utf-8")


def append_progress_note() -> None:
    text = base.PROGRESS_FILE.read_text(encoding="utf-8")
    note = (
        f"\n- {date.today().isoformat()} 视觉复核后重做蒸汽波批次中的衣服形状异常印花："
        f"{'、'.join(BAD_SKUS)}。已重贴产品图、重写 xlsx 并重新同步投放目录。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, note + "\n" + marker, 1)
    else:
        text += note
    base.PROGRESS_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    vapor.configure_base()
    print_dir, mockup_dir, prompt_file, output_xlsx = vapor.batch_paths(START, COUNT, STAMP)
    for sku, keyword in BAD_SKUS.items():
        render_replacement(sku, keyword, print_dir / f"{sku}.png")
        print(f"replaced {sku} {keyword}", flush=True)
    update_prompt_file(prompt_file)
    items = load_items(print_dir, prompt_file)
    base.make_products(items, mockup_dir, 20260614 + 7)
    base.write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, COUNT)
    validation = base.validate_outputs(START, COUNT, print_dir, mockup_dir, output_xlsx)
    base.sync_putaway(mockup_dir, output_xlsx)
    putaway = base.validate_putaway(START, COUNT, output_xlsx)
    append_progress_note()
    print(f"validation={validation}")
    print(f"putaway={putaway}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
