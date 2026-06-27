from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    from tshirt_print_tool import Placement, composite_one, list_images
except ModuleNotFoundError:
    from tools.tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
MODEL_DIR = ROOT / "模特图-干净"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

STORE_NAMES = {"BO": "YUHAOBO"}
STYLE_NAME = "西海岸复古街头印花"
SELLING_POINTS = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]

POSITIVE_SUFFIX = (
    "standalone sticker decal artwork only, centered isolated graphic on pure white background, "
    "retro west coast California beach streetwear style, bold flat vector screen print, "
    "vintage poster color palette, teal orange cream navy red black accents, crisp edges, "
    "sticker-like silhouette, strong contrast for black and white t-shirts, no text, no letters, "
    "no typography, no brand logo, no watermark, no signature, no people, no clothing, no garment, "
    "no shirt, no tee, no product mockup, no printed shirt, no hanging shirt, no folded shirt, "
    "single flat graphic asset only, generous white margin"
)
NEGATIVE = (
    "person, human, face, body, model, mannequin, shirt, t-shirt, tee, top, clothing, apparel, mockup, "
    "printed on shirt, shirt photograph, hanging shirt, folded shirt, collar, sleeves, fabric, "
    "brand, logo, copyrighted character, celebrity, sports team, words, letters, typography, caption, "
    "watermark, signature, tiny text, messy background, room, wall, floor, photo, realistic catalog, "
    "cropped, cut off, blurry, low quality, pale low contrast, thin line only, transparent checkerboard"
)

STRICT_STICKER_SUFFIX = (
    "flat vector sticker icon only, no scene mockup, no apparel, no shirt, no photograph, "
    "no objects placed on table, no poster on wall, no product presentation, only the isolated emblem itself, "
    "simple centered badge silhouette, white background outside the emblem, clean printable graphic"
)


@dataclass(frozen=True)
class BatchPaths:
    print_dir: Path
    raw_dir: Path
    mockup_dir: Path
    mockup_test_dir: Path
    prompt_file: Path
    xlsx_path: Path


@dataclass(frozen=True)
class Theme:
    keyword: str
    prompt: str


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    prompt: str
    print_path: Path


