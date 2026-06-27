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
from comfy_print_batch import (  # noqa: E402
    copy_outputs,
    make_workflow,
    queue_prompt,
    start_comfyui,
    stop_comfyui,
    wait_prompt,
    wait_server,
)


ROOT = Path(__file__).resolve().parents[1]
REALVIS = "RealVisXL_V5.0_fp16.safetensors"


@dataclass(frozen=True)
class CandidateSpec:
    key: str
    prompt: str


def common_prompt() -> str:
    return (
        "black white gray realistic human hand gesture printable t-shirt decal, adult human hands only, "
        "inspired by the gekokujo lower-overcomes-upper esports hand sign, two bare hands only, "
        "one right hand is vertical like a stop sign with palm facing viewer and fingers together, "
        "one left hand crosses in front with a bent limp wrist and fingers pointing downward, "
        "the downward wrist hand overlaps the vertical palm hand, asymmetrical challenger gesture, wrists only, no arms beyond short wrists, "
        "graphite sketch, charcoal and ink engraving style, detailed knuckles, tendons, fingernails, skin folds, "
        "high contrast monochrome screen print, thick readable silhouette, isolated centered artwork on pure white background, "
        "transparent PNG preparation, no face, no head, no person, no body, no torso, no shirt, no t-shirt, no jersey, no clothing, "
        "no copyrighted logo, no brand, no text, no sleeve, no tattoo, no magic effects, no circle, no mandala, no frame, "
        "no decorative background, no extra fingers, no extra hands, anatomically correct hands, clean silhouette"
    )


def build_specs() -> list[CandidateSpec]:
    base = common_prompt()
    return [
        CandidateSpec(
            "vertical_palm_down_wrist",
            base
            + ", front view, vertical palm behind, bent wrist hand crosses in front horizontally, fingers hang downward over the palm, compact centered pose",
        ),
        CandidateSpec(
            "stop_palm_limp_hand",
            base
            + ", stop-sign palm on the right side, other hand draped across the lower palm with wrist bent sharply downward, fingers relaxed and pointing to the floor",
        ),
        CandidateSpec(
            "esports_pose_close_crop",
            base
            + ", close cropped hands only, palm vertical, second wrist folded down at ninety degrees, the two wrists touch, no pointing index fingers",
        ),
        CandidateSpec(
            "downward_fingers_over_palm",
            base
            + ", downward hand shows four fingers hanging in front of the vertical palm, thumb partly hidden, strong overlapping layered silhouette",
        ),
        CandidateSpec(
            "clean_two_hand_symbol",
            base
            + ", clean two-hand symbol, no mystical decoration, no body crop, no background emblem, simplified realistic ink print",
        ),
        CandidateSpec(
            "bold_screenprint_version",
            base
            + ", bold screenprint version, fewer tiny details, dark outlines, white highlights, readable from far away, the bent wrist and vertical palm shape must be obvious",
        ),
    ]


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 360
    label_h = 48
    cols = 3
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Kangkang gekokujo-style monochrome hand gesture print candidates.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061350)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--width", type=int, default=896)
    parser.add_argument("--height", type=int, default=896)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=420)
    parser.add_argument("--prompt-timeout", type=int, default=1200)
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--regenerate-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comfy_print_batch.CHECKPOINT = REALVIS
    specs = build_specs()
    output_dir = ROOT / "印花图_透明底" / f"康康以下克上黑白灰写实手势候选_{args.date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    notes = ROOT / "生成提示词" / f"康康以下克上黑白灰写实手势候选_{args.date}.txt"
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
            final = output_dir / f"{idx:02d}_{spec.key}.png"
            if final.exists() and not args.regenerate_existing:
                print(f"reuse {final}")
                paths.append(final)
                continue
            workflow = make_workflow(spec.prompt, args.seed + idx * 9973, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"queued {idx}: {spec.key}", flush=True)
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.key}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(
                history,
                output_dir,
                f"{idx:02d}_{spec.key}",
                args.bg_threshold,
                args.bg_color_distance,
                False,
            )
            if len(copied) != 1:
                raise RuntimeError(f"{spec.key}: expected one generated output, got {len(copied)}")
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
