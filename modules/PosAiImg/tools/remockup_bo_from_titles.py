from __future__ import annotations

import argparse
import random
import re
import zipfile
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "模特图-干净"
PRINT_DIR = ROOT / "印花图_透明底" / "简约艺术字文字印花_BO-306-BO-505_2026-06-09"
TITLE_DIR = ROOT / "批量贴图结果" / "BO中等标题200_新主图重贴_2026-06-10"
OUTPUT_DIR = ROOT / "批量贴图结果" / "BO中等标题200_按主图底色重贴_2026-06-10"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
OUTPUT_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "BO中等标题200_按主图底色重贴_2026-06-10.xlsx"


def sku_number(sku: str) -> int:
    return int(sku.split("-", 1)[1])


def load_titles(title_dir: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    for path in list_images(title_dir):
        match = pattern.match(path.name)
        if match:
            titles[match.group(1)] = match.group(2)
    return titles


def shirt_color_from_title(title: str) -> str:
    if "白色" in title:
        return "白"
    if "黑色" in title:
        return "黑"
    return ""


def color_from_model_name(model_path: Path) -> tuple[str, str]:
    name = model_path.stem
    if "白" in name:
        return "白", "白色"
    if "黑" in name:
        return "黑", "黑色"
    raise ValueError(f"Model image name does not contain color: {model_path.name}")


def retitle_for_model_color(title: str, color_word: str) -> str:
    title = re.sub(r"夏季(?:白色|黑色)", f"夏季{color_word}", title, count=1)
    return title


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 220, 290
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((200, 230), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:28], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml: list[str] = []
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


def write_xlsx(rows_without_header: list[tuple[str, str, str, str, str]], output_xlsx: Path) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")]
    rows.extend(rows_without_header)
    tmp_path = output_xlsx.with_suffix(".tmp.xlsx")
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE_XLSX, tmp_path)
    with zipfile.ZipFile(tmp_path, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp_path.unlink(missing_ok=True)


def run(seed: int) -> tuple[list[Path], Path]:
    models = list_images(MODEL_DIR)
    prints = [path for path in list_images(PRINT_DIR) if re.match(r"^BO-\d+\.png$", path.name, re.IGNORECASE)]
    titles = load_titles(TITLE_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    if len(prints) != 200:
        raise RuntimeError(f"Expected 200 prints, got {len(prints)}")
    if len(titles) != 200:
        raise RuntimeError(f"Expected 200 titles, got {len(titles)}")

    rng = random.Random(seed)
    rng.shuffle(prints)
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    rows: list[tuple[str, str, str, str, str]] = []
    for print_path in prints:
        sku = print_path.stem
        model_path = rng.choice(models)
        color, color_word = color_from_model_name(model_path)
        title = retitle_for_model_color(titles[sku], color_word)
        output_path = OUTPUT_DIR / f"{sku}_{title}.png"
        composite_one(model_path, print_path, output_path, placement)
        exported.append(output_path)
        rows.append(("YUHAOBO", "T恤", title, sku, color))
        print(f"{sku}: exported")

    exported.sort(key=lambda path: sku_number(path.stem.split("_", 1)[0]))
    rows.sort(key=lambda row: sku_number(row[3]))
    make_overview(exported, OUTPUT_DIR / "_overview.jpg")
    write_xlsx(rows, OUTPUT_XLSX)
    return exported, OUTPUT_XLSX


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-apply BO prints to current model images using existing medium titles.")
    parser.add_argument("--seed", type=int, default=20260610)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exported, xlsx = run(args.seed)
    print(f"Created {len(exported)} mockup(s): {OUTPUT_DIR}")
    print(f"Created xlsx: {xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
