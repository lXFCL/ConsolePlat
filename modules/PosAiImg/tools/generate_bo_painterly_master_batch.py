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
MODEL_DIR = ROOT / "\u6a21\u7279\u56fe-\u5e72\u51c0"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

STORE_NAMES = {"BO": "YUHAOBO", "SZW": "YUHOOBO"}
STYLE_NAME = "\u4eff\u6cb9\u5f69\u540d\u753b\u98ce\u683c\u7ad6\u7248\u5370\u82b1"
SELLING_POINTS = [
    "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u5fae\u5f39\u9488\u7ec7\u4e0a\u8863 \u65e5\u5e38\u4f11\u95f2\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u8212\u9002\u9488\u7ec7\u4e0a\u8863 \u6237\u5916\u4f11\u95f2\u65e5\u5e38\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u8f7b\u8584\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u4f11\u95f2\u901a\u52e4\u65e5\u5e38\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u67d4\u8f6f\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u590f\u5b63\u65e5\u5e38\u767e\u642d",
]

POSITIVE_SUFFIX = (
    "vertical rectangular oil painting print panel, portrait orientation, "
    "standalone art print for t-shirt, centered complete rectangle on a pure white background, "
    "visible painted canvas edges, rich impasto brush strokes, painterly texture, gallery poster composition, "
    "elegant public-domain master painting inspired style, modern wearable art print, "
    "no text, no letters, no watermark, no signature, no people, no clothing, no t-shirt mockup, "
    "generous white margin around the rectangular artwork"
)
NEGATIVE = (
    "model, person, face, body, shirt, t-shirt, clothing, apparel, mannequin, product mockup, "
    "logo, text, letters, typography, watermark, signature, caption, frame mockup, wall, room, floor, "
    "cropped artwork, cut off edges, landscape orientation, square canvas, blurry, low quality, "
    "flat vector, sticker icon, cartoon outline, black line art, transparent checkerboard"
)

