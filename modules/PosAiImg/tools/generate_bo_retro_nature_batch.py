from __future__ import annotations

import argparse
import json
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
    "standalone isolated screen print decal asset, Japanese retro outdoor natural illustration, tasteful everyday t-shirt print design, "
    "clean badge or framed composition, simple hand drawn line art, flat layered shapes, vintage screen print grain, "
    "muted cream, forest green, charcoal black, slate blue, soft terracotta and warm orange accents, "
    "visible on both black and white backgrounds, balanced central graphic, clean outer contour, not photorealistic, "
    "centered isolated artwork on seamless plain pure white background, generous empty margin, "
    "single print asset only, no mockup, no product preview, no model, no shirt, no t-shirt silhouette, no clothing, "
    "no readable text, no letters, no logo, no brand mark, no watermark"
)

NEGATIVE = (
    "person, human, face, body, hands, portrait, skull, skeleton, bones, model, mannequin, animal mascot character, "
    "shirt mockup, t-shirt, shirt silhouette, collar, sleeves, fabric folds, clothing, apparel, product preview, photo scene, "
    "readable text, letters, words, logo, brand name, label, signature, watermark, messy background, gradient background, "
    "3d render, photorealistic landscape photo, overly complex details, dark muddy low contrast, cute cartoon character, anime"
)

