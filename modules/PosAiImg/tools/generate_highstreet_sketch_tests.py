from __future__ import annotations

import json
import time
import urllib.request
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
OUTPUT_DIR = ROOT / "印花图_透明底" / "高街黑白灰写实素描_5张测试_v2_2026-06-13"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

BASE_POSITIVE = (
    "standalone printable t-shirt graphic, high street fashion print, "
    "monochrome black white gray realistic pencil sketch, graphite and charcoal drawing, "
    "detailed metal texture, engraved silver jewelry, gritty luxury streetwear mood, "
    "centered isolated artwork on seamless plain pure white background, crisp edge silhouette, "
    "screen print ready, high contrast, no color except black white gray, generous empty margin, "
    "the jewelry object is the only object in the image, no drawing tools, no paper texture, "
    "single print asset only, no mockup, no model, no shirt, no clothing, no watermark, no logo, "
    "no background scene, no floor line, no cast shadow, no vignette, no grey background"
)

NEGATIVE = (
    "person, model, face, body, hands, shirt mockup, t-shirt, tee shirt, clothing, mannequin, "
    "colorful, gold color, bronze color, warm color, cartoon, cute, anime, vector flat icon, "
    "low detail, blurry, low quality, messy background, gradient background, texture background, "
    "frame, border, typography, letters, words, watermark, signature, cropped, floor, table, "
    "horizon line, cast shadow, contact shadow, product photo lighting, photorealistic scene, "
    "pencil, pen, brush, ruler, sketchbook, paper sheet, notebook, hand drawn construction lines, "
    "random scratches outside the object, text printed on a pencil, extra props"
)

PROMPTS = [
    (
        "01_stacked_rings",
        "叠戴戒指",
        "a cluster of stacked silver rings, intertwined bands, one signet ring and thin chain loops passing through, realistic pencil sketch jewelry illustration",
    ),
    (
        "02_heavy_chain_clasp",
        "粗链扣环",
        "heavy curb chain with large clasp and circular metal connector, broken chain link detail, realistic graphite sketch, streetwear jewelry print",
    ),
    (
        "03_padlock_chain",
        "挂锁链条",
        "small metal padlock hanging from layered chain necklace, scratched steel surface, dark charcoal shadows, realistic monochrome sketch",
    ),
    (
        "04_key_pendant",
        "钥匙吊坠",
        "antique key pendant attached to thin chain and small ring hardware, worn metal scratches, realistic black and white pencil drawing",
    ),
    (
        "05_cross_chain_ring",
        "十字链戒",
        "metal cross pendant, chain segments and a single ring arranged as a compact chest print emblem, realistic charcoal pencil sketch",
    ),
]


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
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
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "highstreet_sketch_test", "images": ["8", 0]},
        },
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
    border = np.concatenate(
        [
            rgba[0, :, :],
            rgba[-1, :, :],
            rgba[:, 0, :],
            rgba[:, -1, :],
        ],
        axis=0,
    )
    opaque = border[border[:, 3] > 200]
    if opaque.size == 0:
        return None
    return np.median(opaque[:, :3].astype(np.float32), axis=0)


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
    Image.fromarray(arr, "RGBA").save(target)


def make_overview(paths: list[Path], target: Path) -> None:
    thumbs = []
    for path in paths:
        img = Image.open(path).convert("RGBA")
        canvas = Image.new("RGB", img.size, "white")
        canvas.paste(img, mask=img.getchannel("A"))
        canvas.thumbnail((320, 320), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (360, 360), "white")
        tile.paste(canvas, ((360 - canvas.width) // 2, (360 - canvas.height) // 2))
        thumbs.append(tile)

    overview = Image.new("RGB", (360 * len(thumbs), 360), "white")
    for index, thumb in enumerate(thumbs):
        overview.paste(thumb, (index * 360, 0))
    overview.save(target, quality=92)


def main() -> None:
    wait_server()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    prompt_records = []
    for index, (slug, title, prompt) in enumerate(PROMPTS, start=1):
        prompt_id = queue_prompt(make_workflow(prompt, seed=2026061300 + index * 113))
        print(f"Queued {index}/5 {title}: {prompt_id}")
        history = wait_prompt(prompt_id)
        outputs = history.get("outputs", {})
        saved = 0
        for node in outputs.values():
            for image in node.get("images", []):
                if image.get("type") != "output":
                    continue
                source = COMFY_DIR / "output" / image["filename"]
                target = OUTPUT_DIR / f"{slug}_{title}.png"
                remove_white_bg(source, target)
                exported.append(target)
                saved += 1
        if saved != 1:
            raise RuntimeError(f"Expected 1 image for {title}, got {saved}")
        prompt_records.append({"file": exported[-1].name, "title": title, "prompt": prompt})

    (OUTPUT_DIR / "prompts.json").write_text(
        json.dumps(prompt_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    make_overview(exported, OUTPUT_DIR / "_overview.jpg")
    print(f"Done. Exported {len(exported)} image(s) to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
