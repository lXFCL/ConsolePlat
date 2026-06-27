from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

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
from make_cat_text_reference_variants import extract_print  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
OUT_DIR = ROOT / "印花图_透明底" / "猫咪韩文参考本地模型小改动_2026-06-15"
CHECKPOINT = "RealVisXL_V5.0_fp16.safetensors"

NEGATIVE = (
    "shirt, t-shirt, clothing mockup, photo background, fabric folds, model, person, hand, watermark, logo, "
    "new unreadable large text, extra character, extra animal, deformed cat, blurry, low quality, cropped artwork, "
    "busy background, frame, border, shadow, photorealistic animal"
)


@dataclass(frozen=True)
class Variant:
    key: str
    prompt: str
    denoise: float
    cfg: float


def make_input(source: Path, target_name: str, size: int) -> str:
    extracted = extract_print(source, size).convert("RGBA")
    white = Image.new("RGBA", extracted.size, (255, 255, 255, 255))
    white.alpha_composite(extracted)
    rgb = white.convert("RGB")
    input_path = COMFY_DIR / "input" / target_name
    input_path.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(input_path, quality=95)
    return target_name


def specs() -> list[Variant]:
    base = (
        "preserve the same simple gray cartoon cat holding a fish and the same Korean handwritten text layout, "
        "isolated printable t-shirt decal on pure white background, black outline, small cute minimal edit only, "
        "keep composition nearly identical, keep the cat shape and fish shape recognizable"
    )
    return [
        Variant("01_subtle_line", base + ", add one thin underline accent below the Korean text", 0.20, 5.2),
        Variant("02_tiny_stars", base + ", add two tiny simple sparkle stars near the cat ear", 0.23, 5.4),
        Variant("03_warm_glasses", base + ", make the sunglasses warmer amber orange, no other major change", 0.21, 5.2),
        Variant("04_blue_fish", base + ", make the fish slightly pale blue while keeping black outline", 0.24, 5.5),
        Variant("05_soft_smile", base + ", make the cat mouth slightly more smiling, subtle expression change", 0.25, 5.5),
    ]


def make_workflow(image_name: str, prompt: str, seed: int, steps: int, denoise: float, cfg: float) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0],
            },
        },
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "cat_reference_img2img", "images": ["7", 0]}},
    }


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 330
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * tile, tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 28, tile - 28), Image.Resampling.LANCZOS)
        x = i * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((i * tile + 12, tile + 11), path.stem[:34], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate five local ComfyUI img2img variants from the cat Korean-text reference.")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--size", type=int, default=896)
    parser.add_argument("--seed", type=int, default=2026061501)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=420)
    parser.add_argument("--prompt-timeout", type=int, default=1200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comfy_print_batch.CHECKPOINT = CHECKPOINT
    args.output_dir.mkdir(parents=True, exist_ok=True)
    input_name = make_input(args.source, f"cat_korean_reference_{args.size}.jpg", args.size)
    shutil.copy2(COMFY_DIR / "input" / input_name, args.output_dir / "_img2img_input.jpg")

    started = None
    started_at = time.time()
    if args.auto_start_comfyui:
        started = start_comfyui(args.comfy_timeout)
    else:
        wait_server()
    try:
        paths: list[Path] = []
        for index, spec in enumerate(specs(), start=1):
            workflow = make_workflow(input_name, spec.prompt, args.seed + index * 991, args.steps, spec.denoise, spec.cfg)
            prompt_id = queue_prompt(workflow)
            print(f"queued {spec.key} denoise={spec.denoise}", flush=True)
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.key}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, args.output_dir, spec.key, 244, 42.0, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.key}: expected 1 output, got {len(copied)}")
            final = args.output_dir / f"{spec.key}.png"
            copied[0].replace(final)
            paths.append(final)
            print(f"saved {final}", flush=True)
        make_overview(paths, args.output_dir / "_overview.jpg")
        print(f"Output dir: {args.output_dir}")
        print(f"Overview: {args.output_dir / '_overview.jpg'}")
        print(f"Elapsed seconds: {time.time() - started_at:.1f}")
        return 0
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    raise SystemExit(main())
