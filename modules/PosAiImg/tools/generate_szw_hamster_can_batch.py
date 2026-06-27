from __future__ import annotations

import argparse
import random
import re
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "AI印花贴图测试" / "hamster_can_drinks_gpt_image2_2026-06-15"
MODEL_DIR = ROOT / "模特图-干净"
FONT_PATH = Path("C:/Windows/Fonts/malgunbd.ttf")


ITEMS = [
    ("cola", "可乐", "01_cola_can.png"),
    ("blue_soda", "蓝色汽水", "02_blue_soda_can.png"),
    ("lime", "青柠汽水", "03_lime_can.png"),
    ("orange", "橙子汽水", "04_orange_can.png"),
    ("grape", "葡萄汽水", "05_grape_can.png"),
    ("lemon", "柠檬汽水", "06_lemon_can.png"),
    ("strawberry", "草莓汽水", "07_strawberry_can.png"),
    ("energy", "能量饮料", "08_energy_can.png"),
    ("peach", "蜜桃汽水", "09_peach_can.png"),
    ("mint", "薄荷汽水", "10_mint_can.png"),
]


def parse_sku(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Za-z]+)-(\d+)", value.strip())
    if not match:
        raise ValueError(f"Invalid SKU start: {value}")
    return match.group(1).upper(), int(match.group(2))


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    connected = np.zeros_like(mask, dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(w):
        if mask[0, x]:
            stack.append((x, 0))
        if mask[h - 1, x]:
            stack.append((x, h - 1))
    for y in range(h):
        if mask[y, 0]:
            stack.append((0, y))
        if mask[y, w - 1]:
            stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        if connected[y, x] or not mask[y, x]:
            continue
        connected[y, x] = True
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not connected[ny, nx]:
                stack.append((nx, ny))
    return connected


def remove_black_background(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    luma = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    near_black = (luma < 38) & (spread < 38)
    background = edge_connected(near_black)
    alpha = arr[..., 3].astype(np.float32)
    alpha[background] = 0
    alpha_img = Image.fromarray(alpha.astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.45))
    arr[..., 3] = np.asarray(alpha_img)
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getbbox()
    if bbox:
        pad = 18
        out = out.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(out.width, bbox[2] + pad),
                min(out.height, bbox[3] + pad),
            )
        )
    return out


def draw_jittered_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int]) -> None:
    x, y = xy
    for dx, dy in ((0, 0), (1, 0), (0, 1)):
        draw.text((x + dx, y + dy), text, font=font, fill=fill, stroke_width=3, stroke_fill=(15, 15, 15, 230))


def add_korean_text(print_img: Image.Image) -> Image.Image:
    print_img = print_img.convert("RGBA")
    target_h = 1120
    scale = target_h / max(1, print_img.height)
    resized = print_img.resize((max(1, int(print_img.width * scale)), target_h), Image.Resampling.LANCZOS)

    canvas_w = max(980, resized.width + 220)
    canvas_h = resized.height + 260
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    x = (canvas_w - resized.width) // 2
    y = 220
    canvas.alpha_composite(resized, (x, y))

    font_big = ImageFont.truetype(str(FONT_PATH), 86)
    font_small = ImageFont.truetype(str(FONT_PATH), 76)
    text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    draw_jittered_text(draw, (canvas_w // 2 - 300, 54), "Q.지치셨나요?", font_big, (255, 255, 255, 255))
    draw_jittered_text(draw, (canvas_w // 2 + 245, 410), "네.", font_small, (255, 255, 255, 255))
    text_layer = text_layer.filter(ImageFilter.GaussianBlur(0.15))
    canvas.alpha_composite(text_layer)
    return canvas


def detect_color(model_path: Path) -> tuple[str, str]:
    name = model_path.name
    if "白" in name:
        return "白色", "白"
    if "黑" in name:
        return "黑色", "黑"
    return "黑色", "黑"


def product_title(color_name: str, flavor: str) -> str:
    return f"夏季{color_name}可爱仓鼠{flavor}易拉罐印花T恤 圆领短袖 透气舒适针织上衣 日常休闲百搭"


def xml_row(row_idx: int, values: list[str]) -> str:
    cells = []
    for col_idx, value in enumerate(values, start=1):
        col = ""
        n = col_idx
        while n:
            n, r = divmod(n - 1, 26)
            col = chr(65 + r) + col
        cells.append(f'<c r="{col}{row_idx}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
    return f'<row r="{row_idx}">{"".join(cells)}</row>'


def write_simple_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = [xml_row(i, row) for i, row in enumerate(rows, start=1)]
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + "".join(sheet_rows)
        + '</sheetData></worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def make_overview(paths: list[Path], output_path: Path) -> None:
    tiles: list[Image.Image] = []
    for path in paths:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((220, 285), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (240, 320), "white")
        tile.paste(img, ((240 - img.width) // 2, 8))
        ImageDraw.Draw(tile).text((8, 292), path.stem[:30], fill=(0, 0, 0))
        tiles.append(tile)
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 240, rows * 320), (238, 238, 238))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * 240, (idx // cols) * 320))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SZW hamster can drink T-shirt mini batch.")
    parser.add_argument("--start-sku", default="SZW-2865")
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prefix, start_num = parse_sku(args.start_sku)
    batch_name = f"{prefix}-{start_num}-{prefix}-{start_num + len(ITEMS) - 1}_hamster_can_{args.date}"
    transparent_dir = ROOT / "印花图_透明底" / batch_name
    product_dir = ROOT / "批量贴图结果" / batch_name
    xlsx_path = ROOT / "衣物对应的xlsx" / "简约200" / f"仓鼠韩文易拉罐印花_{prefix}-{start_num}-{prefix}-{start_num + len(ITEMS) - 1}_{args.date}.xlsx"

    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No T-shirt model images: {MODEL_DIR}")
    rng = random.Random(args.seed)
    placement = Placement(center_x=0.50, center_y=0.43, width=0.30, opacity=0.94, shadow_strength=0.30, wave_strength=0.008, remove_white_bg=False)

    transparent_paths: list[Path] = []
    product_paths: list[Path] = []
    rows = [["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"]]

    transparent_dir.mkdir(parents=True, exist_ok=True)
    product_dir.mkdir(parents=True, exist_ok=True)

    for offset, (_key, flavor, filename) in enumerate(ITEMS):
        sku = f"{prefix}-{start_num + offset}"
        src = SOURCE_DIR / filename
        if not src.exists():
            raise FileNotFoundError(src)
        transparent = add_korean_text(remove_black_background(src))
        print_path = transparent_dir / f"{sku}.png"
        transparent.save(print_path)
        transparent_paths.append(print_path)

        model_path = rng.choice(models)
        color_name, color_short = detect_color(model_path)
        title = product_title(color_name, flavor)
        product_path = product_dir / f"{sku}_{title}.png"
        composite_one(model_path, print_path, product_path, placement)
        product_paths.append(product_path)
        rows.append(["YUHOOBO", "T恤", title, sku, color_short])
        print(f"{sku}: {filename} -> {product_path.name}")

    write_simple_xlsx(xlsx_path, rows)
    make_overview(transparent_paths, transparent_dir / "_overview_prints.jpg")
    make_overview(product_paths, product_dir / "_overview.jpg")

    print(f"Transparent dir: {transparent_dir}")
    print(f"Product dir: {product_dir}")
    print(f"XLSX: {xlsx_path}")
    print(f"Count: prints={len(transparent_paths)} products={len(product_paths)} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
