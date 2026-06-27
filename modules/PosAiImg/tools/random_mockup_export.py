from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "模特图-干净"
DEFAULT_PRINT_DIR = ROOT / "印花图_透明底"
DEFAULT_OUTPUT_DIR = ROOT / "批量贴图结果" / "随机贴图结果"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Randomly place print designs on model main images.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--print-dir", type=Path, default=DEFAULT_PRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--center-x", type=float, default=0.50)
    parser.add_argument("--center-y", type=float, default=0.43)
    parser.add_argument("--width", type=float, default=0.31)
    parser.add_argument("--opacity", type=float, default=0.93)
    parser.add_argument("--rotation", type=float, default=0.0)
    parser.add_argument("--shadow-strength", type=float, default=0.34)
    parser.add_argument("--wave-strength", type=float, default=0.010)
    return parser.parse_args()


def make_overview(paths: list[Path], output_path: Path) -> None:
    tiles: list[Image.Image] = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((220, 280), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (240, 320), "white")
        tile.paste(img, ((240 - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 292), path.stem[:30], fill=(0, 0, 0))
        tiles.append(tile)

    if not tiles:
        return
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 240, rows * 320), (235, 235, 235))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % cols) * 240, (index // cols) * 320))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def main() -> int:
    args = parse_args()
    models = list_images(args.model_dir)
    prints = [path for path in list_images(args.print_dir) if not path.name.startswith("_")]
    if not models:
        raise FileNotFoundError(f"No model images found: {args.model_dir}")
    if not prints:
        raise FileNotFoundError(f"No print images found: {args.print_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
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

    exported: list[Path] = []
    for index in range(1, args.count + 1):
        model_path = rng.choice(models)
        print_path = rng.choice(prints)
        output_path = args.output_dir / f"{index:02d}_{model_path.stem}__{print_path.stem}.png"
        composite_one(model_path, print_path, output_path, placement)
        exported.append(output_path)
        print(f"{index:02d}: {model_path.name} + {print_path.name} -> {output_path.name}")

    make_overview(exported, args.output_dir / "_overview.jpg")
    print(f"Done. Exported {len(exported)} image(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
