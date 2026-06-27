from __future__ import annotations

import argparse
import random
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tshirt_print_tool import Placement, composite_one, list_images
from generate_bo_minimal_text_batch import make_overview, safe_filename, shirt_color, write_xlsx_from_mockup_filenames


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PRINT_DIR = ROOT / "印花图_透明底" / "猫咪自然局部改款_修正7_11_14_15张_2026-06-15"
MODEL_DIR = ROOT / "模特图-干净"


@dataclass(frozen=True)
class BatchPaths:
    print_dir: Path
    mockup_dir: Path
    xlsx_path: Path


def batch_paths(start: int, count: int, stamp: str) -> BatchPaths:
    end = start + count - 1
    name = f"猫咪手写韩文印花_BO-{start}-BO-{end}_{stamp}"
    return BatchPaths(
        print_dir=ROOT / "印花图_透明底" / name,
        mockup_dir=ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        xlsx_path=ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def title_for(color_word: str, index: int) -> str:
    suffixes = [
        "圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
        "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
        "圆领短袖 柔软透气针织上衣 夏季日常百搭",
    ]
    return f"夏季{color_word}卡通猫咪韩文印花T恤 {suffixes[index % len(suffixes)]}"


def copy_renamed_prints(source_dir: Path, target_dir: Path, start: int, count: int) -> list[Path]:
    source_files = [path for path in list_images(source_dir) if not path.name.startswith("_")]
    if len(source_files) != count:
        raise RuntimeError(f"Expected {count} source prints, found {len(source_files)} in {source_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for idx, src in enumerate(sorted(source_files), start=0):
        sku = f"BO-{start + idx}"
        dst = target_dir / f"{sku}.png"
        shutil.copy2(src, dst)
        out.append(dst)
    return out


def export_mockups(print_paths: list[Path], mockup_dir: Path, seed: int) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(
        center_x=0.53,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    mockup_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for idx, print_path in enumerate(print_paths):
        model_path = rng.choice(models)
        sku_match = re.match(r"BO-\d+", print_path.stem, re.IGNORECASE)
        if not sku_match:
            raise RuntimeError(f"Print filename does not start with BO sku: {print_path.name}")
        sku = sku_match.group(0).upper()
        color = shirt_color(model_path)
        color_word = "白色" if color == "白" else "黑色"
        title = title_for(color_word, idx)
        output_path = mockup_dir / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        exported.append(output_path)
        print(f"{sku}: {model_path.name} + {print_path.name} -> {output_path.name}")
    make_overview(exported, mockup_dir / "_overview.jpg")
    return exported


def run(start: int, count: int, seed: int, stamp: str) -> BatchPaths:
    paths = batch_paths(start, count, stamp)
    print_paths = copy_renamed_prints(SOURCE_PRINT_DIR, paths.print_dir, start, count)
    mockups = export_mockups(print_paths, paths.mockup_dir, seed)
    if len(mockups) != count:
        raise RuntimeError(f"Expected {count} mockups, exported {len(mockups)}")
    write_xlsx_from_mockup_filenames(paths.mockup_dir, paths.xlsx_path, count)
    print(f"Print dir: {paths.print_dir}")
    print(f"Mockup dir: {paths.mockup_dir}")
    print(f"Xlsx: {paths.xlsx_path}")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Formalize the cat Korean print test set as a BO batch with xlsx.")
    parser.add_argument("--start", type=int, default=1306)
    parser.add_argument("--count", type=int, default=15)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(args.start, args.count, args.seed, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