WEST_COAST_THEMES: list[Theme] = [
    Theme("棕榈日落", "retro California sunset over ocean waves and tall palm trees, distressed beach poster badge"),
    Theme("卷浪太阳", "curling blue surf wave under low golden sun, small palm silhouette, clean vintage surf decal"),
    Theme("海岸公路", "coastal highway curving beside ocean cliffs, sunset sky, palm tree accents, travel badge composition"),
    Theme("低趴街车", "west coast lowrider street style, abstract classic car silhouette under palm sunset, chrome-like highlights"),
    Theme("滑板海浪", "skateboard silhouette with wave lines, palm leaves and sunburst, vintage skate beach graphic"),
    Theme("码头黄昏", "wooden pier silhouette, orange sunset, calm wave stripes, palm shadows, old California beach mood"),
    Theme("冲浪小巴", "retro surf van with board on roof, ocean wave and palm sun background, sticker-style badge"),
    Theme("海滩霓虹", "neon-style beach sign shape without letters, palm sunset, wave stripe base, red teal black palette"),
    Theme("落日山崖", "ocean cliff at sunset with winding road, small palm trees, bold travel poster shape"),
    Theme("湾区海浪", "stylized bay wave, bridge-like abstract arc without specific landmark, sunburst and palm accents"),
    Theme("沙滩车影", "classic beach cruiser car silhouette, surfboard, palm trees, warm cream outline"),
    Theme("冲浪板组", "three surfboards crossed with wave base and sun circle, retro resort streetwear emblem"),
    Theme("椰树海湾", "quiet cove with palm trees, moon-like sunset disk, teal water and orange sky"),
    Theme("日落电线", "west coast street scene detail, palm trees and power lines against sunset, badge without buildings text"),
    Theme("浪花徽章", "bold foam wave badge, cream spray shapes, navy teal sea, orange sun disk"),
    Theme("公路棕榈", "straight desert coastal road, rows of palms, low red sun, vintage road-trip decal"),
    Theme("复古海鸥", "abstract seabird silhouettes over wave and sun, palm leaves around, no realistic animal detail"),
    Theme("沙丘日光", "beach dunes with palm shadows, wave stripe horizon, sunburst, faded screen print texture"),
    Theme("街头海岸", "urban beach collage with palm, wave, sun, car stripe shapes, clean sticker silhouette"),
    Theme("长板冲浪", "longboard surfboard standing by wave and palm, sunset circle, vintage surf club mood without text"),
    Theme("红橙落日", "large red orange sunset disk with teal wave bands and black palm silhouettes"),
    Theme("蓝调海湾", "deep teal bay water, cream foam, orange sky, decorative palm frame"),
    Theme("轮滑海滩", "roller skate silhouette with wave stripe and sunburst, west coast retro streetwear decal"),
    Theme("海岸唱片", "vinyl record shape blended with sunset wave and palm, music beach mood, no text"),
    Theme("冲浪火焰", "surf wave with small flame-like sunset rays, bold red teal cream palette"),
    Theme("棕榈拱门", "palm trees forming arch around ocean sunset and wave base, centered sticker badge"),
    Theme("公路浪线", "yellow road lines turning into ocean wave stripes, palm sunset, retro road trip symbol"),
    Theme("沙滩排球", "simple volleyball circle icon with wave and palm sun background, vintage beach graphic"),
    Theme("摩托海岸", "abstract cruiser motorcycle silhouette near palm sunset, coastal streetwear mood, no brand"),
    Theme("夕阳帆影", "small sailboat silhouette on ocean sunset with palm leaves, bold poster-style decal"),
    Theme("海浪星芒", "wave crest with starburst sun rays and small sparkle dots, screen print badge"),
    Theme("车窗海景", "retro car window frame showing palm sunset and ocean wave, standalone decal"),
    Theme("西岸花浪", "hibiscus-like tropical flower with wave and sun, west coast beach badge, no realistic photo"),
    Theme("海边加油站", "abstract retro roadside gas pump silhouette without brand, palm sunset, coastal road badge"),
    Theme("夜色棕榈", "deep navy night palm trees, orange moon disk, teal wave stripe, vintage night beach decal"),
    Theme("冲浪尾鳍", "surfboard fin and ocean spray, palm sunset circle, compact sticker silhouette"),
    Theme("海岸相机", "retro camera icon framing wave and palm sunset, travel beach print, no brand"),
    Theme("加州热浪", "heat wave lines around sun disk, palm silhouettes, ocean stripe base, bold vector poster"),
    Theme("码头灯影", "pier lamp silhouette without text, sunset ocean and palm shadows, retro coastal badge"),
    Theme("滑板公路", "skateboard and road stripe crossing wave base, palm sunset, street beach graphic"),
    Theme("棕榈闪电", "palm tree with lightning sunburst and wave base, red teal cream black palette"),
    Theme("复古救生圈", "lifebuoy-like circle with wave and palm sunset, no letters, clean beach emblem"),
    Theme("海风贝壳", "stylized shell with wave bands and palm leaf accents, west coast souvenir decal"),
    Theme("日落天际", "low coastal skyline as abstract blocks, palm trees, wave and sunset, no specific landmark"),
    Theme("冲浪街牌", "blank street sign shape with palm sunset and waves, no text, vintage streetwear sticker"),
]


def batch_name(prefix: str, start: int, count: int, stamp: str) -> str:
    return f"{STYLE_NAME}_{prefix}-{start}-{prefix}-{start + count - 1}_{stamp}"


def batch_paths(prefix: str, start: int, count: int, stamp: str) -> BatchPaths:
    name = batch_name(prefix, start, count, stamp)
    year, month = stamp.split("-")[0], f"{int(stamp.split('-')[1])}月"
    gallery_batch = Path("图库") / prefix / year / month / name
    mockup_batch = Path("批量贴图结果") / prefix / year / month / name
    return BatchPaths(
        print_dir=gallery_batch / "最终透明底",
        raw_dir=gallery_batch / "测试",
        mockup_dir=mockup_batch / "最终产品图",
        mockup_test_dir=mockup_batch / "测试",
        prompt_file=Path("生成提示词") / f"{name}.txt",
        xlsx_path=Path("衣物对应的xlsx") / prefix / f"{name}.xlsx",
    )


def project_paths(paths: BatchPaths) -> BatchPaths:
    return BatchPaths(
        print_dir=ROOT / paths.print_dir,
        raw_dir=ROOT / paths.raw_dir,
        mockup_dir=ROOT / paths.mockup_dir,
        mockup_test_dir=ROOT / paths.mockup_test_dir,
        prompt_file=ROOT / paths.prompt_file,
        xlsx_path=ROOT / paths.xlsx_path,
    )


