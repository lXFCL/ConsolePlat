from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
COMFY_DIR = ROOT / "ComfyUI"
SERVER = "http://127.0.0.1:8188"
CHECKPOINT = "RealVisXL_V5.0_fp16.safetensors"
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "5407554d2c7c4a0283df7ef98ed66a4a-goods.jpeg"


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_server(timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            http_json("GET", f"{SERVER}/system_stats", timeout=5)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("ComfyUI is not available at http://127.0.0.1:8188")


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", f"{SERVER}/prompt", {"prompt": workflow}, timeout=60)
    return result["prompt_id"]


def wait_prompt(prompt_id: str, timeout_seconds: int = 900) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        history = http_json("GET", f"{SERVER}/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}")


def copy_outputs(history: dict, out_dir: Path, prefix: str) -> list[Path]:
    copied: list[Path] = []
    for node in history.get("outputs", {}).values():
        for image in node.get("images", []):
            src = COMFY_DIR / "output" / image["filename"]
            dst = out_dir / f"{prefix}_{image['filename']}"
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def latest_comfy_output(prefix: str) -> Path | None:
    candidates = sorted(
        COMFY_DIR.joinpath("output").glob(f"{prefix}*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def keep_large_components(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    keep = np.zeros_like(mask, dtype=bool)

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(x, y)]
            visited[y, x] = True
            pts: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if nx == cx and ny == cy:
                            continue
                        if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((nx, ny))
            if len(pts) < 500:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            if 45 <= cx <= w - 35 and 10 <= cy <= h - 5:
                for px, py in pts:
                    keep[py, px] = True
    return keep


def fill_holes(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    outside = np.zeros_like(mask, dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((x, y))

    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h and not mask[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                queue.append((nx, ny))
    return ~outside


def extract_hamster(crop: Image.Image) -> tuple[Image.Image, Image.Image]:
    rgb = np.asarray(crop).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # The shirt background is near-black. This keeps the warm hamster, paws, cup, straw, and highlights.
    raw = (luma > 54) | ((r > 62) & (g > 42) & (r - b > 8)) | ((r > 80) & (g > 44) & (b < 72))
    keep = keep_large_components(raw)

    alpha = Image.fromarray((keep.astype(np.uint8) * 255), "L")
    filled = fill_holes(np.asarray(alpha) > 0)
    alpha = Image.fromarray((filled.astype(np.uint8) * 255), "L")
    # Contract a touch to avoid carrying the black shirt into the transparent edge.
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    hard = np.asarray(alpha) > 0
    soft_edge = alpha.filter(ImageFilter.GaussianBlur(1.1))
    soft_arr = np.asarray(soft_edge, dtype=np.uint8)
    # Keep the print itself opaque; only the antialiased boundary should be soft.
    alpha_arr = np.where(hard, 255, soft_arr).astype(np.uint8)
    alpha = Image.fromarray(alpha_arr, "L").filter(ImageFilter.GaussianBlur(0.25))

    rgba = crop.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba, alpha


def trim_alpha(rgba: Image.Image, pad: int = 18) -> Image.Image:
    bbox = rgba.getbbox()
    if not bbox:
        return rgba
    box = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(rgba.width, bbox[2] + pad),
        min(rgba.height, bbox[3] + pad),
    )
    return rgba.crop(box)


def make_drink_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    # Coordinates are relative to the crop around the hamster. This taller mask encourages a can
    # instead of a paper cup while leaving the paws mostly outside the strongest edit area.
    draw.rounded_rectangle((158, 282, 268, 482), radius=14, fill=255)
    draw.ellipse((154, 270, 272, 316), fill=255)
    draw.ellipse((156, 456, 270, 494), fill=250)
    draw.polygon([(194, 224), (213, 224), (219, 318), (199, 318)], fill=255)
    draw.rounded_rectangle((136, 322, 292, 430), radius=18, fill=210)
    mask = mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(4))
    return mask


def make_remove_cup_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    # Cover the original cup, lid, and straw while keeping the hamster face mostly untouched.
    draw.rounded_rectangle((148, 294, 282, 462), radius=25, fill=255)
    draw.ellipse((146, 276, 286, 342), fill=255)
    draw.polygon([(193, 224), (214, 224), (221, 333), (198, 333)], fill=255)
    draw.rounded_rectangle((132, 320, 300, 420), radius=24, fill=230)
    return mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4))


def composite_drink_edit(original: Image.Image, edited: Image.Image, drink_mask: Image.Image) -> Image.Image:
    if edited.size != original.size:
        edited = edited.resize(original.size, Image.Resampling.LANCZOS)
    # Limit model changes to the cup and straw. This preserves the hamster body/face from the source.
    blend_mask = drink_mask.filter(ImageFilter.GaussianBlur(2.0))
    return Image.composite(edited.convert("RGB"), original.convert("RGB"), blend_mask)


def make_hand_restore_mask(crop: Image.Image) -> Image.Image:
    arr = np.asarray(crop.convert("RGB")).astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Restore only pale paws/fur over the can. The original cup is also warm brown, so keep this
    # intentionally narrow to avoid bringing the old drink back into the final composite.
    fur_like = (luma > 138) & (r > 145) & (g > 105) & (b > 88) & ((r - b) < 86) & ((r - g) < 72)
    region = np.zeros(fur_like.shape, dtype=bool)
    region[326:420, 126:190] = True
    region[326:420, 246:306] = True
    mask = Image.fromarray((fur_like & region).astype(np.uint8) * 255, "L")
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.0))
    return mask


