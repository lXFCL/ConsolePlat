from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
PRINT_DIR = ROOT / "印花图_透明底" / "高街黑白灰写实素描_5张测试_v2_2026-06-13"
MODEL_DIR = ROOT / "模特图-干净"
OUTPUT_DIR = ROOT / "AI印花贴图测试" / "高街黑白灰写实素描_黑白各5_2026-06-13"


def pick_models() -> tuple[list[Path], list[Path]]:
    models = list_images(MODEL_DIR)
    black = [p for p in models if "黑" in p.stem]
    white = [p for p in models if "白" in p.stem]
    if not black:
        raise FileNotFoundError(f"No black model images found in {MODEL_DIR}")
    if not white:
        raise FileNotFoundError(f"No white model images found in {MODEL_DIR}")
    return black, white


def make_overview(paths: list[Path], target: Path, columns: int = 5) -> None:
    tile_w, tile_h = 360, 520
    rows = (len(paths) + columns - 1) // columns
    overview = Image.new("RGB", (tile_w * columns, tile_h * rows), "white")
    draw = ImageDraw.Draw(overview)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    except OSError:
        font = ImageFont.load_default()

    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((tile_w - 20, tile_h - 58), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_w
        y = (index // columns) * tile_h
        overview.paste(img, (x + (tile_w - img.width) // 2, y + 8))
        label = path.stem[:34]
        draw.text((x + 12, y + tile_h - 42), label, fill=(20, 20, 20), font=font)
    overview.save(target, quality=92)


def main() -> None:
    prints = sorted(p for p in list_images(PRINT_DIR) if not p.name.startswith("_"))[:5]
    if len(prints) != 5:
        raise RuntimeError(f"Expected 5 print images in {PRINT_DIR}, got {len(prints)}")

    black_models, white_models = pick_models()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=True,
    )

    outputs: list[Path] = []
    for index, print_path in enumerate(prints, start=1):
        pairs = [
            ("黑", black_models[(index - 1) % len(black_models)]),
            ("白", white_models[(index - 1) % len(white_models)]),
        ]
        for color, model_path in pairs:
            output_path = OUTPUT_DIR / f"{color}T_{index:02d}_{print_path.stem}.png"
            composite_one(model_path, print_path, output_path, placement)
            outputs.append(output_path)

    black_outputs = [p for p in outputs if p.name.startswith("黑T_")]
    white_outputs = [p for p in outputs if p.name.startswith("白T_")]
    make_overview(black_outputs, OUTPUT_DIR / "_overview_black.jpg", columns=5)
    make_overview(white_outputs, OUTPUT_DIR / "_overview_white.jpg", columns=5)
    make_overview(outputs, OUTPUT_DIR / "_overview_all.jpg", columns=5)

    print(f"Done. Exported {len(outputs)} image(s) to {OUTPUT_DIR}")
    print(f"Black: {len(black_outputs)} White: {len(white_outputs)}")


if __name__ == "__main__":
    main()
