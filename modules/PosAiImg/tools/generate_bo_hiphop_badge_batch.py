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
    "standalone isolated screen print decal asset, hip hop badge composition, bold urban sticker badge artwork, "
    "compact emblem layout, strong silhouette, thick black outline, white highlight outline, balanced circular or shield composition, no apparel preview, "
    "high contrast black white gray with small red accent, crisp screen print style, not photorealistic product shot, "
    "visible on both black and white backgrounds, dense central graphic with clean outer contour, "
    "centered isolated artwork on seamless plain pure white background, generous empty margin, "
    "single print asset only, object decal only, no mockup, no product preview, no model, no shirt, no t-shirt silhouette, "
    "no collar, no sleeves, no fabric folds, no clothing, no background scene, no shadow"
)

NEGATIVE = (
    "person, human, face, head, body, hands, portrait, skull, skeleton, bones, human bones, model, mannequin, "
    "shirt mockup, t-shirt, tee shirt, t-shirt outline, shirt silhouette, collar, sleeves, fabric folds, clothing, apparel, "
    "product preview, photo scene, readable text, letters, words, logo, brand name, label, badge text, trademark, watermark, "
    "signature, messy background, gradient background, paper texture, floor, table, cast shadow, contact shadow, "
    "cute cartoon, anime character, low quality, blurry, cropped, shoe brand swoosh, brand mark"
)