def remove_cup_with_fur_texture(crop: Image.Image) -> Image.Image:
    base = crop.convert("RGBA")
    texture = base.copy()

    # Use side-body fur only. Avoid center samples because they include the original cup.
    left_fur = crop.crop((58, 270, 150, 535)).resize((96, 260), Image.Resampling.BICUBIC)
    right_fur = crop.crop((300, 270, 392, 535)).resize((96, 260), Image.Resampling.BICUBIC)
    fill = Image.new("RGB", (192, 260), (220, 197, 155))
    fill.paste(left_fur, (0, 0))
    fill.paste(right_fur.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (96, 0))
    fill = fill.resize((210, 286), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2.0)).convert("RGBA")
    texture.alpha_composite(fill, (105, 238))

    cup_mask = Image.new("L", crop.size, 0)
    draw = ImageDraw.Draw(cup_mask)
    draw.rounded_rectangle((136, 268, 300, 486), radius=38, fill=255)
    draw.polygon([(190, 218), (218, 218), (226, 342), (196, 342)], fill=255)
    draw.rounded_rectangle((118, 310, 312, 436), radius=30, fill=245)
    cup_mask = cup_mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(8))
    merged = Image.composite(texture, base, cup_mask)

    # Restore only pale paws/fingers, not the warm/dark cup edges.
    hand_mask = make_hand_restore_mask(crop)
    merged = Image.composite(base, merged, hand_mask)

    # Add a very soft central fur shade to avoid a flat pasted patch.
    shade = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade, "RGBA")
    shade_draw.ellipse((150, 318, 284, 510), fill=(88, 70, 50, 28))
    shade = shade.filter(ImageFilter.GaussianBlur(18))
    merged = Image.alpha_composite(merged.convert("RGBA"), shade)
    return merged.convert("RGB")


def remove_cup_to_transparency(rgba: Image.Image, alpha: Image.Image) -> Image.Image:
    out = rgba.copy()
    cut = Image.new("L", rgba.size, 0)
    draw = ImageDraw.Draw(cut)
    draw.rounded_rectangle((158, 300, 276, 458), radius=24, fill=255)
    draw.ellipse((154, 282, 282, 342), fill=255)
    draw.polygon([(194, 224), (214, 224), (220, 334), (198, 334)], fill=255)
    draw.rounded_rectangle((138, 326, 296, 414), radius=22, fill=210)
    cut = cut.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0))

    alpha_arr = np.asarray(alpha, dtype=np.float32)
    cut_arr = np.asarray(cut, dtype=np.float32) / 255.0
    new_alpha = np.clip(alpha_arr * (1.0 - cut_arr), 0, 255).astype(np.uint8)

    # Keep only the pale visible paws on top of the transparent cutout.
    hand_keep = np.asarray(make_hand_restore_mask(rgba.convert("RGB")), dtype=np.float32) / 255.0
    original_alpha = np.asarray(alpha, dtype=np.float32)
    new_alpha = np.maximum(new_alpha, (original_alpha * hand_keep).astype(np.uint8))
    out.putalpha(Image.fromarray(new_alpha, "L"))
    return out


