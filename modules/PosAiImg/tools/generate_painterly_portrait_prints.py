from __future__ import annotations

import argparse
from collections import deque
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

POSITIVE_SUFFIX = (
    "vertical rectangular oil painting print panel, portrait orientation, "
    "standalone art print for t-shirt, centered complete rectangle on a pure white background, "
    "visible painted canvas edges, rich impasto brush strokes, painterly texture, gallery poster composition, "
    "no text, no letters, no watermark, no signature, no people, no clothing, no t-shirt mockup, "
    "generous white margin around the rectangular artwork"
)

NEGATIVE = (
    "model, person, face, body, shirt, t-shirt, clothing, apparel, mannequin, product mockup, "
    "logo, text, letters, typography, watermark, signature, caption, frame mockup, wall, room, floor, "
    "cropped artwork, cut off edges, landscape orientation, square canvas, blurry, low quality, "
    "flat vector, sticker icon, cartoon outline, black line art, transparent checkerboard"
)

PROMPTS = [
    (
        "monet-inspired misty water lily pond at dawn, soft pastel blue green and lavender, "
        "impressionist light, floating lily pads and gentle reflections"
    ),
    (
        "van gogh-inspired night garden with swirling stars over cypress silhouettes, "
        "deep ultramarine sky, golden brushstroke stars, expressive post-impressionist movement"
    ),
    (
        "cezanne-inspired vertical still life with apples, ceramic jug and folded cloth, "
        "warm earthy palette, structured oil brushwork, quiet studio composition"
    ),
    (
        "klimt-inspired golden floral orchard, decorative oil painting, mosaic-like gold accents, "
        "emerald leaves and small blossoms, elegant vertical ornamental composition"
    ),
    (
        "hokusai-inspired great wave interpreted as thick oil paint, dramatic blue wave rising upward, "
        "cream foam, distant small mountain, vertical modern art print composition"
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
        [
            "conda",
            "run",
            "-n",
            "posai-comfy",
            "python",
            "main.py",
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
        ],
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
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "painterly_portrait_print", "images": ["8", 0]}},
    }


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", f"{SERVER}/prompt", {"prompt": workflow})
    return result["prompt_id"]


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


def prepare_print_panel(source: Path, target: Path, crop_bottom: int = 0, padding_ratio: float = 0.075) -> None:
    img = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    if crop_bottom > 0:
        img = img.crop((0, 0, img.width, max(1, img.height - crop_bottom)))

    pad_x = int(img.width * padding_ratio)
    pad_y = int(img.height * padding_ratio)
    canvas_w = img.width + pad_x * 2
    canvas_h = img.height + pad_y * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    canvas.paste(img, (pad_x, pad_y), img)
    canvas.resize((832, 1216), Image.Resampling.LANCZOS).save(target)


def make_overview(paths: list[Path], output_path: Path) -> None:
    thumbs: list[Image.Image] = []
    for path in paths:
        img = Image.open(path).convert("RGBA")
        checker = Image.new("RGBA", img.size, (245, 245, 245, 255))
        thumb = Image.alpha_composite(checker, img)
        thumb.thumbnail((260, 380), Image.Resampling.LANCZOS)
        thumbs.append(thumb.copy())

    pad = 24
    label_h = 28
    width = pad + len(thumbs) * 260 + (len(thumbs) - 1) * pad + pad
    height = 380 + label_h + pad * 2
    canvas = Image.new("RGB", (width, height), (248, 248, 246))
    draw = ImageDraw.Draw(canvas)
    x = pad
    for index, thumb in enumerate(thumbs, start=1):
        y = pad
        canvas.paste(thumb.convert("RGB"), (x + (260 - thumb.width) // 2, y))
        draw.text((x + 8, height - pad - label_h + 5), f"{index:02d}", fill=(30, 30, 30))
        x += 260 + pad
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=92)


def copy_outputs(history_item: dict, raw_dir: Path, transparent_dir: Path, prefix: str) -> list[Path]:
    exported: list[Path] = []
    raw_dir.mkdir(parents=True, exist_ok=True)
    transparent_dir.mkdir(parents=True, exist_ok=True)
    outputs = history_item.get("outputs", {})
    for node in outputs.values():
        for image in node.get("images", []):
            if image.get("type") != "output":
                continue
            source = COMFY_DIR / "output" / image["filename"]
            raw_target = raw_dir / f"{prefix}_raw.png"
            transparent_target = transparent_dir / f"{prefix}_transparent.png"
            ImageOps.exif_transpose(Image.open(source)).save(raw_target)
            remove_outer_white(source, transparent_target)
            crop_bottom = 72 if prefix.endswith("_01") else 0
            prepare_print_panel(transparent_target, transparent_target, crop_bottom=crop_bottom)
            source.unlink(missing_ok=True)
            exported.append(transparent_target)
    return exported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 5 painterly vertical print panels through local ComfyUI.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "印花图_透明底" / "仿油彩名画风格竖版印花_5款_2026-06-17")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "印花图" / "仿油彩名画风格竖版印花_5款_2026-06-17")
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=1216)
    parser.add_argument("--seed", type=int, default=2026061701)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=300)
    parser.add_argument("--prompt-timeout", type=int, default=900)
    parser.add_argument("--keep-comfyui", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = None
    exported: list[Path] = []
    try:
        if args.auto_start_comfyui:
            started = start_comfyui(args.comfy_timeout)
        else:
            wait_server(args.comfy_timeout)

        for index, prompt in enumerate(PROMPTS, start=1):
            workflow = make_workflow(prompt, args.seed + index * 1000, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"Queued {index}/5: {prompt}")
            history = wait_prompt(prompt_id, args.prompt_timeout)
            exported.extend(copy_outputs(history, args.raw_dir, args.output_dir, f"oil_master_style_{index:02d}"))

        make_overview(exported, args.output_dir / "_overview.jpg")
        print(f"Done. Exported {len(exported)} image(s) to {args.output_dir}")
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    main()