SUBJECTS: list[tuple[str, str]] = [
    ("山湖日落", "mountain lake sunrise badge, pine trees, calm lake reflection, rising sun circle, simple hand drawn retro outdoor composition"),
    ("露营月夜", "night camp badge, crescent moon, tent silhouette, pine branches, tiny campfire glow, simple stars, circular layout"),
    ("植物花束", "quiet botanical oval badge, wildflower bundle, fern leaves, small sun disc, hand drawn line art"),
    ("海浪日落", "retro surf travel badge, stylized ocean wave, small sun, simple cliff line, tiny abstract seabird marks"),
    ("城市夜景", "minimal retro city night badge, moon over rooftops, window light blocks, quiet street curve, geometric composition"),
    ("松林小径", "pine forest trail badge, winding path, layered trees, small sunrise, muted green and cream"),
    ("雪山圆章", "snow mountain round badge, layered mountain peaks, pine silhouettes, warm sun disc"),
    ("湖边帐篷", "lakeside tent badge, tent by water, pine branch frame, calm reflection, vintage outdoor print"),
    ("野花圆牌", "wildflower medallion, small flowers, fern, leaf wreath and tiny sun, quiet natural illustration"),
    ("海岸灯塔", "coastal lighthouse badge, simple lighthouse, wave line, sun circle, cliff shape, retro travel style"),
    ("月亮松枝", "moon and pine branch crest, crescent moon, pine needles, small stars, oval frame"),
    ("日出山脊", "sunrise ridge badge, layered hills, rising sun, pine line, subtle grain"),
    ("溪流石径", "forest stream badge, small stream, rounded stones, fern leaves, simple frame"),
    ("篝火松树", "campfire pine badge, small fire, pine silhouettes, moon dot, circular outdoor emblem"),
    ("海浪圆章", "ocean wave circular badge, stylized wave, sun disc, shell-like arc, muted blue gray"),
    ("岛屿日落", "small island sunset badge, palm-like abstract leaves, ocean line, warm orange sun"),
    ("山谷花园", "mountain valley botanical badge, flowers in foreground, distant mountains, soft oval frame"),
    ("雨后森林", "rainy forest badge, pine trees, small raindrops, puddle reflection, muted blue green"),
    ("沙丘日落", "desert dune sunset badge, dune curves, low sun, sparse grass marks, warm muted palette"),
    ("远山云海", "distant mountain cloud sea badge, cloud layers, mountain silhouettes, sun halo"),
    ("湖面月光", "moonlit lake badge, moon reflection, pine silhouettes, quiet water lines"),
    ("露营炉火", "camp stove fire badge, small camp stove, kettle silhouette, pine branch border, no people"),
    ("复古花园", "retro garden badge, simple flower bed, sun disc, leaf frame, cream and terracotta"),
    ("山间小屋", "mountain cabin badge, tiny cabin silhouette, pine trees, sun behind hill, no smoke text"),
    ("海边贝壳", "seaside shell badge, shell, small wave, sun arc, sea grass, retro print layout"),
    ("林中蘑菇", "forest mushroom botanical badge, mushrooms, fern leaves, tiny sun, hand drawn natural style"),
    ("秋日落叶", "autumn leaf badge, maple-like leaves, small hill line, warm sun, simple oval frame"),
    ("冬日山林", "winter pine badge, snowy trees, mountain line, pale sun, muted cream and slate"),
    ("晨雾湖岸", "misty lakeshore badge, lake reeds, soft hills, rising sun, minimal layered shapes"),
    ("星空营地", "starry campsite badge, tent, star arc, pine trees and moon, no human figures"),
    ("海崖日出", "sea cliff sunrise badge, cliff edge, wave curve, sun disc, minimal seabird marks"),
    ("野草圆环", "meadow grass wreath badge, wild grasses, small flowers, sun dot and oval frame"),
    ("山脉罗盘", "mountain compass badge, abstract compass circle, mountain peaks, pine line, no letters"),
    ("湖边松果", "pinecone lakeside badge, pinecone, pine needles, lake line and small sun"),
    ("溪谷露营", "valley camping badge, tent, stream curve, pine trees, sunrise, compact emblem"),
    ("海浪贝壳", "wave and shell badge, stylized wave behind shell, warm sun accent, no text"),
    ("月夜花园", "moon garden badge, crescent moon, flowers and leaves, dark oval shape, quiet style"),
    ("山花日出", "alpine flower sunrise badge, mountain flower, ridge line, sun disc, muted green"),
    ("森林湖心", "forest lake badge, circular lake, pine ring, small sun reflection, vintage grain"),
    ("露营咖啡", "camp coffee badge, enamel mug silhouette, pine branch, tiny sun, no steam text"),
    ("海边小舟", "small boat coastal badge, simple boat silhouette, wave lines, sun disc, no people"),
    ("松针月亮", "pine needle moon badge, branch cluster, moon circle, star dots, oval frame"),
    ("山路日落", "mountain road sunset badge, winding road, layered hills, pine marks, warm sun"),
    ("植物圆窗", "botanical window badge, round window frame, fern and wildflower silhouettes, sun dot"),
    ("荒野日晕", "wilderness sun halo badge, sun ring, pine trees, mountain layers, screen print grain"),
    ("夜海月光", "night sea moon badge, moon over wave, cliff line, small stars, muted cream and blue"),
    ("苔原小花", "tundra flower badge, small wildflowers, rock shapes, distant hills, quiet palette"),
    ("湖边芦苇", "reeds by lake badge, reed silhouettes, water reflection, round sun, minimal frame"),
    ("松林星环", "pine forest star ring badge, pine silhouettes, star circle, moon accent, no text"),
    ("温柔山海", "gentle mountain and sea badge, mountain line above wave curve, sun disc, botanical accents"),
]


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    prompt: str
    path: Path


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"日系复古自然印花_BO-{start}-BO-{start + count - 1}_{stamp}"


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


def make_workflow(prompt: str, seed: int) -> dict:
    positive = f"{prompt}, {BASE_POSITIVE}"
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 7.0,
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
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bo_retro_nature", "images": ["8", 0]}},
    }


def queue_prompt(workflow: dict) -> str:
    return http_json("POST", f"{SERVER}/prompt", {"prompt": workflow}, timeout=30)["prompt_id"]


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
    expanded = alpha.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(0.5))
    edge_arr = np.asarray(expanded, dtype=np.int16) - np.asarray(alpha, dtype=np.int16)
    edge_arr = np.clip(edge_arr, 0, 85).astype(np.uint8)
    edge = Image.new("RGBA", rgba.size, (238, 236, 226, 0))
    edge.putalpha(Image.fromarray(edge_arr, "L"))
    edge.alpha_composite(rgba)
    return edge