def make_clean_can_edit(crop: Image.Image) -> Image.Image:
    w, h = crop.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    can = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = can.load()

    cx = 211
    top_y = 296
    body_top = 311
    body_bottom = 452
    can_w = 118
    radius_x = can_w / 2
    radius_y = 18
    left = int(cx - radius_x)
    right = int(cx + radius_x)

    for y in range(body_top, body_bottom + 1):
        for x in range(left, right + 1):
            nx = (x - cx) / radius_x
            if abs(nx) > 1:
                continue
            # Slightly taper the bottom/top so the body reads as a small cylinder, not a block.
            if y < body_top + 8 or y > body_bottom - 10:
                limit = 0.92
                if abs(nx) > limit:
                    continue
            edge = abs(nx)
            shade = 1.0 - 0.42 * edge
            highlight = np.exp(-((nx + 0.36) / 0.18) ** 2) * 0.44
            right_glow = np.exp(-((nx - 0.56) / 0.16) ** 2) * 0.24
            red = int(np.clip(158 * shade + 70 * highlight + 50 * right_glow, 80, 235))
            green = int(np.clip(20 * shade + 26 * highlight + 10 * right_glow, 8, 58))
            blue = int(np.clip(22 * shade + 22 * highlight + 18 * right_glow, 10, 68))
            alpha = 255
            if y < body_top + 10:
                alpha = int(248 * (y - body_top + 1) / 11)
            px[x, y] = (red, green, blue, alpha)

    draw = ImageDraw.Draw(can, "RGBA")
    draw.ellipse((left, top_y, right, top_y + 32), fill=(211, 214, 212, 255), outline=(118, 118, 116, 255), width=2)
    draw.ellipse((left + 7, top_y + 6, right - 7, top_y + 26), fill=(235, 236, 232, 245))
    draw.ellipse((left + 30, top_y + 8, left + 61, top_y + 23), fill=(126, 126, 122, 255))
    draw.ellipse((left + 37, top_y + 11, left + 55, top_y + 21), fill=(230, 230, 224, 255))
    draw.rounded_rectangle((left + 42, top_y - 61, left + 54, top_y + 27), radius=4, fill=(245, 238, 216, 255))
    draw.line((left + 46, top_y - 61, left + 48, top_y + 27), fill=(170, 162, 142, 160), width=1)
    draw.ellipse((left + 1, body_bottom - 10, right - 1, body_bottom + 17), fill=(104, 14, 22, 245))
    draw.ellipse((left + 7, body_bottom - 6, right - 7, body_bottom + 10), outline=(230, 145, 135, 150), width=2)
    draw.rounded_rectangle((left + 11, body_top + 28, left + 23, body_bottom - 24), radius=6, fill=(255, 132, 122, 55))
    draw.rounded_rectangle((right - 19, body_top + 18, right - 12, body_bottom - 42), radius=4, fill=(255, 210, 190, 68))

    layer.alpha_composite(can)
    base = crop.convert("RGBA")
    merged = Image.alpha_composite(base, layer)
    hand_mask = make_hand_restore_mask(crop)
    restored_hands = Image.composite(base, merged, hand_mask)
    return restored_hands.convert("RGB")


def refine_model_can_edit(crop: Image.Image, model_edit: Image.Image) -> Image.Image:
    if model_edit.size != crop.size:
        model_edit = model_edit.resize(crop.size, Image.Resampling.LANCZOS)
    base = crop.convert("RGBA")
    # Hide the original cup rim behind the can with nearby fur texture instead of stretching the can top.
    cover_mask = Image.new("L", crop.size, 0)
    cover_draw = ImageDraw.Draw(cover_mask)
    cover_draw.rounded_rectangle((222, 274, 300, 326), radius=18, fill=230)
    cover_mask = cover_mask.filter(ImageFilter.GaussianBlur(3.2))
    fur_texture = crop.crop((262, 216, 342, 300)).resize(crop.size, Image.Resampling.BICUBIC).convert("RGBA")
    fur_texture = fur_texture.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.composite(fur_texture, base, cover_mask)

    overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    # Build the can on the original crop so old cup artifacts cannot leak through.
    left, right = 158, 268
    top_y = 296
    body_top, body_bottom = 312, 426
    draw.rounded_rectangle((left, body_top, right, body_bottom), radius=12, fill=(166, 18, 28, 242))
    draw.ellipse((left, top_y, right, top_y + 34), fill=(215, 216, 211, 255), outline=(104, 105, 102, 235), width=2)
    draw.ellipse((left + 8, top_y + 6, right - 8, top_y + 27), fill=(238, 238, 232, 245))
    draw.ellipse((left + 37, top_y + 8, left + 72, top_y + 25), fill=(118, 119, 116, 255))
    draw.ellipse((left + 45, top_y + 12, left + 65, top_y + 22), fill=(228, 228, 222, 255))
    draw.rounded_rectangle((left + 16, body_top + 18, left + 29, body_bottom - 21), radius=6, fill=(255, 128, 116, 55))
    draw.rounded_rectangle((right - 23, body_top + 13, right - 15, body_bottom - 33), radius=4, fill=(255, 219, 190, 72))
    draw.arc((left + 8, body_bottom - 16, right - 8, body_bottom + 8), start=0, end=180, fill=(236, 144, 132, 120), width=2)
    merged = Image.alpha_composite(base, overlay)

    clean_top = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    top_clean_draw = ImageDraw.Draw(clean_top, "RGBA")
    top_clean_draw.rounded_rectangle((200, 228, 212, 314), radius=4, fill=(245, 238, 214, 255))
    top_clean_draw.line((204, 228, 206, 314), fill=(176, 166, 142, 150), width=1)
    top_clean_draw.ellipse((198, 278, 222, 301), fill=(110, 110, 108, 210))
    top_clean_draw.ellipse((203, 282, 218, 297), fill=(226, 226, 220, 245))
    merged = Image.alpha_composite(merged, clean_top)

    hand_mask = make_hand_restore_mask(crop)
    restored_hands = Image.composite(crop.convert("RGBA"), merged, hand_mask)
    return restored_hands.convert("RGB")