def selected_theme_range(batch_start: int, only_start: int | None, only_count: int | None) -> list[tuple[int, int, Theme]]:
    if only_start is None:
        offset = 0
        count = len(WEST_COAST_THEMES)
    else:
        offset = only_start - batch_start
        if offset < 0:
            raise ValueError("--only-start cannot be smaller than --start")
        count = only_count if only_count is not None else len(WEST_COAST_THEMES) - offset
    if count < 1:
        raise ValueError("--only-count must be positive")
    end = offset + count
    if end > len(WEST_COAST_THEMES):
        raise ValueError("Requested resume range exceeds available west coast themes")
    return [(index, batch_start + index, WEST_COAST_THEMES[index]) for index in range(offset, end)]


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def parse_product_filename(filename: str) -> tuple[str, str, str]:
    match = re.match(r"^(BO-\d+)_(.+)\.png$", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unexpected product filename: {filename}")
    sku, title = match.groups()
    if "白色" in title:
        color = "白"
    elif "黑色" in title:
        color = "黑"
    else:
        color = ""
    return title, sku.upper(), color


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_server_ready() -> bool:
    try:
        http_json("GET", f"{SERVER}/system_stats", timeout=5)
        return True
    except Exception:
        return False


def wait_server(timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_server_ready():
            return
        time.sleep(2)
    raise RuntimeError(f"ComfyUI server is not available at {SERVER}")


def start_comfyui(timeout_seconds: int) -> tuple[subprocess.Popen, object, object] | None:
    if is_server_ready():
        return None
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "comfyui_stdout.log").open("a", encoding="utf-8", errors="replace")
    stderr = (log_dir / "comfyui_stderr.log").open("a", encoding="utf-8", errors="replace")
    env = os.environ.copy()
    env["TQDM_DISABLE"] = "1"
    env["POSAI_DISABLE_TQDM"] = "1"
    process = subprocess.Popen(
        ["conda", "run", "-n", "posai-comfy", "python", "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd=COMFY_DIR,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    wait_server(timeout_seconds)
    return process, stdout, stderr


def stop_comfyui(started: tuple[subprocess.Popen, object, object] | None) -> None:
    if started is None:
        return
    process, stdout, stderr = started
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
    stdout.close()
    stderr.close()


def make_workflow(prompt: str, seed: int, steps: int, width: int, height: int, strict: bool = False) -> dict:
    positive = f"{prompt}, {POSITIVE_SUFFIX}"
    if strict:
        positive = f"{positive}, {STRICT_STICKER_SUFFIX}"
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
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
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bo_west_coast_print", "images": ["8", 0]}},
    }


def queue_prompt(workflow: dict) -> str:
    return http_json("POST", f"{SERVER}/prompt", {"prompt": workflow}, timeout=30)["prompt_id"]


def wait_prompt(prompt_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
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


def remove_outer_white(source: Path, target: Path, threshold: int = 242) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    white = (
        (rgb[..., 0] >= threshold)
        & (rgb[..., 1] >= threshold)
        & (rgb[..., 2] >= threshold)
        & (spread < 30)
    )
    background = edge_connected(white)
    arr[..., 3] = np.where(background, 0, arr[..., 3])
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(target)


def repad_square_png(path: Path, size: int = 1024, padding_ratio: float = 0.12) -> None:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return
    cropped = img.crop(bbox)
    base = max(cropped.width, cropped.height)
    padding = max(48, int(base * padding_ratio))
    canvas_size = base + padding * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    canvas.paste(cropped, ((canvas_size - cropped.width) // 2, (canvas_size - cropped.height) // 2), cropped)
    canvas.resize((size, size), Image.Resampling.LANCZOS).save(path)


def copy_output(history_item: dict, raw_dir: Path, print_dir: Path, sku: str) -> Path:
    outputs = history_item.get("outputs", {})
    for node in outputs.values():
        for image in node.get("images", []):
            if image.get("type") != "output":
                continue
            source = COMFY_DIR / "output" / image["filename"]
            raw_target = raw_dir / f"{sku}_raw.png"
            target = print_dir / f"{sku}.png"
            raw_dir.mkdir(parents=True, exist_ok=True)
            print_dir.mkdir(parents=True, exist_ok=True)
            ImageOps.exif_transpose(Image.open(source)).save(raw_target)
            remove_outer_white(source, target)
            repad_square_png(target)
            source.unlink(missing_ok=True)
            return target
    raise RuntimeError(f"No output image found for {sku}")


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


def product_title(color_word: str, keyword: str, index: int) -> str:
    suffix = SELLING_POINTS[index % len(SELLING_POINTS)]
    return f"夏季{color_word}西海岸{keyword}印花T恤 {suffix}"


def make_overview(paths_to_images: list[Path], output: Path, cols: int = 8) -> None:
    tile_w, tile_h = 230, 310
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


def generate_prints(prefix: str, start: int, count: int, paths: BatchPaths, args: argparse.Namespace) -> list[PrintItem]:
    if count > len(WEST_COAST_THEMES):
        raise ValueError(f"Only {len(WEST_COAST_THEMES)} west coast themes are available.")
    selected = selected_theme_range(start, args.only_start, args.only_count)
    started = None
    items: list[PrintItem] = []
    try:
        if args.auto_start_comfyui:
            started = start_comfyui(args.comfy_timeout)
        else:
            wait_server(args.comfy_timeout)
        for index, sku_number, theme in selected:
            sku = f"{prefix}-{sku_number}"
            workflow = make_workflow(
                theme.prompt,
                args.seed + index * 1000 + args.seed_offset,
                args.steps,
                args.width,
                args.height,
                args.strict_sticker,
            )
            prompt_id = queue_prompt(workflow)
            print(f"Queued {index + 1}/{count}: {sku} {theme.keyword}")
            history = wait_prompt(prompt_id, args.prompt_timeout)
            print_path = copy_output(history, paths.raw_dir, paths.print_dir, sku)
            items.append(PrintItem(sku=sku, keyword=theme.keyword, prompt=theme.prompt, print_path=print_path))
            print(f"Saved {print_path}")
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)
    return items


def make_prompt_file(items: list[PrintItem], paths: BatchPaths) -> None:
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [paths.print_dir.name, "本地 ComfyUI 生成；西海岸复古街头/冲浪/棕榈/落日方向；无文字、无品牌、无人物、无衣服。"]
    lines.extend(f"{item.sku}\t{item.keyword}\t{item.prompt}" for item in items)
    paths.prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_products(items: list[PrintItem], paths: BatchPaths, args: argparse.Namespace) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(args.mockup_seed)
    placement = Placement(
        center_x=0.50,
        center_y=0.43,
        width=0.32,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.26,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    paths.mockup_dir.mkdir(parents=True, exist_ok=True)
    paths.mockup_test_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, item in enumerate(items):
        model = rng.choice(models)
        color_word, _ = shirt_color(model)
        title = product_title(color_word, item.keyword, index)
        output = paths.mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model, item.print_path, output, placement)
        outputs.append(output)
    make_overview(outputs, paths.mockup_test_dir / "_overview.jpg")
    make_overview([item.print_path for item in items], paths.raw_dir / "_transparent_overview.jpg")
    return outputs


def product_rows(prefix: str, paths: BatchPaths) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for path in list_images(paths.mockup_dir):
        if path.name.startswith("_"):
            continue
        title, sku, color = parse_product_filename(path.name)
        if not sku.startswith(f"{prefix}-"):
            continue
        rows.append((STORE_NAMES[prefix], "T恤", title, sku, color))
    return sorted(rows, key=lambda row: int(row[3].split("-")[1]))


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


def find_template(prefix: str, output_xlsx: Path) -> Path:
    dirs = [ROOT / "衣物对应的xlsx" / prefix, ROOT / "衣物对应的xlsx" / "简约200"]
    templates: list[Path] = []
    for directory in dirs:
        if directory.exists():
            templates.extend(p for p in directory.glob("*.xlsx") if not p.name.startswith("~$") and p != output_xlsx)
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {dirs}")
    return sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def write_xlsx(prefix: str, paths: BatchPaths, count: int) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *product_rows(prefix, paths)]
    if len(rows) != count + 1:
        raise RuntimeError(f"Expected {count + 1} xlsx rows including header, got {len(rows)}")
    paths.xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.xlsx_path.with_suffix(".tmp.xlsx")
    shutil.copy2(find_template(prefix, paths.xlsx_path), tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(paths.xlsx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = build_sheet_xml(rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename)
            dst.writestr(info, data)
    tmp.unlink(missing_ok=True)


def sku_numbers(files: list[Path], prefix: str) -> list[int]:
    values = []
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)", re.IGNORECASE)
    for path in files:
        match = pattern.search(path.name)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs(prefix: str, start: int, count: int, paths: BatchPaths) -> dict:
    expected = list(range(start, start + count))
    print_files = sorted(p for p in list_images(paths.print_dir) if re.fullmatch(rf"{prefix}-\d+\.png", p.name, re.IGNORECASE))
    product_files = sorted(p for p in list_images(paths.mockup_dir) if p.name.startswith(f"{prefix}-"))
    rows = product_rows(prefix, paths)
    transparency = []
    for path in print_files:
        extrema = Image.open(path).convert("RGBA").getchannel("A").getextrema()
        transparency.append(extrema[0] == 0 and extrema[1] == 255)
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_skus": sku_numbers(print_files, prefix),
        "product_skus": sku_numbers(product_files, prefix),
        "transparent_pngs_ok": all(transparency),
        "xlsx_exists": paths.xlsx_path.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "store_names": sorted({row[0] for row in rows}),
        "overview_exists": (paths.mockup_test_dir / "_overview.jpg").exists(),
        "transparent_overview_exists": (paths.raw_dir / "_transparent_overview.jpg").exists(),
    }
    if len(print_files) != count or len(product_files) != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if summary["print_skus"] != expected or summary["product_skus"] != expected:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not summary["transparent_pngs_ok"]:
        raise RuntimeError(f"Transparency validation failed: {summary}")
    if not paths.xlsx_path.exists() or len(rows) != count or summary["store_names"] != [STORE_NAMES[prefix]]:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway(prefix: str, paths: BatchPaths) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(paths.mockup_dir):
        if path.name.startswith(f"{prefix}-"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.xlsx_path, PUTAWAY_DATA_DIR / paths.xlsx_path.name)


def validate_putaway(prefix: str, start: int, count: int, paths: BatchPaths) -> dict:
    expected = list(range(start, start + count))
    files = [p for p in list_images(PUTAWAY_PIC_DIR) if p.name.startswith(f"{prefix}-")]
    skus = sku_numbers(files, prefix)
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": skus,
        "putaway_range_ok": skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / paths.xlsx_path.name).exists(),
    }
    if len(files) != count or skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_bo_progress(start: int, count: int, paths: BatchPaths, validation: dict, putaway: dict, stamp: str) -> None:
    end = start + count - 1
    next_start = end + 1
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到：\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从：\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 {count} 张西海岸复古街头印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{paths.print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在；原生图和透明底总览存放在同批次 `测试` 目录。\n"
        f"- `{paths.mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；测试总览存放在同批次 `测试` 目录；贴图参数为 center_x=0.50、center_y=0.43、width=0.32、opacity=0.96、shadow_strength=0.26、wave_strength=0.006。\n"
        f"- `{paths.xlsx_path}` 当前校验为 {count + 1} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}，店铺名称为 YUHAOBO。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway.get('putaway_pic_count', 0)} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg` 和 `_transparent_overview.jpg`；西海岸方向包含棕榈、冲浪、落日、公路、滑板、低趴车等元素。需人工确认是否存在 AI 伪签名、细小文字残留或个别主体过复杂的问题。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO west coast formal print batch.")
    parser.add_argument("--prefix", choices=["BO"], default="BO")
    parser.add_argument("--start", type=int, default=1521)
    parser.add_argument("--count", type=int, default=45)
    parser.add_argument("--stamp", default=date.today().isoformat())
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=2026061745)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--mockup-seed", type=int, default=2026061746)
    parser.add_argument("--only-start", type=int, default=None, help="Only regenerate prints from this SKU number.")
    parser.add_argument("--only-count", type=int, default=None, help="Number of prints to regenerate with --only-start.")
    parser.add_argument("--strict-sticker", action="store_true", help="Add stricter prompt wording to avoid apparel mockups.")
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=300)
    parser.add_argument("--prompt-timeout", type=int, default=900)
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-progress", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = project_paths(batch_paths(args.prefix, args.start, args.count, args.stamp))
    items = generate_prints(args.prefix, args.start, args.count, paths, args)
    if args.only_start is not None:
        print(json.dumps({
            "mode": "partial-regenerate",
            "batch": batch_name(args.prefix, args.start, args.count, args.stamp),
            "generated_count": len(items),
            "print_dir": str(paths.print_dir),
        }, ensure_ascii=False, indent=2))
        return 0
    make_prompt_file(items, paths)
    products = make_products(items, paths, args)
    write_xlsx(args.prefix, paths, args.count)
    validation = validate_outputs(args.prefix, args.start, args.count, paths)
    putaway = {}
    if not args.skip_sync:
        sync_putaway(args.prefix, paths)
        putaway = validate_putaway(args.prefix, args.start, args.count, paths)
    if args.prefix == "BO" and not args.skip_progress:
        update_bo_progress(args.start, args.count, paths, validation, putaway, args.stamp)
    print(json.dumps({
        "batch": batch_name(args.prefix, args.start, args.count, args.stamp),
        "print_dir": str(paths.print_dir),
        "raw_dir": str(paths.raw_dir),
        "mockup_dir": str(paths.mockup_dir),
        "xlsx": str(paths.xlsx_path),
        "prompt": str(paths.prompt_file),
        "product_count": len(products),
        "validation": validation,
        "putaway": putaway,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
