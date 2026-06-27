from __future__ import annotations

import json
import math
import re
import shutil
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
START = 1421
SOURCE_DIR = Path(r"C:\Users\Administrator\.codex\generated_images\019ed15a-d643-7661-bdc1-3d8315b23a8a")
SOURCE_GLOB = "*.png"
STAMP = date.today().isoformat()
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

KEYWORDS = [
    "尖刺银字", "重铬字形", "暗纹金属字", "锋利链字", "银灰爆裂字",
    "冷白镭射字", "暗银尖角字", "蓝紫金属字", "铬色破碎字", "流光钩刺字",
    "冰银弯折字", "黑银重影字", "橙光金属字", "紫红锐边字", "铁灰扭曲字",
    "浅金裂纹字", "青蓝电镀字", "深银荆棘字", "米白铬影字", "暗金尖刺字",
    "灰黑刀锋字", "冰蓝链条字", "紫银爆裂字", "红黑金属字", "高光铬刺字",
    "雾银镂空字", "电蓝锐角字", "暗紫重金属字", "银白火花字", "黑铬裂片字",
    "橙红冷钢字", "蓝灰层叠字", "紫蓝碎片字", "浅银齿轮字", "深灰电光字",
    "白铬尖刺字", "暗红金属字", "银蓝变形字", "黑银爆闪字", "冷灰棱角字",
    "亮银流线字", "彩铬扭结字", "暗色链刺字", "金属字形",
]
SELLING_POINTS = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    source: Path
    path: Path
    luma: float


def source_files() -> list[Path]:
    files = sorted(SOURCE_DIR.glob(SOURCE_GLOB), key=lambda p: (p.stat().st_mtime, p.name))
    if not files:
        raise FileNotFoundError(f"No generated images found in {SOURCE_DIR}")
    return files


def batch_name(count: int) -> str:
    return f"爆款金属字印花_BO-{START}-BO-{START + count - 1}_{STAMP}"


def paths(count: int) -> tuple[Path, Path, Path, Path]:
    name = batch_name(count)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_按色主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    connected = np.zeros_like(mask, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        if mask[0, x]:
            queue.append((0, x))
        if mask[h - 1, x]:
            queue.append((h - 1, x))
    for y in range(1, h - 1):
        if mask[y, 0]:
            queue.append((y, 0))
        if mask[y, w - 1]:
            queue.append((y, w - 1))
    while queue:
        y, x = queue.popleft()
        if connected[y, x] or not mask[y, x]:
            continue
        connected[y, x] = True
        if y > 0:
            queue.append((y - 1, x))
        if y + 1 < h:
            queue.append((y + 1, x))
        if x > 0:
            queue.append((y, x - 1))
        if x + 1 < w:
            queue.append((y, x + 1))
    return connected


def remove_green_background(source: Path, target: Path) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    score = g - np.maximum(r, b)
    green = (g > 135) & (score > 42) & (r < 170) & (b < 170)
    background = edge_connected(green) | ((g > 165) & (score > 58) & (r < 150) & (b < 150))
    feather = (g > 125) & (score > 26) & (r < 190) & (b < 190)
    arr[..., 3] = np.where(background, 0, arr[..., 3])
    arr[..., 3] = np.where(feather & ~background, np.minimum(arr[..., 3], np.clip((58 - score) * 5, 0, 255)), arr[..., 3])

    opaque = arr[..., 3] > 0
    spill = opaque & (g > np.maximum(r, b) + 10)
    neutral = np.maximum(r, b)
    arr[..., 1] = np.where(spill, (neutral * 0.78 + g * 0.10).clip(0, 255), arr[..., 1]).astype(np.uint8)

    alpha = Image.fromarray(arr[..., 3], "L")
    bbox = alpha.getbbox()
    result = Image.fromarray(arr, "RGBA")
    if bbox:
        pad = 36
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(result.width, bbox[2] + pad),
            min(result.height, bbox[3] + pad),
        )
        result = result.crop(crop_box)
    target.parent.mkdir(parents=True, exist_ok=True)
    result.save(target)


def alpha_luma(path: Path) -> float:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    arr = np.asarray(img, dtype=np.float32)
    alpha = arr[..., 3] > 12
    if not np.any(alpha):
        return 255.0
    rgb = arr[..., :3][alpha]
    luma = 0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]
    return float(np.median(luma))


def shirt_color(model_path: Path) -> tuple[str, str]:
    stem = model_path.stem
    if "白" in stem:
        return "白色", "白"
    if "黑" in stem:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def choose_model(print_luma: float, index: int) -> Path:
    models = list_images(MODEL_DIR)
    black = [p for p in models if "黑" in p.stem]
    white = [p for p in models if "白" in p.stem]
    if not black or not white:
        raise FileNotFoundError(f"Need black and white model images in {MODEL_DIR}")
    candidates = black if print_luma >= 145 else white
    return candidates[index % len(candidates)]


def product_title(color_word: str, keyword: str) -> str:
    suffix = SELLING_POINTS[sum(ord(c) for c in color_word + keyword) % len(SELLING_POINTS)]
    return f"夏季{color_word}高街金属字{keyword}印花T恤 {suffix}"


def make_overview(paths_to_images: list[Path], output: Path) -> None:
    cols, tile_w, tile_h = 8, 230, 310
    rows = max(1, math.ceil(len(paths_to_images) / cols))
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths_to_images):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((210, 248), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 6))
        ImageDraw.Draw(tile).text((6, 260), path.stem[:30], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_idx, values in enumerate(rows, 1):
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
        "</worksheet>"
    )