def make_inpaint_workflow(image_name: str, mask_name: str, prompt: str, seed: int, steps: int, denoise: float) -> dict:
    negative = (
        "coffee, coffee cup, paper cup, plastic cup, transparent cup, glass, clear plastic, visible liquid, latte foam, logo, brand text, readable text, extra paws, extra hands, deformed paws, "
        "change hamster face, change hamster body, change background, shirt, clothing mockup, blur, low quality"
    )
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "6": {
            "class_type": "InpaintModelConditioning",
            "inputs": {
                "positive": ["4", 0],
                "negative": ["5", 0],
                "vae": ["1", 2],
                "pixels": ["2", 0],
                "mask": ["3", 0],
                "noise_mask": True,
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 6.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["6", 2],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hamster_cola_inpaint", "images": ["8", 0]}},
    }


def make_remove_cup_workflow(image_name: str, mask_name: str, prompt: str, seed: int, steps: int, denoise: float) -> dict:
    negative = (
        "cup, drink, coffee, cola, soda can, can, straw, glass, bottle, paper cup, plastic cup, latte foam, "
        "extra object, logo, readable text, extra paws, extra hands, deformed paws, change hamster face, "
        "change hamster body, shirt, clothing mockup, blur, low quality"
    )
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "6": {
            "class_type": "InpaintModelConditioning",
            "inputs": {
                "positive": ["4", 0],
                "negative": ["5", 0],
                "vae": ["1", 2],
                "pixels": ["2", 0],
                "mask": ["3", 0],
                "noise_mask": True,
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 5.8,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["6", 2],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hamster_no_cup_inpaint", "images": ["8", 0]}},
    }


def save_previews(rgba: Image.Image, out_dir: Path, stem: str) -> None:
    for name, color in (("black", (16, 16, 16)), ("white", (245, 245, 245))):
        bg = Image.new("RGBA", rgba.size, (*color, 255))
        bg.alpha_composite(rgba)
        bg.convert("RGB").save(out_dir / f"{stem}_preview_{name}.jpg", quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract the hamster print and locally inpaint the drink as cola.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "AI印花贴图测试" / f"hamster_cola_local_test_{date.today().isoformat()}")
    parser.add_argument("--mode", choices=("cola-can", "remove-cup"), default="cola-can")
    parser.add_argument("--seed", type=int, default=2026061501)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--denoise", type=float, default=0.58)
    parser.add_argument("--skip-comfy", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGB")
    crop_box = (438, 665, 858, 1298)
    crop = source.crop(crop_box)
    crop.save(args.output_dir / "_hamster_crop_source.jpg", quality=96)

    rgba, alpha = extract_hamster(crop)
    alpha.save(args.output_dir / "_hamster_alpha.png")
    trim_alpha(rgba).save(args.output_dir / "hamster_cutout_original_drink.png")
    save_previews(trim_alpha(rgba), args.output_dir, "hamster_cutout_original_drink")

    drink_mask = make_remove_cup_mask(crop.size) if args.mode == "remove-cup" else make_drink_mask(crop.size)
    drink_mask.save(args.output_dir / "_drink_inpaint_mask.png")

    if args.skip_comfy:
        print(f"Output dir: {args.output_dir}")
        return 0

    wait_server()
    image_name = "hamster_cola_inpaint_source.png"
    mask_name = "hamster_cola_inpaint_mask.png"
    COMFY_DIR.joinpath("input").mkdir(parents=True, exist_ok=True)
    crop.save(COMFY_DIR / "input" / image_name)
    drink_mask.convert("RGB").save(COMFY_DIR / "input" / mask_name)

    if args.mode == "remove-cup":
        prompt = (
            "Natural product print edit: preserve the hamster exactly, preserve the face, body, paws and pose, "
            "remove the cup, remove the straw, remove any drink object, fill the removed area with natural cream hamster fur "
            "and small relaxed paws touching naturally in front of the body, seamless soft lighting matching the original print, "
            "no object in the hands"
        )
        workflow = make_remove_cup_workflow(image_name, mask_name, prompt, args.seed, args.steps, args.denoise)
    else:
        prompt = (
            "Natural product print edit: preserve the hamster exactly, preserve the paws and pose, "
            "replace only the drink with a small opaque red aluminum cola soda can, vertical cylindrical can shape, "
            "metal top with pull tab opening, a simple white straw inserted through the opening, "
            "solid red metal can body with subtle silver highlights, no transparent liquid, no glass, no logo, no readable text, "
            "realistic soft lighting matching the original print, the can remains held naturally between the hamster paws"
        )
        workflow = make_inpaint_workflow(image_name, mask_name, prompt, args.seed, args.steps, args.denoise)
    prompt_id = queue_prompt(workflow)
    print(f"queued {prompt_id}", flush=True)
    history = wait_prompt(prompt_id)
    status = history.get("status", {})
    if status.get("status_str") == "error":
        raise RuntimeError(f"ComfyUI error: {status}")
    outputs = copy_outputs(history, args.output_dir, "cola_try")
    if not outputs:
        cached = latest_comfy_output("hamster_cola_inpaint")
        if cached is None:
            raise RuntimeError("ComfyUI did not return an output image")
        cached_copy = args.output_dir / f"cola_try_{cached.name}"
        shutil.copy2(cached, cached_copy)
        outputs = [cached_copy]
    raw_edited = ImageOps.exif_transpose(Image.open(outputs[0])).convert("RGB")
    if args.mode == "remove-cup":
        edited = composite_drink_edit(crop, raw_edited, drink_mask)
        edited.save(args.output_dir / "hamster_no_cup_inpaint_full_crop.png")
        texture_edited = remove_cup_with_fur_texture(crop)
        texture_edited.save(args.output_dir / "hamster_no_cup_texture_full_crop.png")
        transparent_removed = remove_cup_to_transparency(rgba, alpha)
        final = trim_alpha(transparent_removed)
        final.save(args.output_dir / "hamster_cutout_cup_removed_transparent.png")
        save_previews(final, args.output_dir, "hamster_cutout_cup_removed_transparent")
        print(f"Output dir: {args.output_dir}")
        print(f"Final: {args.output_dir / 'hamster_cutout_cup_removed_transparent.png'}")
        return 0

    edited = composite_drink_edit(crop, raw_edited, drink_mask)
    edited.save(args.output_dir / "hamster_cola_inpaint_full_crop.png")
    edited_rgba = edited.convert("RGBA")
    edited_rgba.putalpha(alpha)
    final = trim_alpha(edited_rgba)
    final.save(args.output_dir / "hamster_cutout_cola_can.png")
    save_previews(final, args.output_dir, "hamster_cutout_cola_can")

    clean_edited = make_clean_can_edit(crop)
    clean_edited.save(args.output_dir / "hamster_cola_can_clean_full_crop.png")
    clean_rgba = clean_edited.convert("RGBA")
    clean_rgba.putalpha(alpha)
    clean_final = trim_alpha(clean_rgba)
    clean_final.save(args.output_dir / "hamster_cutout_cola_can_clean.png")
    save_previews(clean_final, args.output_dir, "hamster_cutout_cola_can_clean")

    refined_edited = refine_model_can_edit(crop, edited)
    refined_edited.save(args.output_dir / "hamster_cola_can_refined_full_crop.png")
    refined_rgba = refined_edited.convert("RGBA")
    refined_rgba.putalpha(alpha)
    refined_final = trim_alpha(refined_rgba)
    refined_final.save(args.output_dir / "hamster_cutout_cola_can_refined.png")
    save_previews(refined_final, args.output_dir, "hamster_cutout_cola_can_refined")
    print(f"Output dir: {args.output_dir}")
    print(f"Final: {args.output_dir / 'hamster_cutout_cola_can_refined.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
