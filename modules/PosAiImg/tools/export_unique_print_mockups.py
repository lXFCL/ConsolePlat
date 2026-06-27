from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "模特图-干净"
DEFAULT_PRINT_DIR = ROOT / "印花图_透明底" / "简约艺术字文字印花_200款_2026-06-09"
DEFAULT_OUTPUT_DIR = ROOT / "批量贴图结果" / "简约艺术字文字印花_随机主图200张_2026-06-09"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export mockups with each print used at most once and random model images.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--print-dir", type=Path, default=DEFAULT_PRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--center-x", type=float, default=0.50)
    parser.add_argument("--center-y", type=float, default=0.42)
    parser.add_argument("--width", type=float, default=0.28)
    parser.add_argument("--opacity", type=float, default=0.94)
    parser.add_argument("--rotation", type=float, default=0.0)
    parser.add_argument("--shadow-strength", type=float, default=0.30)
    parser.add_argument("--wave-strength", type=float, default=0.008)
    return parser.parse_args()


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 220, 290
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))

    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((200, 230), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:28], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def main() -> int:
    args = parse_args()
    models = list_images(args.model_dir)
    prints = [path for path in list_images(args.print_dir) if not path.name.startswith("_")]
    if not models:
        raise FileNotFoundError(f"No model images found: {args.model_dir}")
    if len(prints) < args.count:
        raise RuntimeError(f"Need at least {args.count} print images, found {len(prints)} in {args.print_dir}")

    rng = random.Random(args.seed)
    selected_prints = prints[:]
    rng.shuffle(selected_prints)
    selected_prints = selected_prints[: args.count]

    placement = Placement(
        center_x=args.center_x,
        center_y=args.center_y,
        width=args.width,
        opacity=args.opacity,
        rotation=args.rotation,
        shadow_strength=args.shadow_strength,
        wave_strength=args.wave_strength,
        remove_white_bg=False,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for index, print_path in enumerate(selected_prints, start=1):
        model_path = rng.choice(models)
        output_path = args.output_dir / f"{index:03d}_{model_path.stem}__{print_path.stem}.png"
        composite_one(model_path, print_path, output_path, placement)
        exported.append(output_path)
        print(f"{index:03d}: {model_path.name} + {print_path.name} -> {output_path.name}")

    make_overview(exported, args.output_dir / "_overview.jpg")
    print(f"Done. Exported {len(exported)} image(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