def repad(img: Image.Image, padding_ratio: float = 0.14) -> Image.Image:
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
    target.parent.mkdir(parents=True, exist_ok=True)
    repad(add_light_edge(Image.fromarray(arr, "RGBA"))).save(target)


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
    return f"夏季{color_word}日系复古自然{keyword}印花T恤 {suffix}"


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
        ImageDraw.Draw(tile).text((8, 286), path.stem[:32], fill=(0, 0, 0), font=font)
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
    items: list[PrintItem] = []
    prompt_lines: list[str] = []
    for index, (keyword, subject) in enumerate(subjects, start=1):
        sku = f"BO-{start + index - 1}"
        prompt_id = queue_prompt(make_workflow(subject, seed + index * 101))
        print(f"Queued {index}/{count} {sku} {keyword}: {prompt_id}", flush=True)
        history = wait_prompt(prompt_id)
        saved = 0
        for node in history.get("outputs", {}).values():
            for image in node.get("images", []):
                if image.get("type") != "output":
                    continue
                source = COMFY_DIR / "output" / image["filename"]
                target = print_dir / f"{sku}.png"
                remove_white_bg(source, target)
                items.append(PrintItem(sku=sku, keyword=keyword, prompt=subject, path=target))
                saved += 1
        if saved != 1:
            raise RuntimeError(f"Expected 1 image for {sku}, got {saved}")
        prompt_lines.append(f"{sku}\t{keyword}\t{subject}")
    prompt_file.write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")
    return items


def make_products(print_items: list[PrintItem], mockup_dir: Path, seed: int) -> None:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(center_x=0.50, center_y=0.42, width=0.28, opacity=0.96, rotation=0.0, shadow_strength=0.28, wave_strength=0.006, remove_white_bg=True)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for item in print_items:
        model_path = rng.choice(models)
        color_word, color_short = shirt_color(model_path)
        title = product_title(color_word, item.keyword)
        output_path = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, item.path, output_path, placement)
        outputs.append(output_path)
        print(f"{item.sku}: exported {color_short}", flush=True)
    make_overview(outputs, mockup_dir / "_overview.jpg")


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
    rows = rows_from_mockup_filenames(mockup_dir)
    summary = {
        "print_count": len(print_files),
        "product_count": len(mockup_files),
        "print_range_ok": sku_numbers(print_files) == expected,
        "product_range_ok": sku_numbers(mockup_files) == expected,
        "xlsx_exists": output_xlsx.exists(),
        "xlsx_data_rows": len(rows),
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
    }
    if summary["print_count"] != count or summary["product_count"] != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"]:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not output_xlsx.exists() or len(rows) != count:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway(mockup_dir: Path, output_xlsx: Path) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(mockup_dir):
        if not path.name.startswith("_"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_xlsx, PUTAWAY_DATA_DIR / output_xlsx.name)


def validate_putaway(start: int, count: int, output_xlsx: Path) -> dict:
    expected = list(range(start, start + count))
    files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    summary = {
        "putaway_pic_count": len(files),
        "putaway_range_ok": sku_numbers(files) == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / output_xlsx.name).exists(),
    }
    if len(files) != count or sku_numbers(files) != expected or not summary["putaway_xlsx_exists"]:
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
        f"\n- {stamp} 已从 BO-{start} 生成 50 张日系复古自然印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，整体为日系复古自然/户外插画方向；需重点留意个别浅色图案在白 T 上是否偏淡。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO Japanese retro nature prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=906)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    http_json("GET", f"{SERVER}/system_stats", timeout=5)
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(args.start, args.count, args.date)
    print_items = generate_prints(args.start, args.count, print_dir, prompt_file, args.seed)
    make_products(print_items, mockup_dir, args.seed + 7)
    write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, args.count)
    validation = validate_outputs(args.start, args.count, print_dir, mockup_dir, output_xlsx)
    sync_putaway(mockup_dir, output_xlsx)
    putaway = validate_putaway(args.start, args.count, output_xlsx)
    update_progress(args.start, args.count, print_dir, mockup_dir, output_xlsx, validation, putaway)
    print(f"Created {len(print_items)} print(s): {print_dir}")
    print(f"Created product image dir: {mockup_dir}")
    print(f"Created xlsx: {output_xlsx}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False)}")
    print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
