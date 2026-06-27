from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comfy_print_batch  # noqa: E402
from comfy_print_batch import copy_outputs, make_workflow, queue_prompt, start_comfyui, stop_comfyui, wait_prompt, wait_server  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REALVIS = "RealVisXL_V5.0_fp16.safetensors"


@dataclass(frozen=True)
class GestureStyleSpec:
    key: str
    prompt: str


def common_style() -> str:
    return (
        "isolated disembodied hands only, wrists cut off cleanly, no arms beyond short wrists, "
        "front-facing black white gray realistic printable hand gesture decal, "
        "silver rings on fingers, one silver bracelet, luxury high street jewelry detail, "
        "grayscale studio lighting, realistic skin folds, detailed knuckles and fingernails, "
        "high contrast monochrome screen print, floating centered print asset on pure white background, "
        "transparent PNG preparation, no person, no man, no woman, no face, no head, no hair, no neck, "
        "no torso, no shirt, no t-shirt, no clothing, no sleeve, no logo, no text, no tattoo, "
        "no colored background, no black background, no rectangle, no border, no decorative frame, no circle, no mandala, "
        "no extra fingers, no extra hands, clean silhouette, product print artwork only"
    )


def build_specs() -> list[GestureStyleSpec]:
    base = common_style()
    return [
        GestureStyleSpec(
            "gekokujo_up_down_front",
            base
            + ", left hand makes a fist with one index finger pointing straight upward, right hand makes a fist with index and middle fingers pointing downward, both palms face the viewer, lower-overcomes-upper gesture",
        ),
        GestureStyleSpec(
            "double_down_front",
            base
            + ", two separate front-facing fists, both hands make index and middle fingers pointing downward, bold downward challenge sign, rings visible on the folded fingers",
        ),
        GestureStyleSpec(
            "crossed_index_front",
            base
            + ", two front-facing fists with both index fingers extended and crossed in the center, fingers form an X sign, compact symmetrical street hand sign",
        ),
        GestureStyleSpec(
            "rock_horns_front",
            base
            + ", two front-facing hands making rock horn signs, index and little fingers extended on each hand, middle and ring fingers folded, rings and bracelet visible",
        ),
        GestureStyleSpec(
            "finger_frame_front",
            base
            + ", two front-facing hands forming a rectangular finger frame, thumbs horizontal and index fingers vertical, rings visible, clean high street graphic gesture",
        ),
    ]


def make_overview(paths: list[Path], output_path: Path, bg_color: str) -> None:
    tile = 330
    label_h = 48
    cols = len(paths)
    sheet = Image.new("RGB", (cols * tile, tile + label_h), bg_color)
    draw = ImageDraw.Draw(sheet)
    label_color = (0, 0, 0) if bg_color == "white" else (230, 230, 230)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, bg_color)
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = idx * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((idx * tile + 12, tile + 12), path.stem[:36], fill=label_color)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 5 different front-facing monochrome streetwear hand gesture print variants.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061390)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--width", type=int, default=896)
    parser.add_argument("--height", type=int, default=896)
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
    specs = build_specs()
    out_dir = ROOT / "印花图_透明底" / f"正面不同手势黑白灰高街印花5款_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    notes = ROOT / "生成提示词" / f"正面不同手势黑白灰高街印花5款_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(
        "\n".join(f"{idx + 1}. {spec.key}\n{spec.prompt}\n" for idx, spec in enumerate(specs)),
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
            workflow = make_workflow(spec.prompt, args.seed + idx * 9973, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"queued {idx}: {spec.key}", flush=True)
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.key}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, out_dir, f"{idx:02d}_{spec.key}", args.bg_threshold, args.bg_color_distance, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.key}: expected one generated output, got {len(copied)}")
            final = out_dir / f"{idx:02d}_{spec.key}.png"
            copied[0].replace(final)
            paths.append(final)
            print(f"saved {final}", flush=True)
        make_overview(paths, out_dir / "_overview_on_black.jpg", "black")
        make_overview(paths, out_dir / "_overview_on_white.jpg", "white")
        print(f"Output dir: {out_dir}")
        print(f"Black overview: {out_dir / '_overview_on_black.jpg'}")
        print(f"White overview: {out_dir / '_overview_on_white.jpg'}")
        print(f"Elapsed seconds: {time.time() - started_at:.1f}")
        return 0
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


if __name__ == "__main__":
    raise SystemExit(main())
