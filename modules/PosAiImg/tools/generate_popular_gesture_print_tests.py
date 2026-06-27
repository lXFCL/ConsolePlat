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
class GestureSpec:
    key: str
    title: str
    description: str
    prompt: str


def common_prompt() -> str:
    return (
        "black white gray realistic human hand gesture print decal, adult human hands only, "
        "graphite sketch, charcoal drawing and ink engraving style, detailed knuckles, tendons, nails, skin folds, "
        "high contrast monochrome screen print, thick readable silhouette, isolated centered artwork, pure white background for background removal, "
        "transparent PNG preparation, no face, no head, no full body, no character, no anime character, "
        "no copyrighted logo, no brand, no text, no clothing, no sleeve, no tattoo, no magic effects, "
        "no circle, no mandala, no sigil, no frame, no decorative background, no extra fingers, "
        "anatomically correct hands, clean silhouette, suitable for t-shirt chest print"
    )


def build_specs() -> list[GestureSpec]:
    base = common_prompt()
    return [
        GestureSpec(
            "gekokujo_up_down",
            "以下犯上 / 下克上感",
            "带挑衅感的上下指向、反叛姿态；转成一上一下两只手的对抗构图，适合街头感印花。",
            base + ", two separate realistic hands only, top hand enters from top edge with one index finger pointing downward, bottom hand enters from bottom edge with one index finger pointing upward, fingertips almost meeting in the center, both other hands mostly clenched, vertical opposition composition, plain white background only",
        ),
        GestureSpec(
            "single_point_sky",
            "单手指天",
            "单手食指竖直向上，强调“指向天空/天上天下”的强势姿态。",
            base + ", one single realistic hand only, closed fist with exactly one index finger extended straight upward, all other fingers tightly curled into the fist, thumb locking folded fingers, vertical pointing gesture, palm side visible, strong vertical silhouette, no middle finger raised, no open hand",
        ),
        GestureSpec(
            "ninja_prayer_seal",
            "忍者合掌结印",
            "双手掌面贴合、指尖向上，类似武术/忍者题材中结印前的集中姿势。",
            base + ", exactly two hands pressed palm to palm vertically like a compact martial arts mudra, fingertips aligned upward, thumbs crossed tightly, wrists close together, closed ritual hand seal pose, no open spread fingers, no prayer beads",
        ),
        GestureSpec(
            "ninja_interlock_seal",
            "忍者交叉结印",
            "两手手指互锁或交叉，形成紧凑复杂的结印结构。",
            base + ", exactly two bare hands touching each other, fingers woven together in a compact martial arts hand seal, crossed index fingers forming an X shape in the center, thumbs locked, both wrists visible, strong symmetrical silhouette, plain white background only, no open palms",
        ),
        GestureSpec(
            "confrontation_half_tiger",
            "对峙之印 / 半虎印感",
            "动漫忍者题材里常见的战斗准备手势，可理解为半个虎/羊印的对峙姿态；这里只保留通用手势，不使用角色元素。",
            base + ", one hand making a half-tiger confrontation sign, index and middle fingers raised together and pressed close, ring and little fingers folded, thumb locking folded fingers, compact martial combat readiness gesture, wrist only",
        ),
        GestureSpec(
            "rebel_fist",
            "握拳 / 反抗拳",
            "街头、乐队、复古海报里常见的举拳符号，黑白印花识别度高。",
            base + ", one realistic clenched fist raised upward, front view of knuckles, wrist visible, powerful protest fist silhouette, bold shadow and engraved line detail, plain white background only, no open fingers, no weapon",
        ),
        GestureSpec(
            "rock_horns",
            "摇滚角手势",
            "食指和小指伸出，其余手指收起，适合街头/音乐感印花。",
            base + ", one realistic hand making rock horns sign, index finger and little finger extended upward only, middle finger and ring finger folded down under the thumb, thumb crosses the palm, palm facing viewer, bold music gesture, plain white background only, not an open hand, no shaka",
        ),
        GestureSpec(
            "shaka_call",
            "Shaka / 电话手势",
            "拇指和小指张开，其余手指收起，偏滑板、冲浪、街头休闲。",
            base + ", one realistic hand making shaka call-me gesture, thumb and little finger extended outward, middle fingers folded, relaxed streetwear surf gesture",
        ),
    ]


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile = 330
    label_h = 42
    cols = 4
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile - 36, tile - 36), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile
        y0 = (idx // cols) * (tile + label_h)
        sheet.paste(preview, (x0 + (tile - preview.width) // 2, y0 + (tile - preview.height) // 2))
        draw.text((x0 + 12, y0 + tile + 10), path.stem[:36], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate popular realistic gesture print tests with RealVisXL.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061331)
    parser.add_argument("--steps", type=int, default=22)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=420)
    parser.add_argument("--prompt-timeout", type=int, default=1200)
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--regenerate-existing", action="store_true")
    parser.add_argument("--only", default="", help="Comma-separated 1-based indexes to generate, for example 2,4,6.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comfy_print_batch.CHECKPOINT = REALVIS
    specs = build_specs()
    only_indexes = None
    if args.only.strip():
        only_indexes = {int(part.strip()) for part in args.only.split(",") if part.strip()}
    output_dir = ROOT / "印花图_透明底" / f"热门写实手势印花测试_{args.date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    notes = ROOT / "生成提示词" / f"热门写实手势印花测试_{args.date}.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(
        "\n".join(f"{idx + 1}. {spec.title}: {spec.description}\n   prompt: {spec.prompt}" for idx, spec in enumerate(specs)) + "\n",
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
        for index, spec in enumerate(specs):
            final = output_dir / f"{index + 1:02d}_{spec.key}.png"
            if only_indexes is not None and index + 1 not in only_indexes:
                if final.exists():
                    paths.append(final)
                continue
            if final.exists() and not args.regenerate_existing:
                print(f"reuse {final}")
                paths.append(final)
                continue
            workflow = make_workflow(spec.prompt, args.seed + index * 9973, args.steps, args.width, args.height)
            prompt_id = queue_prompt(workflow)
            print(f"queued {index + 1}: {spec.title}")
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"{spec.title}: ComfyUI error: {history.get('status')}")
            copied = copy_outputs(history, output_dir, f"{index + 1:02d}_{spec.key}", args.bg_threshold, args.bg_color_distance, False)
            if len(copied) != 1:
                raise RuntimeError(f"{spec.title}: expected one generated output, got {len(copied)}")
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
