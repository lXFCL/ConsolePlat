from __future__ import annotations

import argparse
import math
import random
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tshirt_print_tool import Placement, composite_one, list_images


MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"
BATCH_STYLE = "空灵线条印花"


@dataclass(frozen=True)
class Paths:
    print_dir: Path
    product_dir: Path
    prompt_file: Path
    output_xlsx: Path


MOTIFS = [
    "月轨静息",
    "呼吸波纹",
    "沉浸门形",
    "水纹静月",
    "极光层流",
    "星尘弧线",
    "雾环涟漪",
    "安静轨道",
    "柔光水面",
    "慢流曲线",
]

TITLE_SUFFIXES = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]


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
        output_xlsx=TEMPLATE_DIR / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def blank(size: int = 2600) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def line(draw: ImageDraw.ImageDraw, pts: list[tuple[float, float]], inner: tuple[int, int, int, int], outer: tuple[int, int, int, int], inner_w: int, outer_w: int, accent: tuple[int, int, int, int] | None = None, accent_w: int = 4) -> None:
    draw.line(pts, fill=outer, width=outer_w, joint="curve")
    draw.line(pts, fill=inner, width=inner_w, joint="curve")
    if accent:
        draw.line(pts, fill=accent, width=accent_w, joint="curve")


def arc_points(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, steps: int = 360) -> list[tuple[float, float]]:
    return [
        (cx + math.cos(math.radians(a0 + (a1 - a0) * i / steps)) * rx, cy + math.sin(math.radians(a0 + (a1 - a0) * i / steps)) * ry)
        for i in range(steps + 1)
    ]


def stroked_arc(draw: ImageDraw.ImageDraw, cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, inner: tuple[int, int, int, int], outer: tuple[int, int, int, int], inner_w: int = 9, outer_w: int = 20, accent: tuple[int, int, int, int] | None = None, accent_w: int = 4) -> None:
    line(draw, arc_points(cx, cy, rx, ry, a0, a1), inner, outer, inner_w, outer_w, accent, accent_w)


def stroked_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], inner: tuple[int, int, int, int], outer: tuple[int, int, int, int], inner_w: int = 9, outer_w: int = 20, accent: tuple[int, int, int, int] | None = None, accent_w: int = 4) -> None:
    draw.ellipse(box, outline=outer, width=outer_w)
    draw.ellipse(box, outline=inner, width=inner_w)
    if accent:
        draw.ellipse(box, outline=accent, width=accent_w)


