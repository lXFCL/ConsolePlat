from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comfy_print_batch  # noqa: E402
from comfy_print_batch import (  # noqa: E402
    COMFY_DIR,
    copy_outputs,
    queue_prompt,
    start_comfyui,
    stop_comfyui,
    wait_prompt,
    wait_server,
)


ROOT = Path(__file__).resolve().parents[1]
REALVIS = "RealVisXL_V5.0_fp16.safetensors"
JUGGERNAUT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"


NEGATIVE_HANDS = (
    "face, head, person, body, torso, shirt, t-shirt, clothing, sleeve, logo, watermark, text, "
    "anime character, cartoon, chibi, colored outfit, orange outfit, symbol from existing media, "
    "magic effects, flame, aura, background scene, floor, table, frame, cropped hands, one hand only, "
    "extra fingers, missing fingers, fused fingers, deformed anatomy, blurry, low quality"
)


@dataclass(frozen=True)
class HandSpec:
    stem: str
    label: str
    prompt: str


def crop_reference_print(image: Image.Image) -> Image.Image:
    width, height = image.size
    return image.crop(
        (
            int(width * 0.25),
            int(height * 0.25),
            int(width * 0.78),
            int(height * 0.64),
        )
    )


def extract_gray_print(crop: Image.Image, size: int) -> Image.Image:
    rgb_img = crop.convert("RGB")
    rgb = np.asarray(rgb_img).astype(np.int16)
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    luma = (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.float32)
    chroma = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])

    dark_ink = np.clip((236 - luma) * 2.15, 0, 255)
    non_white_gray = (luma < 236) & (chroma < 78)
    deep_detail = luma < 190
    alpha = np.where(non_white_gray | deep_detail, dark_ink, 0).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, "L")
    alpha_img = alpha_img.filter(ImageFilter.MaxFilter(3))
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(0.45))

    gray = ImageOps.grayscale(rgb_img)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray_arr = np.asarray(gray, dtype=np.uint8)
    ink_rgb = np.stack([gray_arr, gray_arr, gray_arr], axis=-1)
    rgba = np.dstack([ink_rgb, np.asarray(alpha_img, dtype=np.uint8)])
    out = Image.fromarray(rgba, "RGBA")

    bbox = out.getbbox()
    if bbox:
        pad = 90
        out = out.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(out.width, bbox[2] + pad),
                min(out.height, bbox[3] + pad),
            )
        )
    out.thumbnail((int(size * 0.92), int(size * 0.92)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(out, ((size - out.width) // 2, (size - out.height) // 2))
    return canvas


def make_preview(path: Path, output: Path, bg: str) -> None:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    canvas = Image.new("RGBA", img.size, bg)
    canvas.alpha_composite(img)
    canvas.convert("RGB").save(output, quality=94)


def prepare_img2img_reference(source: Path, target_name: str, size: int) -> str:
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    width, height = image.size
    crop = image.crop(
        (
            int(width * 0.24),
            int(height * 0.28),
            int(width * 0.72),
            int(height * 0.78),
        )
    )
    canvas = Image.new("RGB", (size, size), "white")
    target_w = int(size * 0.90)
    target_h = max(1, int(crop.height * target_w / crop.width))
    if target_h > int(size * 0.86):
        target_h = int(size * 0.86)
        target_w = max(1, int(crop.width * target_h / crop.height))
    crop = crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
    canvas.paste(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    input_path = COMFY_DIR / "input" / target_name
    input_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(input_path, quality=94)
    return target_name


def make_img2img_workflow(image_name: str, prompt: str, seed: int, steps: int, denoise: float, cfg: float) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": REALVIS}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE_HANDS, "clip": ["1", 1]}},
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0],
            },
        },
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "kangkang_reference_style_hand", "images": ["7", 0]}},
    }


def make_text2img_workflow(prompt: str, seed: int, steps: int, width: int, height: int) -> dict:
    positive = (
        f"{prompt}, original monochrome black white gray printable decal, two realistic adult human hands only, "
        "hands touching each other, compact martial hand sign, detailed knuckles, fingernails, tendons, skin folds, "
        "photorealistic graphite and charcoal shading, crisp black ink linework, high contrast grayscale screen print, "
        "isolated centered artwork on pure white background, generous empty margin, no text"
    )
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 7.6,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": REALVIS}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE_HANDS, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "zodiac_handseal_style", "images": ["8", 0]}},
    }


def build_handseal_specs() -> list[HandSpec]:
    base = "ninja-inspired zodiac hand seal, not from any existing anime, original gesture"
    return [
        HandSpec("01_zi_rat", "子", f"{base}, rat sign, both index fingers vertical and pressed together, thumbs crossed at the base, remaining fingers folded tightly"),
        HandSpec("02_chou_ox", "丑", f"{base}, ox sign, fingers interlocked horizontally, both thumbs locked, heavy knuckles and strong compact silhouette"),
        HandSpec("03_yin_tiger", "寅", f"{base}, tiger sign, vertical prayer-like hands with two index fingers extended upward together, other fingers clasped"),
        HandSpec("04_mao_rabbit", "卯", f"{base}, rabbit sign, two raised fingers forming narrow ears, opposite hand braces the wrist, compact realistic mudra"),
        HandSpec("05_chen_dragon", "辰", f"{base}, dragon sign, fingertips touching to form a small triangular window, thumbs horizontal and crossed, tense angular pose"),
        HandSpec("06_si_snake", "巳", f"{base}, snake sign, both hands clasped with long index fingers weaving around each other, sinuous closed shape"),
        HandSpec("07_wu_horse", "午", f"{base}, horse sign, palms facing inward, fingers folded into a saddle-like block, thumbs pressed side by side"),
        HandSpec("08_wei_goat", "未", f"{base}, goat sign, two hands stacked diagonally, ring and middle fingers curled inward, thumbs forming small horns"),
        HandSpec("09_shen_monkey", "申", f"{base}, monkey sign, crossed wrists, bent fingers hooked together, playful but realistic compact combat seal"),
    ]


