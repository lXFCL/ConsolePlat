from __future__ import annotations

import argparse
from collections import deque
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
PROMPTS_FILE = ROOT / "印花提示词.txt"
OUTPUT_DIR = ROOT / "印花图_透明底"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"


BASE_POSITIVE = (
    "standalone printable graphic decal, centered isolated artwork on plain white background, "
    "flat 2D clean vector illustration, simple black outline, high contrast, screen print ready, crisp edges, "
    "clearly visible on both light and dark fabric colors, high-contrast dual-tone artwork, "
    "use a dark main fill with light cream or white outline, or a light main fill with dark outline, "
    "limited color palette, floating sticker-like standalone artwork, generous empty margin, "
    "small chest print occupying less than 55 percent of the canvas, "
    "single print asset only, no mockup, no model, no shirt, no clothing, no watermark, "
    "no background scene, no floor line, no shadow"
)

NEGATIVE = (
    "photo, realistic person, model, shirt mockup, t-shirt, tee shirt, top, clothing, apparel, fabric, mannequin, watermark, "
    "signature, blurry, low quality, messy background, cropped, frame, border, text artifacts, "
    "floor, ground, table, horizon line, cast shadow, contact shadow, 3d render, glossy, glass, "
    "transparent body, complex gradient, huge full canvas character, low contrast print, "
    "dark-only artwork, pale-only artwork, invisible on black shirt, invisible on white shirt"
)


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


def wait_server(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            http_json("GET", f"{SERVER}/system_stats", timeout=5)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("ComfyUI server is not available at http://127.0.0.1:8188")


def is_server_ready() -> bool:
    try:
        http_json("GET", f"{SERVER}/system_stats", timeout=5)
        return True
    except Exception:
        return False


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
    try:
        wait_server(timeout_seconds)
    except Exception:
        process.terminate()
        stdout.close()
        stderr.close()
        raise
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
    positive = f"{prompt}, {BASE_POSITIVE}"
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
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
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
            "inputs": {"filename_prefix": "posai_print", "images": ["8", 0]},
        },
    }


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", f"{SERVER}/prompt", {"prompt": workflow})
    return result["prompt_id"]


def wait_prompt(prompt_id: str, timeout_seconds: int = 900) -> dict:
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


def remove_white_bg(source: Path, target: Path, threshold: int, color_distance: float) -> None:
    img = Image.open(source).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    white = (rgb[..., 0] >= threshold) & (rgb[..., 1] >= threshold) & (rgb[..., 2] >= threshold)
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    white &= spread < 24

    bg_color = estimate_border_color(arr)
    if bg_color is not None:
        distance = np.linalg.norm(rgb.astype(np.float32) - bg_color[None, None, :], axis=2)
        background_like = white | (distance <= color_distance)
        background = edge_connected(background_like)
    else:
        background = edge_connected(white)

    arr[..., 3] = np.where(background, 0, arr[..., 3])
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(target)


def repad_transparent_png(path: Path, padding_ratio: float = 0.16) -> None:
    img = Image.open(path).convert("RGBA")
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return

    cropped = img.crop(bbox)
    size = max(cropped.width, cropped.height)
    padding = max(24, int(size * padding_ratio))
    canvas_size = min(2048, size + padding * 2)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    canvas.paste(cropped, ((canvas_size - cropped.width) // 2, (canvas_size - cropped.height) // 2), cropped)
    canvas.resize(img.size, Image.Resampling.LANCZOS).save(path)


def copy_outputs(
    history_item: dict,
    output_dir: Path,
    stem: str,
    bg_threshold: int,
    bg_color_distance: float,
    keep_raw_comfy_output: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    outputs = history_item.get("outputs", {})
    for node in outputs.values():
        for image in node.get("images", []):
            if image.get("type") != "output":
                continue
            source = COMFY_DIR / "output" / image["filename"]
            target = output_dir / f"{stem}_{len(copied) + 1:02d}_transparent.png"
            remove_white_bg(source, target, bg_threshold, bg_color_distance)
            repad_transparent_png(target)
            if not keep_raw_comfy_output:
                source.unlink(missing_ok=True)
            copied.append(target)
    return copied


def read_prompts(path: Path) -> list[str]:
    if not path.exists():
        path.write_text(
            "vintage sun and desert road, retro western style\n"
            "streetwear tiger head emblem, bold red and cream colors\n"
            "minimal geometric mountain badge, teal yellow black palette\n",
            encoding="utf-8",
        )
    prompts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            prompts.append(line)
    return prompts


def safe_name(text: str, index: int) -> str:
    keep = []
    for char in text.lower():
        if char.isalnum():
            keep.append(char)
        elif char in {" ", "-", "_"}:
            keep.append("_")
    value = "".join(keep).strip("_")
    value = "_".join(part for part in value.split("_") if part)
    return f"print_{index:03d}_{value[:48] or 'design'}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate print designs through local ComfyUI.")
    parser.add_argument("--prompts", type=Path, default=PROMPTS_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=1, help="Images per prompt.")
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--keep-raw-comfy-output", action="store_true")
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=240)
    parser.add_argument("--keep-comfyui", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = None
    try:
        if args.auto_start_comfyui:
            started = start_comfyui(args.comfy_timeout)
        else:
            wait_server()

        prompts = read_prompts(args.prompts)
        if not prompts:
            raise RuntimeError(f"No prompts found in {args.prompts}")

        exported: list[Path] = []
        for prompt_index, prompt in enumerate(prompts, start=1):
            for variant in range(args.count):
                seed = args.seed + prompt_index * 1000 + variant
                workflow = make_workflow(prompt, seed, args.steps, args.width, args.height)
                prompt_id = queue_prompt(workflow)
                print(f"Queued {prompt_index}.{variant + 1}: {prompt}")
                history = wait_prompt(prompt_id)
                stem = safe_name(prompt, prompt_index) + f"_v{variant + 1}"
                copied = copy_outputs(
                    history,
                    args.output_dir,
                    stem,
                    args.bg_threshold,
                    args.bg_color_distance,
                    args.keep_raw_comfy_output,
                )
                exported.extend(copied)
                for path in copied:
                    print(f"Saved {path}")
        print(f"Done. Exported {len(exported)} image(s) to {args.output_dir}")
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    main()
