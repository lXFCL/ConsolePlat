from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def make_checker(size: tuple[int, int], tile: int = 32) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    width, height = size
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle([x, y, x + tile - 1, y + tile - 1], fill=(230, 230, 230, 255))
    return image


def create_overview(input_dir: Path, output: Path, thumb_size: int, columns: int) -> None:
    files = sorted(path for path in input_dir.glob("*.png") if path.is_file())
    if not files:
        raise RuntimeError(f"No PNG files found in {input_dir}")

    cards: list[Image.Image] = []
    card_width = thumb_size + 40
    card_height = thumb_size + 78

    for path in files:
        image = Image.open(path).convert("RGBA")
        background = make_checker(image.size)
        background.alpha_composite(image)
        thumb = ImageOps.contain(background.convert("RGB"), (thumb_size, thumb_size), Image.Resampling.LANCZOS)

        card = Image.new("RGB", (card_width, card_height), (250, 250, 248))
        card.paste(thumb, ((card_width - thumb.width) // 2, 18))
        draw = ImageDraw.Draw(card)
        draw.text((14, thumb_size + 32), path.name[:46], fill=(30, 30, 30))
        cards.append(card)

    rows = (len(cards) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * card_width, rows * card_height), (238, 238, 235))
    for index, card in enumerate(cards):
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        sheet.paste(card, (x, y))

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a contact sheet for generated PNG images.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--thumb-size", type=int, default=260)
    parser.add_argument("--columns", type=int, default=5)
    args = parser.parse_args()

    output = args.output or args.input_dir / "_overview.jpg"
    create_overview(args.input_dir, output, args.thumb_size, args.columns)
    print(output)


if __name__ == "__main__":
    main()