def rows_from_product_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append(("YUHAOBO", "T恤", title, sku, color))
    return sorted(rows, key=lambda row: int(row[3].split("-")[1]))


def write_xlsx(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *rows_from_product_filenames(mockup_dir)]
    if len(rows) != expected_count + 1:
        raise RuntimeError(f"Expected {expected_count + 1} xlsx rows including header, got {len(rows)}")
    templates = [p for p in TEMPLATE_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {TEMPLATE_DIR}")
    template = sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_xlsx.with_suffix(".tmp.xlsx")
    shutil.copy2(template, tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = build_sheet_xml(rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename)
            dst.writestr(info, data)
    tmp.unlink(missing_ok=True)


def prepare_prints(files: list[Path], print_dir: Path, prompt_file: Path) -> list[PrintItem]:
    print_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for idx, source in enumerate(files):
        sku = f"BO-{START + idx}"
        keyword = KEYWORDS[idx % len(KEYWORDS)]
        target = print_dir / f"{sku}.png"
        remove_green_background(source, target)
        items.append(PrintItem(sku=sku, keyword=keyword, source=source, path=target, luma=alpha_luma(target)))
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{batch_name(len(files))}",
        f"从 {SOURCE_DIR} 提取上一轮已生成图片 {len(files)} 张，不继续补生成。",
        "按生成时间排序编号；前 5 张为先前已处理源图，其余为本次找回图片。",
        "贴图主图按印花主体亮度选择：浅色印花贴黑 T，深色印花贴白 T。",
    ]
    lines.extend(f"{item.sku}\t{item.keyword}\t{item.source.name}\tluma={item.luma:.1f}" for item in items)
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return items


def make_products(items: list[PrintItem], mockup_dir: Path) -> list[Path]:
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
    outputs = []
    for idx, item in enumerate(items):
        model = choose_model(item.luma, idx)
        color_word, _ = shirt_color(model)
        title = product_title(color_word, item.keyword)
        output = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model, item.path, output, placement)
        outputs.append(output)
    make_overview(outputs, mockup_dir / "_overview.jpg")
    return outputs


def sku_numbers(paths_to_files: list[Path]) -> list[int]:
    values = []
    for path in paths_to_files:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs(count: int, print_dir: Path, mockup_dir: Path, xlsx_path: Path) -> dict:
    expected = list(range(START, START + count))
    print_files = sorted(p for p in list_images(print_dir) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    product_files = sorted(p for p in list_images(mockup_dir) if not p.name.startswith("_"))
    rows = rows_from_product_filenames(mockup_dir)
    transparency = []
    for path in print_files:
        extrema = Image.open(path).convert("RGBA").getchannel("A").getextrema()
        transparency.append(extrema[0] == 0 and extrema[1] == 255)
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_skus": sku_numbers(print_files),
        "product_skus": sku_numbers(product_files),
        "transparent_pngs_ok": all(transparency),
        "xlsx_exists": xlsx_path.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "overview_exists": (mockup_dir / "_overview.jpg").exists(),
    }
    if len(print_files) != count or len(product_files) != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if sku_numbers(print_files) != expected or sku_numbers(product_files) != expected:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not all(transparency):
        raise RuntimeError(f"Transparency validation failed: {summary}")
    if not xlsx_path.exists() or len(rows) != count:
        raise RuntimeError(f"XLSX validation failed: {summary}")
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


def validate_putaway(count: int, xlsx_path: Path) -> dict:
    expected = list(range(START, START + count))
    files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    skus = sku_numbers(files)
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": skus,
        "putaway_range_ok": skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / xlsx_path.name).exists(),
    }
    if len(files) != count or skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(count: int, print_dir: Path, mockup_dir: Path, xlsx_path: Path, validation: dict, putaway: dict) -> None:
    end = START + count - 1
    next_start = end + 1
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间[：:]\s*.*", f"更新时间：{STAMP}", text)
    text = re.sub(r"上次已分配到[：:]\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从[：:]\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {STAMP} 根据用户补充的 `C:\\Users\\Administrator\\.codex\\generated_images\\019ed15a-d643-7661-bdc1-3d8315b23a8a`，接续上一轮已生成图片，不再补生成；从 BO-{START} 整理 {count} 张爆款金属字印花，实际范围为 BO-{START} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号；主图按印花亮度选择黑/白 T。\n"
        f"- `{xlsx_path}` 当前校验为 {count + 1} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{START}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`；原计划 BO-1421 到 BO-1470 中实际找回并处理 {count} 张，未继续补生成 BO-{next_start} 到 BO-1470。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    files = source_files()
    print_dir, mockup_dir, prompt_file, xlsx_path = paths(len(files))
    items = prepare_prints(files, print_dir, prompt_file)
    products = make_products(items, mockup_dir)
    write_xlsx(mockup_dir, xlsx_path, len(files))
    validation = validate_outputs(len(files), print_dir, mockup_dir, xlsx_path)
    sync_putaway(mockup_dir, xlsx_path)
    putaway = validate_putaway(len(files), xlsx_path)
    update_progress(len(files), print_dir, mockup_dir, xlsx_path, validation, putaway)
    print(json.dumps({
        "batch": batch_name(len(files)),
        "source_count": len(files),
        "print_dir": str(print_dir),
        "mockup_dir": str(mockup_dir),
        "xlsx": str(xlsx_path),
        "prompt": str(prompt_file),
        "product_count": len(products),
        "validation": validation,
        "putaway": putaway,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
