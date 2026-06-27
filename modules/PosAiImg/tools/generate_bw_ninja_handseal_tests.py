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


@dataclass(frozen=True)
class SealSpec:
    name: str
    prompt: str


def build_specs() -> list[SealSpec]:
    base = (
        "original monochrome black white gray printable decal of realistic human hands forming a ninja-like hand seal, "
        "two hands only, realistic hand anatomy, adult hands, detailed knuckles, fingernails, tendons and skin folds, "
        "dramatic ink wash and graphite pencil shading, high contrast black linework, grayscale screen print style, "
        "isolated centered composition, pure white background for background removal, no sleeves, no arms beyond wrists, "
        "both hands must touch each other, fingers must interlock or press together, compact ritual mudra pose, "
        "closed hand sign, not open palms, not waving hands, not five fingers spread apart, not one hand, "
        "no face, no character, no anime character, no copyrighted symbol, no logo, no text, no orange outfit, "
        "no magic effects, no flames, no glowing aura, no cartoon style, no chibi, no simplified icon, "
        "not Naruto, not from any existing anime, original hand gesture inspired by martial arts hand signs"
    )
    return [
        SealSpec(
            "vertical_prayer_seal",
            base + ", palms pressed together vertically, all fingertips aligned and touching, thumbs crossed tightly at center, closed prayer-like combat seal",
        ),
        SealSpec(
            "interlocked_shadow_seal",
            base + ", fingers interlocked in a complex symmetrical seal, both index fingers crossing over each other, thumbs locked, tense knuckles, no open palms",
        ),
        SealSpec(
            "crossed_index_seal",
            base + ", both hands in front view with crossed index fingers and folded remaining fingers, compact ritual hand sign, strong silhouette, hands touching at knuckles",
        ),
        SealSpec(
            "triangle_focus_seal",
            base + ", fingertips touching to form a small triangle window between both hands, thumbs horizontal and touching, meditative martial sign, closed compact pose",
        ),
        SealSpec(
            "stacked_wrist_seal",
            base + ", one hand vertical and the other hand horizontal crossing in front, both hands visible and touching, fingers folded into a sharp angular seal, no solo hand",
        ),
    ]


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 42
    sheet = Image.new("RGB", (tile * len(paths), tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x = idx * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((idx * tile + 16, tile + 10), path.stem[:34], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 5 monochrome realistic hand-seal print tests.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061301)
    parser.add_argument("--steps", type=int, default=26)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=300)
    parser.add_argument("--prompt-timeout", type=int, default=1200)
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--regenerate-existing", action="store_true")
    parser.add_argument("--checkpoint", default=None, help="Override ComfyUI checkpoint filename.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = build_specs()
    if args.checkpoint:
        comfy_print_batch.CHECKPOINT = args.checkpoint
    output_dir = ROOT / "印花图_透明底" / f"黑白灰写实结印手势测试_{args.date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    notes = ROOT / "生成提示词" / f"黑白灰写实结印手势测试_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("\n".join(f"{idx + 1}. {spec.name}: {spec.prompt}" for idx, spec in enumerate(specs)) + "\n", encoding="utf-8")

    started = None
    started_at = time.time()
    if args.auto_start_comfyui:
        started = start_comfyui(args.comfy_timeout)
    else:
        wait_server()
    try:
        paths: list[Path] = []
        for index, spec in enumerate(specs):
            final = output_dir / f"{index + 1:02d}_{spec.name}.png"
            if final.exists() and not args.regenerate_existing:
                print(f"reuse {final}")
                paths.append(final)
                continue
            workflow = make_workflow(spec.prompt, args.seed + index * 9973, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"queued {index + 1}: {spec.name}")
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.name}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, output_dir, f"{index + 1:02d}_{spec.name}", args.bg_threshold, args.bg_color_distance, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.name}: expected one generated output, got {len(copied)}")
            copied[0].replace(final)
            paths.append(final)
            print(f"saved {final}")
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