BASE_THEMES: list[tuple[str, str]] = [
    ("\u7761\u83b2\u6c60\u5858", "monet-inspired misty water lily pond at dawn, soft pastel blue green and lavender, impressionist light, floating lily pads and gentle reflections"),
    ("\u661f\u591c\u82b1\u56ed", "van gogh-inspired night garden with swirling stars over cypress silhouettes, deep ultramarine sky, golden brushstroke stars, expressive post-impressionist movement"),
    ("\u82f9\u679c\u9759\u7269", "cezanne-inspired vertical still life with apples, ceramic jug and folded cloth, warm earthy palette, structured oil brushwork, quiet studio composition"),
    ("\u91d1\u8272\u82b1\u679d", "klimt-inspired golden floral orchard, decorative oil painting, mosaic-like gold accents, emerald leaves and small blossoms, elegant vertical ornamental composition"),
    ("\u6d6e\u4e16\u5de8\u6d6a", "hokusai-inspired great wave interpreted as thick oil paint, dramatic blue wave rising upward, cream foam, distant small mountain, vertical modern art print composition"),
    ("\u9e22\u5c3e\u82b1\u56ed", "van gogh-inspired irises in a vertical garden, cobalt blue flowers, olive green leaves, heavy oil brush texture"),
    ("\u7761\u83b2\u5915\u7167", "monet-inspired water lilies under warm sunset haze, coral peach sky, soft reflected clouds, impressionist brush marks"),
    ("\u68ee\u6797\u5c0f\u5f84", "post-impressionist forest path with tall cypress trees, swirling blue green shadows, golden light on the trail"),
    ("\u4e61\u6751\u82b1\u7a97", "matisse-inspired colorful window with flowers and garden shapes, expressive oil paint, decorative vertical composition"),
    ("\u6708\u591c\u6d77\u6e7e", "whistler-inspired moonlit bay, quiet blue silver water, soft glowing moon, atmospheric oil painting panel"),
    ("\u5411\u65e5\u8475\u9759\u7269", "van gogh-inspired sunflowers in a ceramic vase, ochre yellow petals, teal wall, thick impasto oil paint"),
    ("\u6a44\u6984\u679c\u74f6", "cezanne-inspired still life with pears, olive jar and folded linen, geometric brushwork, earthy colors"),
    ("\u91d1\u8272\u6811\u6797", "klimt-inspired golden birch forest, vertical tree trunks, mosaic gold leaves, emerald and cream accents"),
    ("\u84dd\u8272\u6d77\u6d6a", "hokusai-inspired curling blue wave, cream foam, pale sky, oil painted reinterpretation with thick texture"),
    ("\u8292\u679c\u82b1\u5e03", "gauguin-inspired tropical fruit and flowers, warm orange mango, deep green leaves, bold oil painting blocks"),
    ("\u6d77\u5cb8\u65e5\u843d", "turner-inspired glowing coastal sunset, dramatic golden sky, soft waves, luminous oil brushwork"),
    ("\u7ea2\u8272\u82b1\u74f6", "matisse-inspired red flower vase on patterned table, bold decorative color, vertical oil painting"),
    ("\u96ea\u5730\u677e\u6797", "monet-inspired snowy pine grove, pale violet shadows, soft winter light, impressionist vertical panel"),
    ("\u7a3b\u7530\u98ce\u666f", "van gogh-inspired wheat field with crows removed, golden field, blue sky swirls, vertical crop, no birds"),
    ("\u84dd\u8272\u5c71\u5ce6", "cezanne-inspired blue mountain landscape, layered geometric hills, warm foreground, structured oil paint"),
    ("\u91d1\u8272\u5b54\u96c0\u7fbd", "klimt-inspired ornamental peacock feathers, gold mosaic pattern, teal eye shapes, vertical decorative art"),
    ("\u9ed1\u677e\u6d6a\u82b1", "hokusai-inspired wave and black pine silhouettes, navy blue water, cream foam, vertical oil painting"),
    ("\u8fde\u7ef5\u6c60\u5cb8", "monet-inspired pond bank with reeds and lilies, foggy morning light, green blue lavender palette"),
    ("\u8def\u706f\u661f\u7a7a", "van gogh-inspired small road under swirling starry sky, lamp glow, cypress silhouettes, no buildings text"),
    ("\u767d\u58f6\u68a8\u5b50", "cezanne-inspired white pitcher with pears and cloth, quiet beige wall, warm tabletop, textured oil paint"),
    ("\u91d1\u53f6\u5c0f\u9e1f", "klimt-inspired gold leaf branches with small abstract birds, ornamental flowers, no text, vertical panel"),
    ("\u5bcc\u58eb\u6d6a\u5c71", "hokusai-inspired wave with distant mountain, cream clouds, thick oil paint, balanced vertical composition"),
    ("\u82b1\u6865\u6c60\u6c34", "monet-inspired garden bridge over water lilies, soft green bridge, misty pond reflections, vertical panel"),
    ("\u84dd\u9ec4\u82b1\u675f", "van gogh-inspired blue and yellow wildflower bouquet, vigorous brush strokes, dark teal background"),
    ("\u6843\u5b50\u9759\u7269", "cezanne-inspired peaches on folded white cloth, ceramic bowl, warm ochre shadows, structured composition"),
    ("\u91d1\u8272\u661f\u6811", "klimt-inspired golden tree of life, curling branches, mosaic stars, emerald details, vertical ornament"),
    ("\u6d6a\u4e0e\u660e\u6708", "hokusai-inspired moonlit wave, indigo water, cream foam, pale moon, oil paint reinterpretation"),
    ("\u6de1\u7d2b\u82b1\u6c60", "monet-inspired violet water lily pond, soft pink sky, floating blossoms, hazy impressionist oil"),
    ("\u6df1\u84dd\u677e\u6797", "van gogh-inspired deep blue pine forest with golden moon, swirling brushwork, vertical landscape"),
    ("\u9752\u82f9\u679c\u684c", "cezanne-inspired green apples on rustic table, folded cloth, muted wall, strong oil texture"),
    ("\u91d1\u8272\u83dc\u7c7d\u82b1", "klimt-inspired golden meadow flowers, dense decorative blossoms, green stems, cream background"),
    ("\u6d77\u6d6a\u4e91\u5c71", "hokusai-inspired wave beneath cloud mountain, navy and cream palette, vertical print panel"),
    ("\u8377\u53f6\u6668\u96fe", "monet-inspired lotus leaves in morning mist, pale blue water, glowing sunrise reflection"),
    ("\u9ea6\u7530\u6708\u8272", "van gogh-inspired moonlit wheat field, blue shadows, golden strokes, no figures, vertical panel"),
    ("\u74f6\u82b1\u684c\u5e03", "cezanne-inspired vase, oranges and striped cloth, earthy ochre and green, still life panel"),
    ("\u91d1\u8272\u82b1\u74f6", "klimt-inspired gold flower vase, ornamental blossoms, mosaic pattern, teal and ivory accents"),
    ("\u5c71\u6d77\u6d6a\u5c16", "hokusai-inspired sharp wave peaks with distant hills, cream foam dots, thick oil paint texture"),
    ("\u7761\u83b2\u84dd\u6865", "monet-inspired blue garden bridge and lily pond, cool blue green haze, impressionist brush strokes"),
    ("\u6a59\u8272\u661f\u591c", "van gogh-inspired orange starry night over rolling hills, cypress line, dynamic oil brushwork"),
    ("\u9676\u7f50\u8461\u8404", "cezanne-inspired clay pot with grapes and apples, warm brown table, geometric composition"),
    ("\u91d1\u8272\u85e4\u8513", "klimt-inspired golden vines and white flowers, decorative vertical pattern, emerald leaves"),
    ("\u5927\u6d6a\u767d\u6ce1", "hokusai-inspired great wave closeup, white foam claws, deep blue sea, vertical oil panel"),
    ("\u6c60\u7554\u82b1\u5f71", "monet-inspired pond flowers and soft reflections, pale yellow sunlight, lavender green palette"),
    ("\u84dd\u8272\u9e22\u5c3e", "van gogh-inspired blue irises closeup, olive leaves, cream ground, impasto brushwork"),
    ("\u68a8\u5b50\u74f7\u7897", "cezanne-inspired pears in ceramic bowl, folded linen, muted ochre and sage, vertical still life"),
]