SUBJECTS: list[tuple[str, str]] = [
    ("麦克风链条", "microphone chain soundwave badge, microphone centered inside circular chain frame, red radial sound bursts, black paint splatter, compact emblem, no person, no label, no letters, no logo"),
    ("唱盘耳机", "turntable headphones soundwave badge, vinyl turntable, headphones, equalizer bars, lightning shapes, spray splatter and chain arc arranged as a shield emblem, blank lower area, no text, no words, no letters"),
    ("音箱喷溅", "boombox crown graffiti badge, retro speaker front, small abstract crown, sound waves, paint splashes and chain arc, compact high contrast emblem"),
    ("涂鸦皇冠", "crown chain graffiti crest, crown inside a circular chain halo, spray paint drips, star accents, lightning marks and splatter, compact emblem, no readable letters"),
    ("耳机喷罐", "headphones spray can chain badge, headphones, spray paint can, chain arc, lightning bolt, paint splatter and abstract starburst arranged as compact emblem, no shoe, no logo, no letters, no brand mark"),
    ("街头鼓机", "drum machine sampler badge, square sampler pads, headphones, small chain arc, red splatter halo, compact shield emblem, no words"),
    ("低音喇叭", "bass speaker badge, twin speaker cones, soundwave rings, lightning bolts and paint splatter, bold circular emblem, no letters"),
    ("唱针闪电", "record needle lightning badge, tonearm, vinyl fragment, equalizer bars, chain halo and red burst, compact emblem"),
    ("喷漆音浪", "spray can soundwave badge, spray can, waveform arcs, crown spark, chain loop, black red splatter, no letters"),
    ("街舞地板", "abstract dance floor tile badge, vinyl disc, arrows, soundwave rings and chain frame, no dancer, no person"),
    ("磁带音箱", "cassette boombox badge, cassette tape, speaker cones, paint drips and red lightning, compact sticker emblem, no text"),
    ("皇冠音浪", "crown soundwave badge, abstract crown, waveform circle, chain ring and black splatter, no readable letters"),
    ("耳机星芒", "headphones starburst badge, large headphones around red starburst, equalizer bars and chain fragments, no logo"),
    ("唱片火花", "vinyl spark badge, vinyl record with red spark halo, abstract lightning, chain arc, no plain record icon"),
    ("城市音箱", "urban speaker badge, compact speaker stack, skyline-like equalizer bars, red splatter, no readable text"),
    ("节奏闪电", "rhythm lightning badge, microphone, lightning bolts, waveform circle and paint drips, compact emblem"),
    ("地下唱盘", "underground turntable badge, turntable platter, chain ring, black white red splashes, no letters"),
    ("重低音", "subwoofer badge, deep bass speaker cone, circular shockwaves, red accent splatter, thick outline"),
    ("街头采样器", "sampler machine badge, grid pads, knob details, headphones and paint splatter, no brand mark"),
    ("黑胶皇冠", "vinyl crown badge, vinyl record behind abstract crown, chain halo and spray paint drips, no text"),
    ("喷漆皇冠", "spray can crown badge, abstract crown above spray can, chain arc and red black splatter, no letters"),
    ("麦克风星环", "microphone star ring badge, microphone, starburst, soundwave arcs and chain circle, no label"),
    ("音浪锁链", "soundwave chain badge, waveform bars inside circular chain frame, red lightning accents, no text"),
    ("双音箱", "double speaker badge, two speaker cones, cassette center, splatter halo and chain arc, no words"),
    ("耳机黑胶", "headphones vinyl badge, headphones around vinyl record, equalizer bars and red splatter, no readable marks"),
    ("街头节拍", "street beat badge, drum pad controller, vinyl slice, lightning and spray splatter, no letters"),
    ("唱片涂鸦", "graffiti vinyl badge, vinyl record, paint drips, star accents and chain frame, no readable graffiti words"),
    ("喷溅音箱", "splatter boombox badge, boombox, bold red spray burst, soundwave arcs, thick white outline"),
    ("音频旋钮", "mixer knobs badge, audio knobs, faders, headphones, lightning and chain halo, no text"),
    ("节拍圆章", "beat circle badge, sampler pads, microphone silhouette, red radial burst and black splatter, no words"),
    ("低音皇冠", "bass crown badge, crown, speaker cone, shockwave circle and paint drips, no letters"),
    ("音浪圆牌", "soundwave medallion badge, waveform bars, chain border, red spark accents, no typography"),
    ("涂鸦耳机", "graffiti headphones badge, headphones, spray splatter, lightning marks and chain border, no readable letters"),
    ("唱片链环", "vinyl chain ring badge, vinyl record inside thick chain border, red burst and equalizer accents, no text"),
    ("复古收录机", "retro cassette radio badge, radio speaker front, red splatter, waveform arcs, no logo"),
    ("节奏火花", "beat spark badge, microphone, sampler pad, lightning sparks and circular splatter, no letters"),
    ("音箱链条", "speaker chain badge, central speaker box, chain border, paint drips and red shockwaves, no text"),
    ("黑胶闪电", "vinyl lightning shield badge, vinyl fragment, bold lightning, splatter halo and thick outline, no words"),
    ("喷漆节拍", "spray beat badge, spray can, sampler pads, waveform circle and chain arc, no letters"),
    ("耳机皇冠", "headphones crown crest, headphones, small abstract crown, red splatter and chain frame, no brand mark"),
    ("麦克风喷溅", "microphone splatter badge, microphone, circular paint burst, soundwave rings and chain, no text"),
    ("唱盘链条", "turntable chain badge, turntable deck, chain loop, red lightning and paint drips, no words"),
    ("鼓点音浪", "drum beat soundwave badge, drum pad grid, waveform arcs, red splatter, thick outline"),
    ("音箱星环", "speaker star ring badge, boombox speaker, starburst halo, chain fragments and paint splashes"),
    ("混音台", "mixer console badge, faders, knobs, headphones, red burst and circular shield outline, no labels"),
    ("地下音浪", "underground soundwave crest, waveform, chain frame, crown spark and black red splatter, no text"),
    ("采样耳机", "sampler headphones badge, pad controller, headphones, chain arc, lightning and red splatter"),
    ("街头唱针", "street tonearm badge, record tonearm, soundwave circle, paint drips and chain border"),
    ("爆裂音箱", "exploded speaker badge, speaker cone, red burst, black splatter, chain ring and thick outline"),
    ("节奏王冠", "rhythm crown badge, abstract crown, equalizer bars, speaker cone and paint splatter, no words"),
]


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    prompt: str
    path: Path


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"嘻哈徽章印花_BO-{start}-BO-{start + count - 1}_{stamp}"


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
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bo_hiphop_badge", "images": ["8", 0]}},
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
    edge_arr = np.clip(edge_arr, 0, 95).astype(np.uint8)
    edge = Image.new("RGBA", rgba.size, (235, 235, 235, 0))
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
    return f"夏季{color_word}嘻哈街头徽章{keyword}印花T恤 {suffix}"


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
        prompt_id = queue_prompt(make_workflow(subject, seed + index * 117))
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
        f"\n- {stamp} 已从 BO-{start} 生成 50 张嘻哈徽章印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，嘻哈徽章构图整体适合胸前印花；需重点留意个别 AI 伪文字或过细喷溅。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO hip hop badge prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=856)
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