def star(draw: ImageDraw.ImageDraw, x: float, y: float, r: int, color: tuple[int, int, int, int]) -> None:
    draw.line((x - r, y, x + r, y), fill=color, width=max(3, r // 4))
    draw.line((x, y - r, x, y + r), fill=color, width=max(3, r // 4))
    draw.ellipse((x - r * 0.18, y - r * 0.18, x + r * 0.18, y + r * 0.18), fill=color)


def add_crescent(img: Image.Image, box: tuple[int, int, int, int], cut_shift: int, dark: tuple[int, int, int, int], light: tuple[int, int, int, int]) -> None:
    moon = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(moon, "RGBA")
    draw.ellipse(box, fill=light)
    x0, y0, x1, y1 = box
    mask = Image.new("L", img.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse((x0 + cut_shift, y0 - 38, x1 + cut_shift, y1 - 38), fill=255)
    alpha = ImageChops.subtract(moon.getchannel("A"), mask)
    moon.putalpha(alpha)
    img.alpha_composite(moon)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.arc(box, 76, 284, fill=dark, width=14)
    draw.arc((x0 + cut_shift, y0 - 38, x1 + cut_shift, y1 - 38), 96, 264, fill=dark, width=10)


def palette(index: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
    darks = [(31, 37, 48, 245), (43, 48, 54, 245), (40, 54, 52, 245)]
    lights = [(242, 238, 220, 245), (246, 242, 230, 245), (236, 238, 226, 245)]
    accents = [(94, 190, 196, 225), (160, 142, 218, 220), (135, 184, 162, 215), (210, 195, 150, 220)]
    return darks[index % len(darks)], lights[index % len(lights)], accents[index % len(accents)], accents[(index + 1) % len(accents)]


def render_print(sku: str, index: int, output_dir: Path) -> Path:
    rng = random.Random(20260614 + index * 31)
    img = blank()
    draw = ImageDraw.Draw(img, "RGBA")
    dark, light, accent, accent2 = palette(index)
    motif = index % 5
    cx = 1300 + rng.randint(-45, 45)
    cy = 1220 + rng.randint(-40, 40)

    if motif == 0:
        for r in [520, 430, 340, 255]:
            stroked_ellipse(draw, (int(cx - r), int(cy - r), int(cx + r), int(cy + r)), dark, light, 9, 19, accent if r in (520, 340) else None, 4)
        for i in range(4):
            stroked_arc(draw, cx, cy - 145 + i * 90, 720 + i * 35, 170 + i * 10, 192, 348, dark, light, 8, 18, accent2, 3)
        add_crescent(img, (int(cx - 260), int(cy - 360), int(cx + 105), int(cy + 5)), 125 + rng.randint(-20, 20), dark, light)
        draw = ImageDraw.Draw(img, "RGBA")
        for deg in range(0, 360, 30):
            star(draw, cx + math.cos(math.radians(deg)) * 620, cy + math.sin(math.radians(deg)) * 270, 10, light if deg % 60 else accent)

    elif motif == 1:
        for i in range(10 + index % 4):
            y = 910 + i * 58
            pts = []
            for x in range(450, 2151, 12):
                env = math.sin(math.pi * (x - 450) / 1700)
                yy = y + math.sin(x / (78 + index % 9) + i * 0.52) * (24 + index % 8) * env
                pts.append((x, yy))
            line(draw, pts, dark, light, 8, 18, accent if i % 2 == 0 else None, 4)
        for i in range(6 + index % 3):
            stroked_arc(draw, cx, cy - 40, 380 + i * 58, 92 + i * 22, 180, 360, dark, light, 7, 16, accent2 if i % 3 == 0 else None, 3)
        draw.ellipse((cx - 52, cy - 52, cx + 52, cy + 52), fill=light)
        draw.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), outline=dark, width=9)

    elif motif == 2:
        for i in range(5):
            stroked_arc(draw, cx, cy - 120 + i * 88, 700 - i * 70, 300 - i * 32, 200, 340, dark, light, 9, 20, accent if i % 2 == 0 else None, 4)
            stroked_arc(draw, cx, cy - 30 + i * 88, 700 - i * 70, 300 - i * 32, 20, 160, dark, light, 7, 16, accent2 if i % 2 == 1 else None, 3)
        for i, width in enumerate([900, 720, 540, 360]):
            y = cy - 185 + i * 114
            draw.rounded_rectangle((cx - width // 2, y, cx + width // 2, y + 20), radius=10, fill=light)
            draw.rounded_rectangle((cx - width // 2 + 8, y + 5, cx + width // 2 - 8, y + 15), radius=5, fill=dark)
        for _ in range(34):
            x = int(rng.gauss(cx, 350))
            y = int(rng.gauss(cy, 250))
            if 480 < x < 2120 and 520 < y < 1820:
                star(draw, x, y, rng.choice([8, 10, 12]), rng.choice([light, accent, accent2]))

    elif motif == 3:
        for i in range(14 + index % 4):
            rx = 180 + i * 62
            ry = 38 + i * 15
            stroked_ellipse(draw, (int(cx - rx), int(cy + 105 - ry), int(cx + rx), int(cy + 105 + ry)), dark, light, 7, 16, accent if i % 3 == 0 else None, 3)
        for i in range(5):
            stroked_arc(draw, cx, cy - 315 + i * 74, 420 + i * 60, 100 + i * 12, 203, 337, dark, light, 8, 18, accent2 if i % 2 else None, 3)
        draw.ellipse((cx - 130, cy - 540, cx + 130, cy - 280), fill=light)
        draw.ellipse((cx - 92, cy - 502, cx + 92, cy - 318), outline=dark, width=10)
        draw.ellipse((cx - 62, cy - 472, cx + 62, cy - 348), outline=accent, width=6)

    else:
        ribbon_colors = [accent, accent2, light, (232, 224, 198, 230)]
        for band, col in enumerate(ribbon_colors):
            pts = []
            base_y = cy - 150 + band * 88
            phase = band * 1.3 + index * 0.08
            for x in range(440, 2161, 10):
                env = math.sin(math.pi * (x - 440) / 1720)
                y = base_y + math.sin(x / (110 + band * 8) + phase) * 86 * env + math.sin(x / 47 + phase) * 18
                pts.append((x, y))
            line(draw, pts, dark, light, 13, 29, col, 7)
        for i in range(6):
            stroked_arc(draw, cx, cy + 140 + i * 32, 585 + i * 55, 160 + i * 15, 188, 352, dark, light, 7, 16)
        for _ in range(28):
            star(draw, rng.randint(520, 2080), rng.randint(610, 1630), rng.choice([8, 10, 12]), rng.choice([light, accent, accent2]))

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{sku}.png"
    img.save(path)
    return path


def shirt_color(model_path: Path) -> str:
    if "白" in model_path.stem:
        return "白"
    if "黑" in model_path.stem:
        return "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return "白" if float(np.median(luma)) >= 150 else "黑"


def title_for(index: int, color: str) -> str:
    color_word = "白色" if color == "白" else "黑色"
    motif = MOTIFS[index % len(MOTIFS)]
    suffix = TITLE_SUFFIXES[index % len(TITLE_SUFFIXES)]
    return f"夏季{color_word}空灵线条{motif}印花T恤 {suffix}"


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 220, 300
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((200, 238), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 266), path.stem[:26], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def template_xlsx() -> Path:
    candidates = sorted(p for p in TEMPLATE_DIR.glob("*.xlsx") if not p.name.startswith("~$"))
    preferred = TEMPLATE_DIR / "test(9).xlsx"
    if preferred.exists():
        return preferred
    if not candidates:
        raise FileNotFoundError(f"No xlsx template found in {TEMPLATE_DIR}")
    return candidates[0]


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:E{len(rows)}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )


def rows_from_product_filenames(product_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows = []
    for path in list_images(product_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append(("YUHAOBO", "T恤", title, sku, color))
    rows.sort(key=lambda row: int(row[3].split("-")[1]))
    return rows


def write_xlsx(product_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows = rows_from_product_filenames(product_dir)
    if len(rows) != expected_count:
        raise RuntimeError(f"Expected {expected_count} product rows, got {len(rows)}")
    all_rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *rows]
    tmp = output_xlsx.with_suffix(".tmp.xlsx")
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_xlsx(), tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(all_rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp.unlink(missing_ok=True)


def write_prompt_file(paths: Paths, start: int, count: int) -> None:
    end = start + count - 1
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{BATCH_STYLE} BO-{start}-BO-{end}",
        "风格：空灵、放松、沉浸，清晰线条图形，不做大面积模糊光晕。",
        "黑白 T 通用规则：深色主线适配白 T，米白外描边适配黑 T，少量浅青/浅紫/柔金点缀。",
        "构图：胸前居中印花，主体集中，减少细碎噪点，避免过细线条。",
    ]
    paths.prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(paths: Paths, start: int, count: int) -> dict[str, object]:
    end = start + count - 1
    print_paths = sorted(paths.print_dir.glob("BO-*.png"))
    product_paths = [p for p in list_images(paths.product_dir) if not p.name.startswith("_")]
    print_skus = [int(p.stem.split("-")[1]) for p in print_paths]
    product_skus = []
    for p in product_paths:
        match = re.match(r"^BO-(\d+)_", p.name)
        if match:
            product_skus.append(int(match.group(1)))
    product_skus.sort()
    alpha_ok = all(Image.open(p).mode == "RGBA" and Image.open(p).getchannel("A").getbbox() is not None for p in print_paths)
    rows = rows_from_product_filenames(paths.product_dir)
    return {
        "print_count": len(print_paths),
        "product_count": len(product_paths),
        "print_range_ok": print_skus == list(range(start, end + 1)),
        "product_range_ok": product_skus == list(range(start, end + 1)),
        "alpha_ok": alpha_ok,
        "xlsx_exists": paths.output_xlsx.exists(),
        "xlsx_rows": len(rows) + 1,
        "xlsx_first": rows[0][3] if rows else "",
        "xlsx_last": rows[-1][3] if rows else "",
    }


def run(start: int, count: int, seed: int, batch_date: str | None = None) -> tuple[Paths, dict[str, object]]:
    paths = batch_paths(start, count, batch_date)
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    write_prompt_file(paths, start, count)

    print_paths: list[Path] = []
    for idx in range(count):
        sku = f"BO-{start + idx}"
        print_paths.append(render_print(sku, idx, paths.print_dir))

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
    product_paths: list[Path] = []
    shuffled_prints = print_paths[:]
    rng.shuffle(shuffled_prints)
    for idx, print_path in enumerate(shuffled_prints):
        sku = print_path.stem
        model_path = rng.choice(models)
        color = shirt_color(model_path)
        title = title_for(int(sku.split("-")[1]) - start, color)
        output_path = paths.product_dir / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        product_paths.append(output_path)
        print(f"{sku}: {model_path.name} -> {output_path.name}")

    make_overview(product_paths, paths.product_dir / "_overview.jpg")
    write_xlsx(paths.product_dir, paths.output_xlsx, count)
    return paths, validate(paths, start, count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO ethereal line-art T-shirt prints, product images, and xlsx.")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260614)
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
