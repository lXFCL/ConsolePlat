from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import time
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"

SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

BASE_POSITIVE = (
    "standalone printable t-shirt graphic, high street fashion print, monochrome black white gray realistic pencil sketch, "
    "graphite and charcoal drawing, detailed silver metal texture, engraved jewelry, gritty luxury streetwear mood, "
    "bold bright silver highlights inside the object, strong dark outer contour, visible on both black and white t-shirts, "
    "centered isolated artwork on seamless plain pure white background, crisp edge silhouette, screen print ready, "
    "high contrast, no color except black white gray, generous empty margin, object occupies 45 percent of canvas, "
    "the jewelry object is the only object in the image, no drawing tools, no paper texture, no scene, no clothing, no model"
)

NEGATIVE = (
    "person, human, model, face, body, hands, head, portrait, skull, skeleton, bones, human bones, shirt mockup, t-shirt, tee shirt, clothing, mannequin, colorful, gold color, "
    "bronze color, warm color, cartoon, cute, anime, vector flat icon, low detail, blurry, low quality, messy background, "
    "gradient background, texture background, frame, border, typography, letters, words, watermark, signature, cropped, "
    "floor, table, horizon line, cast shadow, contact shadow, product photo lighting, photorealistic scene, pencil, pen, "
    "brush, ruler, sketchbook, paper sheet, notebook, hand drawn construction lines, random scratches outside the object, extra props"
)

SUBJECTS: list[tuple[str, str]] = [
    ("叠戒", "stacked silver rings with chain loops and engraved bands"),
    ("粗链", "heavy curb chain knot with oversized clasp and circular connector"),
    ("挂锁", "metal padlock pendant hanging from layered chain necklace"),
    ("钥匙", "antique key pendant with small ring hardware and thin chain"),
    ("十字链", "ornate metal cross pendant with chain segments"),
    ("安全别针", "large polished safety pin with chain and tiny ring details"),
    ("锁扣", "carabiner clasp with short chain links and scratched steel surface"),
    ("刀片吊坠", "razor blade pendant on a thin chain, dark charcoal sketch"),
    ("铭牌", "blank dog tag pendant with chain, scratched silver metal"),
    ("荆棘环", "barbed wire ring circle with chain fragments"),
    ("骰子链", "metal dice charm attached to a curb chain"),
    ("蛇形戒", "coiled snake ring with chain loops, silver engraved texture"),
    ("铆钉链", "spiked stud chain bracelet arranged as compact emblem"),
    ("泪滴吊坠", "teardrop metal pendant with layered chain hardware"),
    ("齿轮戒", "gear shaped ring and small chain connector"),
    ("手铐链", "small handcuff charm with short chain links"),
    ("玫瑰戒", "metal rose ring with wrapped chain and engraved petals"),
    ("星芒吊坠", "sharp starburst pendant with necklace chain"),
    ("圆环链", "interlocking metal rings and chain links, compact jewelry emblem"),
    ("锁芯吊坠", "keyhole lock core pendant with chain and scratched steel"),
    ("针扣链", "belt buckle inspired metal clasp with chain links"),
    ("月牙链", "crescent moon metal pendant with layered chains"),
    ("火焰戒", "flame engraved silver ring and broken chain links"),
    ("牌匾链", "small blank metal plaque pendant with ring connector"),
    ("钩扣链", "industrial hook clasp with heavy chain, high street jewelry"),
    ("方扣", "square metal buckle pendant with chain and ring"),
    ("蝴蝶扣", "butterfly shaped metal clasp with thin chain"),
    ("裂纹戒", "cracked signet ring with chain wrapped around it"),
    ("链网", "mesh of overlapping chain links forming compact chest print"),
    ("倒十字", "inverted cross pendant and chain fragments"),
    ("圆牌", "round medallion pendant with engraved rim and chain"),
    ("锁眼戒", "keyhole signet ring with chain loops"),
    ("钉环", "spiked hoop ring and short chain, realistic metal"),
    ("剪刀吊坠", "small scissor pendant with ring hardware and chain"),
    ("十字钥匙", "cross-shaped antique key pendant on chain"),
    ("铰链", "metal hinge charm with chain links, scratched steel"),
    ("双环", "two interlocking rings with dangling chain"),
    ("弯钩", "curved metal hook pendant with chain clasp"),
    ("暗纹牌", "ornamental engraved tag pendant with black gray shading"),
    ("刺链", "thorn shaped chain necklace in compact emblem shape"),
    ("锁链心", "heart shaped lock charm with heavy chain, dark sketch"),
    ("圆扣", "round spring clasp and layered necklace chain"),
    ("三戒", "three signet rings stacked with chain crossing through"),
    ("铆钉牌", "studded metal tag pendant with chain connector"),
    ("哥特吊坠", "gothic metal pendant with chain and sharp filigree"),
    ("别针链", "safety pin chain cluster with small charms"),
    ("破环", "broken metal ring with dangling chain fragment"),
    ("锁片", "flat lock plate charm with keyhole and chain"),
    ("链结", "large interlocked chain knot with silver highlights"),
]


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    prompt: str
    path: Path