def make_overview(paths: list[Path], output_path: Path, cols: int = 4) -> None:
    tile = 360
    label_h = 50
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile
        y0 = (idx // cols) * (tile + label_h)
        sheet.paste(preview, (x0 + (tile - preview.width) // 2, y0 + (tile - preview.height) // 2))
        draw.text((x0 + 12, y0 + tile + 12), path.stem[:42], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def write_notes(output_dir: Path, hand_specs: list[HandSpec], kangkang_prompt: str) -> None:
    notes = output_dir / "_prompts.txt"
    lines = [
        "Reference style: realistic monochrome grayscale hand gesture print, T-shirt printable, no logo/text.",
        "",
        "Kangkang img2img prompt:",
        kangkang_prompt,
        "",
        "Zodiac-inspired original hand seal prompts:",
    ]
    for spec in hand_specs:
        lines.append(f"{spec.stem} {spec.label}: {spec.prompt}")
    notes.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract reference T-shirt print and generate matching hand gesture print assets.")
    parser.add_argument("--source", type=Path, default=ROOT / "爆款印花知识库" / "爆款1" / "c2f71ffcc04d40cba78e4526a00f0c72-goods.jpeg")
    parser.add_argument("--kangkang-source", type=Path, default=ROOT / "参考图" / "zmjjkk_gekokujo_reference.jpg")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061601)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--size", type=int, default=1200)
    parser.add_argument("--gen-size", type=int, default=1024)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=420)
    parser.add_argument("--prompt-timeout", type=int, default=1200)
    parser.add_argument("--keep-comfyui", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comfy_print_batch.CHECKPOINT = REALVIS
    output_dir = ROOT / "印花图_透明底" / f"写实黑白手势印花_{args.date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_img = ImageOps.exif_transpose(Image.open(args.source)).convert("RGB")
    crop = crop_reference_print(source_img)
    crop_path = output_dir / "_reference_crop.jpg"
    crop.save(crop_path, quality=95)
    extracted = output_dir / "00_reference_tshirt_print_extracted.png"
    extract_gray_print(crop, args.size).save(extracted)
    make_preview(extracted, output_dir / "00_reference_tshirt_print_extracted_preview_white.jpg", "white")
    make_preview(extracted, output_dir / "00_reference_tshirt_print_extracted_preview_black.jpg", "black")
    print(f"saved {extracted}", flush=True)

    hand_specs = build_handseal_specs()
    kangkang_prompt = (
        "redraw the reference gesture as an original monochrome black white gray printable hand gesture decal, "
        "preserve the rebellious two-hand pose idea with one vertical hand and one crossing hand, hands and wrists only, "
        "realistic hand anatomy, jewelry-like rings optional, long fingernails optional, graphite pencil and charcoal shading, "
        "high contrast grayscale screen print, isolated centered artwork on pure white background, no text, no logo"
    )
    write_notes(output_dir, hand_specs, kangkang_prompt)

    started = None
    started_at = time.time()
    if args.auto_start_comfyui:
        started = start_comfyui(args.comfy_timeout)
    else:
        wait_server()
    try:
        generated_paths: list[Path] = [extracted]

        input_name = prepare_img2img_reference(args.kangkang_source, f"kangkang_reference_style_{args.gen_size}.jpg", args.gen_size)
        shutil.copy2(COMFY_DIR / "input" / input_name, output_dir / "_kangkang_img2img_input.jpg")
        workflow = make_img2img_workflow(input_name, kangkang_prompt, args.seed + 101, args.steps, denoise=0.74, cfg=8.0)
        prompt_id = queue_prompt(workflow)
        print("queued kangkang img2img", flush=True)
        history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
        if history.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"kangkang img2img ComfyUI error: {history.get('status')}")
        copied = copy_outputs(history, output_dir, "10_kangkang_gekokujo_style", args.bg_threshold, args.bg_color_distance, False)
        if len(copied) != 1:
            raise RuntimeError(f"kangkang img2img expected one output, got {len(copied)}")
        kangkang_final = output_dir / "10_kangkang_gekokujo_style.png"
        copied[0].replace(kangkang_final)
        generated_paths.append(kangkang_final)
        print(f"saved {kangkang_final}", flush=True)

        for index, spec in enumerate(hand_specs, start=1):
            workflow = make_text2img_workflow(spec.prompt, args.seed + 1000 + index * 9973, args.steps, args.gen_size, args.gen_size)
            prompt_id = queue_prompt(workflow)
            print(f"queued {spec.stem} {spec.label}", flush=True)
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.stem}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, output_dir, spec.stem, args.bg_threshold, args.bg_color_distance, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.stem}: expected one output, got {len(copied)}")
            final = output_dir / f"{spec.stem}_{spec.label}.png"
            copied[0].replace(final)
            generated_paths.append(final)
            print(f"saved {final}", flush=True)

        make_overview(generated_paths, output_dir / "_overview_all.jpg", cols=4)
        make_overview(generated_paths[2:], output_dir / "_overview_9_zodiac_handseals.jpg", cols=3)
        print(f"Output dir: {output_dir}", flush=True)
        print(f"Overview: {output_dir / '_overview_all.jpg'}", flush=True)
        print(f"Elapsed seconds: {time.time() - started_at:.1f}", flush=True)
        return 0
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    raise SystemExit(main())
