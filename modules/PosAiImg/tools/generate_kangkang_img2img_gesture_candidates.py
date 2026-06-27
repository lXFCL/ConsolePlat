from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
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


ROOT = Path(__file__).resolve().parents[1]
REALVIS = "RealVisXL_V5.0_fp16.safetensors"

NEGATIVE = (
    "face, head, person, body, torso, shirt, t-shirt, jersey, clothing, logo, text, watermark, sleeve, tattoo, "
    "background scene, esports stage, blue background, purple background, colored lights, decorative frame, circle, mandala, "
    "extra fingers, extra hands, deformed anatomy, blurry, low quality, cropped fingers, full body, photorealistic photo"
)


@dataclass(frozen=True)
class Img2ImgSpec:
    key: str
    prompt: str
    denoise: float
    cfg: float


def prepare_reference(source: Path, target_name: str, size: int) -> str:
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    w, h = image.size
    crop = image.crop((int(w * 0.26), int(h * 0.27), int(w * 0.80), int(h * 0.82)))
    canvas = Image.new("RGB", (size, size), "white")
    target_w = int(size * 0.92)
    target_h = max(1, int(crop.height * target_w / crop.width))
    if target_h > int(size * 0.82):
        target_h = int(size * 0.82)
        target_w = max(1, int(crop.width * target_h / crop.height))
    crop = crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
    canvas.paste(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    input_path = COMFY_DIR / "input" / target_name
    input_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(input_path, quality=94)
    return target_name


def build_specs() -> list[Img2ImgSpec]:
    base = (
        "redraw the reference gesture as an original monochrome black white gray printable hand gesture decal, "
        "preserve the same iconic pose: one vertical open palm on the right and one bent wrist hand crossing in front with fingers pointing downward, "
        "hands and forearm gesture only, remove the face, remove the shirt, remove the jersey, remove all colored background, "
        "realistic hand anatomy, graphite pencil sketch, charcoal drawing, ink engraving, high contrast monochrome screen print, "
        "isolated centered artwork on pure white background, crisp black linework, gray shading, no text"
    )
    return [
        Img2ImgSpec("strong_redraw_engraving", base + ", fine engraving lines, detailed knuckles and fingernails", 0.72, 8.0),
        Img2ImgSpec("strong_redraw_bold", base + ", bold black outline, fewer details, readable small chest print", 0.78, 8.5),
        Img2ImgSpec("monochrome_decal", base + ", clean sticker-like decal, no decorative elements, crisp edge", 0.84, 8.5),
        Img2ImgSpec("screenprint_redraw", base + ", screenprint style, strong white highlights and dark contour lines", 0.90, 9.0),
    ]


def make_workflow(image_name: str, prompt: str, seed: int, steps: int, denoise: float, cfg: float) -> dict:
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": REALVIS},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "3": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE, "clip": ["1", 1]},
        },
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
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "kangkang_img2img_gesture", "images": ["7", 0]},
        },
    }


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 48
    cols = 2
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
        draw.text((x0 + 12, y0 + tile + 12), path.stem[:38], fill=(0, 0, 0))
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate img2img candidates from the Kangkang gekokujo reference photo.")
    parser.add_argument("--source", type=Path, default=ROOT / "参考图" / "zmjjkk_gekokujo_reference.jpg")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061368)
    parser.add_argument("--steps", type=int, default=26)
    parser.add_argument("--size", type=int, default=896)
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
    input_name = prepare_reference(args.source, f"kangkang_gekokujo_reference_{args.size}.jpg", args.size)
    output_dir = ROOT / "印花图_透明底" / f"康康参考图img2img黑白灰手势候选_{args.date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(COMFY_DIR / "input" / input_name, output_dir / "_img2img_input.jpg")

    notes = ROOT / "生成提示词" / f"康康参考图img2img黑白灰手势候选_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    specs = build_specs()
    notes.write_text(
        "\n".join(f"{idx + 1}. {spec.key} denoise={spec.denoise} cfg={spec.cfg}\n{spec.prompt}\n" for idx, spec in enumerate(specs)),
        encoding="utf-8",
    )

    started = None
    started_at = time.time()
    if args.auto_start_comfyui:
        started = start_comfyui(args.comfy_timeout)
    else:
        wait_server()
    try:
        paths: list[Path] = []
        for idx, spec in enumerate(specs, start=1):
            workflow = make_workflow(input_name, spec.prompt, args.seed + idx * 9973, args.steps, spec.denoise, spec.cfg)
            prompt_id = queue_prompt(workflow)
            print(f"queued {idx}: {spec.key}", flush=True)
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.key}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, output_dir, f"{idx:02d}_{spec.key}", args.bg_threshold, args.bg_color_distance, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.key}: expected one generated output, got {len(copied)}")
            final = output_dir / f"{idx:02d}_{spec.key}.png"
            copied[0].replace(final)
            paths.append(final)
            print(f"saved {final}", flush=True)
        make_overview(paths, output_dir / "_overview.jpg")
        print(f"Output dir: {output_dir}")
        print(f"Overview: {output_dir / '_overview.jpg'}")
        print(f"Elapsed seconds: {time.time() - started_at:.1f}")
        return 0
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    raise SystemExit(main())