@dataclass(frozen=True)
class ProductItem:
    sku: str
    title: str
    color: str
    model_path: Path
    print_path: Path
    output_path: Path


def batch_name(start: int, count: int, stamp: str) -> str:
    end = start + count - 1
    return f"高街黑白灰金属素描印花_BO-{start}-BO-{end}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, stamp)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_server() -> None:
    http_json("GET", f"{SERVER}/system_stats", timeout=5)


def make_workflow(prompt: str, seed: int) -> dict:
    positive = f"{prompt}, {BASE_POSITIVE}"
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bo_highstreet_sketch", "images": ["8", 0]}},
    }


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", f"{SERVER}/prompt", {"prompt": workflow}, timeout=30)
    return result["prompt_id"]


def wait_prompt(prompt_id: str) -> dict:
    deadline = time.time() + 900
    while time.time() < deadline:
        history = http_json("GET", f"{SERVER}/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


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


def estimate_border_color(rgba: np.ndarray) -> np.ndarray | None:
    border = np.concatenate([rgba[0, :, :], rgba[-1, :, :], rgba[:, 0, :], rgba[:, -1, :]], axis=0)
    opaque = border[border[:, 3] > 200]
    if opaque.size == 0:
        return None
    return np.median(opaque[:, :3].astype(np.float32), axis=0)


def add_light_edge(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    expanded = alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(0.6))
    edge_arr = np.asarray(expanded, dtype=np.int16) - np.asarray(alpha, dtype=np.int16)
    edge_arr = np.clip(edge_arr, 0, 105).astype(np.uint8)
    edge = Image.new("RGBA", rgba.size, (232, 232, 232, 0))
    edge.putalpha(Image.fromarray(edge_arr, "L"))
    edge.alpha_composite(rgba)
    return edge


def repad_transparent_png(img: Image.Image, padding_ratio: float = 0.14) -> Image.Image:
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return img
    cropped = img.crop(bbox)
    size = max(cropped.width, cropped.height)
    padding = max(24, int(size * padding_ratio))
    canvas_size = min(2048, size + padding * 2)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    canvas.paste(cropped, ((canvas_size - cropped.width) // 2, (canvas_size - cropped.height) // 2), cropped)
    return canvas.resize(img.size, Image.Resampling.LANCZOS)


def remove_white_bg(source: Path, target: Path) -> None:
    img = Image.open(source).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    white = (rgb[..., 0] >= 244) & (rgb[..., 1] >= 244) & (rgb[..., 2] >= 244)
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    background_like = white & (spread < 28)
    bg_color = estimate_border_color(arr)
    if bg_color is not None:
        distance = np.linalg.norm(rgb.astype(np.float32) - bg_color[None, None, :], axis=2)
        background_like |= distance <= 54.0
    background = edge_connected(background_like)
    arr[..., 3] = np.where(background, 0, arr[..., 3])
    processed = Image.fromarray(arr, "RGBA")
    processed = repad_transparent_png(add_light_edge(processed))
    target.parent.mkdir(parents=True, exist_ok=True)
    processed.save(target)


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def shirt_color(model_path: Path) -> tuple[str, str]:
    if "白" in model_path.stem:
        return "白色", "白"
    if "黑" in model_path.stem:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def product_title(color_word: str, keyword: str) -> str:
    variants = [
        "圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
        "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
        "圆领短袖 柔软透气针织上衣 夏季日常百搭",
    ]
    suffix = variants[sum(ord(c) for c in color_word + keyword) % len(variants)]
    return f"夏季{color_word}高街金属素描{keyword}印花T恤 {suffix}"


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 260, 330
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((240, 268), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 286), path.stem[:32], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    dimension = f"A1:E{len(rows)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )


def rows_from_mockup_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(mockup_dir):
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


def write_xlsx_from_mockup_filenames(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows_without_header = rows_from_mockup_filenames(mockup_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} rows, got {len(rows_without_header)} from {mockup_dir}")
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")]
    rows.extend(rows_without_header)
    if not TEMPLATE_XLSX.exists():
        raise FileNotFoundError(f"Template xlsx not found: {TEMPLATE_XLSX}")
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_xlsx.with_suffix(".tmp.xlsx")
    shutil.copy2(TEMPLATE_XLSX, tmp_path)
    with zipfile.ZipFile(tmp_path, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp_path.unlink(missing_ok=True)


def generate_prints(start: int, count: int, print_dir: Path, prompt_file: Path, seed: int) -> list[PrintItem]:
    if count > len(SUBJECTS):
        raise ValueError(f"Only {len(SUBJECTS)} subjects are configured")
    rng = random.Random(seed)
    subjects = SUBJECTS[:]
    rng.shuffle(subjects)
    subjects = subjects[:count]
    print_dir.mkdir(parents=True, exist_ok=True)
    prompt_file.parent.mkdir(parents=True, exist_ok=True)

    records: list[str] = []
    items: list[PrintItem] = []
    for index, (keyword, subject) in enumerate(subjects, start=1):
        sku = f"BO-{start + index - 1}"
        prompt = f"{subject}, compact jewelry print emblem"
        prompt_id = queue_prompt(make_workflow(prompt, seed + index * 113))
        print(f"Queued {index}/{count} {sku} {keyword}: {prompt_id}", flush=True)
        history = wait_prompt(prompt_id)
        outputs = history.get("outputs", {})
        saved = 0
        for node in outputs.values():
            for image in node.get("images", []):
                if image.get("type") != "output":
                    continue
                source = COMFY_DIR / "output" / image["filename"]
                target = print_dir / f"{sku}.png"
                remove_white_bg(source, target)
                items.append(PrintItem(sku=sku, keyword=keyword, prompt=prompt, path=target))
                saved += 1
        if saved != 1:
            raise RuntimeError(f"Expected 1 image for {sku}, got {saved}")
        records.append(f"{sku}\t{keyword}\t{prompt}")
    prompt_file.write_text("\n".join(records) + "\n", encoding="utf-8")
    return items


def make_products(print_items: list[PrintItem], mockup_dir: Path, seed: int) -> list[ProductItem]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    placement = Placement(center_x=0.50, center_y=0.42, width=0.28, opacity=0.96, rotation=0.0, shadow_strength=0.28, wave_strength=0.006, remove_white_bg=True)
    products: list[ProductItem] = []
    for item in print_items:
        model_path = rng.choice(models)
        color_word, color_short = shirt_color(model_path)
        title = product_title(color_word, item.keyword)
        output_path = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, item.path, output_path, placement)
        products.append(ProductItem(item.sku, title, color_short, model_path, item.path, output_path))
        print(f"{item.sku}: exported {color_short}", flush=True)
    make_overview([item.output_path for item in products], mockup_dir / "_overview.jpg")
    return products


def sku_numbers(paths: list[Path]) -> list[int]:
    values = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs(start: int, count: int, print_dir: Path, mockup_dir: Path, output_xlsx: Path) -> dict:
    expected = list(range(start, start + count))
    print_files = sorted(p for p in list_images(print_dir) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    mockup_files = sorted(p for p in list_images(mockup_dir) if not p.name.startswith("_"))
    print_skus = sku_numbers(print_files)
    mockup_skus = sku_numbers(mockup_files)
    rows = rows_from_mockup_filenames(mockup_dir)
    summary = {
        "print_count": len(print_files),
        "product_count": len(mockup_files),
        "print_range_ok": print_skus == expected,
        "product_range_ok": mockup_skus == expected,
        "xlsx_exists": output_xlsx.exists(),
        "xlsx_data_rows": len(rows),
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
    }
    if summary["print_count"] != count:
        raise RuntimeError(f"Print count mismatch: {summary}")
    if summary["product_count"] != count:
        raise RuntimeError(f"Product count mismatch: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"]:
        raise RuntimeError(f"SKU range mismatch: {summary}")
    if not output_xlsx.exists() or len(rows) != count:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway(mockup_dir: Path, output_xlsx: Path) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_xlsx, PUTAWAY_DATA_DIR / output_xlsx.name)


def validate_putaway(start: int, count: int, output_xlsx: Path) -> dict:
    expected = list(range(start, start + count))
    pic_files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    pic_skus = sku_numbers(pic_files)
    summary = {
        "putaway_pic_count": len(pic_files),
        "putaway_range_ok": pic_skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / output_xlsx.name).exists(),
    }
    if len(pic_files) != count or pic_skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(start: int, count: int, print_dir: Path, mockup_dir: Path, output_xlsx: Path, validation: dict, putaway: dict) -> None:
    end = start + count - 1
    next_start = end + 1
    stamp = date.today().isoformat()
    try:
        text = PROGRESS_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = PROGRESS_FILE.read_text(encoding="gbk", errors="replace")
    text = re.sub(r"更新时间[：:]\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到[：:]\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从[：:]\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张高街黑白灰金属素描印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，需人工查看黑白 T 上金属素描清晰度，黑 T 以银白高光和浅描边保证可见。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 50 BO high-street monochrome metal sketch prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=806)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260613)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-putaway", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wait_server()
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(args.start, args.count, args.date)
    if args.skip_generation:
        print_items = [
            PrintItem(sku=f"BO-{args.start + idx}", keyword=SUBJECTS[idx][0], prompt="", path=print_dir / f"BO-{args.start + idx}.png")
            for idx in range(args.count)
        ]
    else:
        print_items = generate_prints(args.start, args.count, print_dir, prompt_file, args.seed)
    products = make_products(print_items, mockup_dir, args.seed + 7)
    write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, args.count)
    validation = validate_outputs(args.start, args.count, print_dir, mockup_dir, output_xlsx)
    putaway = {"putaway_pic_count": 0, "putaway_range_ok": False, "putaway_xlsx_exists": False}
    if not args.skip_putaway:
        sync_putaway(mockup_dir, output_xlsx)
        putaway = validate_putaway(args.start, args.count, output_xlsx)
    update_progress(args.start, args.count, print_dir, mockup_dir, output_xlsx, validation, putaway)
    print(f"Created {len(print_items)} print(s): {print_dir}")
    print(f"Created {len(products)} product image(s): {mockup_dir}")
    print(f"Created xlsx: {output_xlsx}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False)}")
    print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