@dataclass(frozen=True)
class BatchPaths:
    print_dir: Path
    raw_dir: Path
    mockup_dir: Path
    mockup_test_dir: Path
    prompt_file: Path
    xlsx_path: Path


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    prompt: str
    print_path: Path


def batch_name(prefix: str, start: int, count: int, stamp: str) -> str:
    return f"{STYLE_NAME}_{prefix}-{start}-{prefix}-{start + count - 1}_{stamp}"


def batch_paths(prefix: str, start: int, count: int, stamp: str) -> BatchPaths:
    name = batch_name(prefix, start, count, stamp)
    year, month = stamp.split("-")[0], f"{int(stamp.split('-')[1])}\u6708"
    gallery_batch = Path("\u56fe\u5e93") / prefix / year / month / name
    mockup_batch = Path("\u6279\u91cf\u8d34\u56fe\u7ed3\u679c") / prefix / year / month / name
    return BatchPaths(
        print_dir=gallery_batch / "\u6700\u7ec8\u900f\u660e\u5e95",
        raw_dir=gallery_batch / "\u6d4b\u8bd5",
        mockup_dir=mockup_batch / "\u6700\u7ec8\u4ea7\u54c1\u56fe",
        mockup_test_dir=mockup_batch / "\u6d4b\u8bd5",
        prompt_file=Path("\u751f\u6210\u63d0\u793a\u8bcd") / f"{name}.txt",
        xlsx_path=Path("\u8863\u7269\u5bf9\u5e94\u7684xlsx") / prefix / f"{name}.xlsx",
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


def parse_product_filename(filename: str) -> tuple[str, str, str]:
    match = re.match(r"^((?:BO|SZW)-\d+)_(.+)\.png$", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unexpected product filename: {filename}")
    sku, title = match.groups()
    if "\u767d\u8272" in title:
        color = "\u767d"
    elif "\u9ed1\u8272" in title:
        color = "\u9ed1"
    else:
        color = ""
    return title, sku.upper(), color


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


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


def make_workflow(prompt: str, seed: int, steps: int, width: int, height: int) -> dict:
    positive = f"{prompt}, {POSITIVE_SUFFIX}"
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
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bo_painterly_master_print", "images": ["8", 0]}},
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
        & (spread < 28)
    )
    background = edge_connected(white)
    arr[..., 3] = np.where(background, 0, arr[..., 3])
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(target)


def prepare_print_panel(source: Path, target: Path, padding_ratio: float = 0.075) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    pad_x = int(img.width * padding_ratio)
    pad_y = int(img.height * padding_ratio)
    canvas = Image.new("RGBA", (img.width + pad_x * 2, img.height + pad_y * 2), (255, 255, 255, 0))
    canvas.paste(img, (pad_x, pad_y), img)
    canvas.resize((832, 1216), Image.Resampling.LANCZOS).save(target)


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
            prepare_print_panel(target, target)
            source.unlink(missing_ok=True)
            return target
    raise RuntimeError(f"No output image found for {sku}")


def shirt_color(model_path: Path) -> tuple[str, str]:
    stem = model_path.stem
    if "\u767d" in stem:
        return "\u767d\u8272", "\u767d"
    if "\u9ed1" in stem:
        return "\u9ed1\u8272", "\u9ed1"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("\u767d\u8272", "\u767d") if float(np.median(luma)) >= 150 else ("\u9ed1\u8272", "\u9ed1")


def product_title(color_word: str, keyword: str, index: int) -> str:
    suffix = SELLING_POINTS[index % len(SELLING_POINTS)]
    return f"\u590f\u5b63{color_word}\u4eff\u6cb9\u5f69\u540d\u753b{keyword}\u5370\u82b1T\u6064 {suffix}"


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
    started = None
    items: list[PrintItem] = []
    try:
        if args.auto_start_comfyui:
            started = start_comfyui(args.comfy_timeout)
        else:
            wait_server(args.comfy_timeout)
        for index in range(count):
            sku = f"{prefix}-{start + index}"
            keyword, prompt = BASE_THEMES[index % len(BASE_THEMES)]
            workflow = make_workflow(prompt, args.seed + index * 1000, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"Queued {index + 1}/{count}: {sku} {keyword}")
            history = wait_prompt(prompt_id, args.prompt_timeout)
            print_path = copy_output(history, paths.raw_dir, paths.print_dir, sku)
            items.append(PrintItem(sku=sku, keyword=keyword, prompt=prompt, print_path=print_path))
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)
    return items


