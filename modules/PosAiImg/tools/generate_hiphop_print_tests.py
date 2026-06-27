from __future__ import annotations

import json
import time
import urllib.request
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
OUTPUT_DIR = ROOT / "印花图_透明底" / "嘻哈元素印花_5张测试_v8_2026-06-13"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

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
    "product preview, photo scene, readable text, letters, words, logo, brand name, label, badge, symbol, trademark, watermark, "
    "signature, messy background, gradient background, paper texture, floor, table, cast shadow, contact shadow, "
    "cute cartoon, anime character, low quality, blurry, cropped"
)

PROMPTS = [
    (
        "01_microphone_chain",
        "麦克风链条",
        "microphone chain soundwave badge, microphone centered inside circular chain frame, red radial sound bursts, black paint splatter, compact emblem, no person, no label, no letters, no logo",
    ),
    (
        "02_turntable_vinyl",
        "黑胶唱盘",
        "turntable headphones soundwave badge, vinyl turntable, headphones, equalizer bars, lightning shapes, spray splatter and chain arc arranged as a shield emblem, blank lower area, no text, no words, no letters",
    ),
    (
        "03_boombox",
        "复古音箱",
        "boombox crown graffiti badge, retro speaker front, small abstract crown, sound waves, paint splashes and chain arc, compact high contrast emblem",
    ),
    (
        "04_graffiti_crown",
        "涂鸦皇冠",
        "crown chain graffiti crest, crown inside a circular chain halo, spray paint drips, star accents, lightning marks and splatter, compact emblem, no readable letters",
    ),
    (
        "05_sneaker_charm",
        "球鞋吊坠",
        "headphones spray can chain badge, headphones, spray paint can, chain arc, lightning bolt, paint splatter and abstract starburst arranged as compact emblem, no shoe, no logo, no letters, no brand mark",
    ),
]


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
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hiphop_print_test", "images": ["8", 0]}},
    }


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
    repad(add_light_edge(Image.fromarray(arr, "RGBA"))).save(target)


def make_overview(paths: list[Path], target: Path) -> None:
    tile_w = 360
    tile_h = 360
    sheet = Image.new("RGB", (tile_w * len(paths), tile_h), "white")
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        canvas = Image.new("RGB", img.size, "white")
        canvas.paste(img, mask=img.getchannel("A"))
        canvas.thumbnail((320, 320), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(canvas, ((tile_w - canvas.width) // 2, (tile_h - canvas.height) // 2))
        sheet.paste(tile, (index * tile_w, 0))
    sheet.save(target, quality=92)


def main() -> int:
    http_json("GET", f"{SERVER}/system_stats", timeout=5)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    records = []
    for index, (slug, title, prompt) in enumerate(PROMPTS, start=1):
        prompt_id = http_json("POST", f"{SERVER}/prompt", {"prompt": make_workflow(prompt, 2026061350 + index * 117)}, timeout=30)["prompt_id"]
        print(f"Queued {index}/5 {title}: {prompt_id}", flush=True)
        history = wait_prompt(prompt_id)
        saved = 0
        for node in history.get("outputs", {}).values():
            for image in node.get("images", []):
                if image.get("type") != "output":
                    continue
                source = COMFY_DIR / "output" / image["filename"]
                target = OUTPUT_DIR / f"{slug}_{title}.png"
                remove_white_bg(source, target)
                exported.append(target)
                records.append({"file": target.name, "title": title, "prompt": prompt})
                saved += 1
        if saved != 1:
            raise RuntimeError(f"Expected 1 image for {title}, got {saved}")
    (OUTPUT_DIR / "prompts.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    make_overview(exported, OUTPUT_DIR / "_overview.jpg")
    print(f"Done. Exported {len(exported)} image(s) to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
