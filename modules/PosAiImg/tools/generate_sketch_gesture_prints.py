from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_gesture_controlnet_ipadapter_batch as gesture_base  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "印花图_透明底"
COMFY = ROOT / "ComfyUI"


@dataclass(frozen=True)
class SketchSpec:
    key: str
    prompt: str
    control_kind: str


def specs() -> list[SketchSpec]:
    return [
        SketchSpec(
            "prayer_seal_sketch",
            "two front-facing hands pressed together in a compact prayer hand seal, cropped short wrists",
            "tiger",
        ),
        SketchSpec(
            "interlocked_seal_sketch",
            "two front-facing hands with fingers interlocked in a compact seal gesture, cropped short wrists",
            "snake",
        ),
        SketchSpec(
            "double_index_up_sketch",
            "two front-facing hands, both index fingers pointing upward, other fingers folded, cropped short wrists",
            "point_up",
        ),
        SketchSpec(
            "finger_frame_sketch",
            "two front-facing hands forming a compact rectangular finger frame, thumbs horizontal and index fingers vertical",
            "frame",
        ),
        SketchSpec(
            "ok_hand_sketch",
            "one front-facing hand making an OK gesture, thumb and index finger form a circle, other fingers raised",
            "ok",
        ),
    ]


STYLE = (
    "black white gray pencil sketch of hands, graphite drawing, charcoal shading, "
    "monochrome hand gesture illustration, fine pencil linework, cross hatching, soft gray shadows, "
    "tattoo flash style, screen print ready t-shirt graphic, centered isolated artwork on pure white background, "
    "clean negative space around the hands, high contrast grayscale, hand-drawn sketch texture, no photorealistic skin color, "
    "no color, no jewelry overload, no background block, no person, no face, no body, no clothing, no text, no logo"
)

NEGATIVE = (
    "photo, photorealistic skin, skin color, realistic person, portrait, face, mouth, eyes, nose, head, hair, torso, "
    "shirt, clothing, sleeve, full arms, background scene, gray rectangle, frame, border, circle, circular frame, halo, burst, radial lines, sunburst, watermark, text, logo, "
    "anime, cartoon, 3d render, color, red, blue, yellow, brown, beige, extra fingers, missing fingers, distorted hands, horror, creepy"
)


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_server(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            http_json("GET", "http://127.0.0.1:8188/system_stats", timeout=5)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("ComfyUI is not available at http://127.0.0.1:8188")


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", "http://127.0.0.1:8188/prompt", {"prompt": workflow}, timeout=60)
    return result["prompt_id"]


def wait_prompt(prompt_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        history = http_json("GET", f"http://127.0.0.1:8188/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


def edge_connected(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    connected = np.zeros_like(mask, dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        if mask[0, x]:
            q.append((0, x))
        if mask[h - 1, x]:
            q.append((h - 1, x))
    for y in range(1, h - 1):
        if mask[y, 0]:
            q.append((y, 0))
        if mask[y, w - 1]:
            q.append((y, w - 1))
    while q:
        y, x = q.popleft()
        if connected[y, x] or not mask[y, x]:
            continue
        connected[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w:
                q.append((ny, nx))
    return connected


def sketch_transparent(source: Path, output: Path) -> None:
    img = Image.open(source).convert("RGBA")
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    arr = np.asarray(img).astype(np.uint8)
    bg = arr > 238
    background = edge_connected(bg)
    alpha = np.where(background, 0, np.clip((255 - arr) * 1.8, 0, 255)).astype(np.uint8)
    ink = np.clip(arr * 0.70, 0, 255).astype(np.uint8)
    # Add a light ink layer for black garments while preserving gray pencil texture.
    light = np.where(alpha > 20, np.maximum(ink, 205), ink).astype(np.uint8)
    rgba = np.dstack([light, light, light, alpha])
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(output)


def copy_outputs(history: dict, output_dir: Path, stem: str) -> Path:
    for node in history.get("outputs", {}).values():
        for image in node.get("images", []):
            if image.get("type") != "output":
                continue
            source = COMFY / "output" / image["filename"]
            target = output_dir / f"{stem}.png"
            sketch_transparent(source, target)
            source.unlink(missing_ok=True)
            return target
    raise RuntimeError("No output image found in ComfyUI history")


def make_workflow(prompt: str, control_image: str, seed: int, width: int, height: int, steps: int, strength: float) -> dict:
    positive = f"{prompt}, {STYLE}"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": control_image}},
        "3": {"class_type": "ImageScale", "inputs": {"image": ["2", 0], "upscale_method": "nearest-exact", "width": width, "height": height, "crop": "disabled"}},
        "4": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "controlnet-openpose-sdxl-1.0.safetensors"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "7": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["5", 0],
                "negative": ["6", 0],
                "control_net": ["4", 0],
                "image": ["3", 0],
                "strength": strength,
                "start_percent": 0.0,
                "end_percent": 0.68,
            },
        },
        "8": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 7.2,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "positive": ["7", 0],
                "negative": ["7", 1],
                "latent_image": ["8", 0],
                "denoise": 1.0,
            },
        },
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "sketch_gesture", "images": ["10", 0]}},
    }


def make_overview(paths: list[Path], output: Path, bg: str) -> None:
    tile = 330
    label_h = 46
    sheet = Image.new("RGB", (len(paths) * tile, tile + label_h), bg)
    draw = ImageDraw.Draw(sheet)
    label_color = (0, 0, 0) if bg == "white" else (235, 235, 235)
    for i, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        canvas = Image.new("RGBA", img.size, bg)
        canvas.alpha_composite(img)
        prev = canvas.convert("RGB")
        prev.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        sheet.paste(prev, (i * tile + (tile - prev.width) // 2, (tile - prev.height) // 2))
        draw.text((i * tile + 12, tile + 12), path.stem[:36], fill=label_color)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061319)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--width", type=int, default=896)
    parser.add_argument("--height", type=int, default=896)
    parser.add_argument("--control-strength", type=float, default=0.56)
    parser.add_argument("--prompt-timeout", type=int, default=1500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wait_server()
    out_dir = OUT_ROOT / f"黑白灰素描手势印花_{args.date}"
    control_dir = out_dir / "control"
    outputs: list[Path] = []
    prompt_lines: list[str] = []
    for i, spec in enumerate(specs(), start=1):
        control_path = control_dir / f"{i:02d}_{spec.key}_control.png"
        gesture_base.make_control(spec.control_kind, control_path, args.width)
        control_name = gesture_base.copy_to_input(control_path, control_path.name)
        workflow = make_workflow(spec.prompt, control_name, args.seed + i * 101, args.width, args.height, args.steps, args.control_strength)
        prompt_id = queue_prompt(workflow)
        print(f"queued {spec.key}", flush=True)
        history = wait_prompt(prompt_id, args.prompt_timeout)
        if history.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"ComfyUI error for {spec.key}: {history.get('status')}")
        output = copy_outputs(history, out_dir, f"{i:02d}_{spec.key}")
        outputs.append(output)
        prompt_lines.append(f"{output.name}\n{spec.prompt}\n")
        print(f"saved {output}", flush=True)
    (out_dir / "_prompts.txt").write_text("\n".join(prompt_lines), encoding="utf-8")
    make_overview(outputs, out_dir / "_overview_on_white.jpg", "white")
    make_overview(outputs, out_dir / "_overview_on_black.jpg", "black")
    print(f"Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