def make_prompt_file(items: list[PrintItem], paths: BatchPaths) -> None:
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [paths.print_dir.name, "\u672c\u5730 ComfyUI \u751f\u6210\uff1b\u7ad6\u7248\u4eff\u6cb9\u5f69\u540d\u753b\u98ce\u683c\uff1b\u65e0\u6587\u5b57\u3001\u65e0\u6a21\u7279\u3001\u65e0\u8863\u670d\u3002"]
    lines.extend(f"{item.sku}\t{item.keyword}\t{item.prompt}" for item in items)
    paths.prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_products(items: list[PrintItem], paths: BatchPaths, args: argparse.Namespace) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(args.mockup_seed)
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
    return outputs


def product_rows(prefix: str, paths: BatchPaths) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for path in list_images(paths.mockup_dir):
        if path.name.startswith("_"):
            continue
        title, sku, color = parse_product_filename(path.name)
        if not sku.startswith(f"{prefix}-"):
            continue
        rows.append((STORE_NAMES[prefix], "T\u6064", title, sku, color))
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
    dirs = [ROOT / "\u8863\u7269\u5bf9\u5e94\u7684xlsx" / prefix, ROOT / "\u8863\u7269\u5bf9\u5e94\u7684xlsx" / "\u7b80\u7ea6200"]
    templates: list[Path] = []
    for directory in dirs:
        if directory.exists():
            templates.extend(p for p in directory.glob("*.xlsx") if not p.name.startswith("~$") and p != output_xlsx)
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {dirs}")
    return sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def write_xlsx(prefix: str, paths: BatchPaths, count: int) -> None:
    rows = [("\u5e97\u94fa\u540d\u79f0", "\u4ea7\u54c1\u5206\u7c7b", "\u4ea7\u54c1\u6807\u9898", "\u4ea7\u54c1\u5e8f\u5217\u53f7", "\u989c\u8272"), *product_rows(prefix, paths)]
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
        f"\n- {stamp} 按用户确认重新从 BO-{start} 生成 50 张仿油彩名画风格竖版印花；原因：上一轮 BO-1421 起的金属字批次实际临时改归 SZW，本批 BO 货号从 BO-{start} 重新分配到 BO-{end}。\n"
        f"- `{paths.print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在；印花图已按店铺前缀存放在 `印花图_透明底/BO/`。\n"
        f"- `{paths.mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；贴图参数为 center_x=0.50、center_y=0.42、width=0.28、opacity=0.96、shadow_strength=0.28、wave_strength=0.006。\n"
        f"- `{paths.xlsx_path}` 当前校验为 {count + 1} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}，店铺名称为 YUHAOBO。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，需人工确认竖版油彩画芯在黑白 T 上的印花大小和清晰度；个别 AI 油画可能仍需留意伪签名或过细边缘。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO/SZW painterly master-style vertical print batch.")
    parser.add_argument("--prefix", choices=["BO", "SZW"], default="BO")
    parser.add_argument("--start", type=int, default=1421)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--stamp", default=date.today().isoformat())
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=1216)
    parser.add_argument("--seed", type=int, default=2026061702)
    parser.add_argument("--mockup-seed", type=int, default=2026061703)
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
