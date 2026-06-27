from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u590d\u53e4\u50cf\u7d20\u6e38\u620f\u98ce_\u65e0\u6846_5\u6b3e_2026-06-15"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

GRID = 128
CANVAS = 1024
SCALE = CANVAS // GRID

TRANSPARENT = (0, 0, 0, 0)
INK = (20, 19, 24, 255)
OUTLINE = (250, 241, 203, 255)
WHITE = (255, 248, 222, 255)
RED = (218, 57, 47, 255)
ORANGE = (241, 122, 39, 255)
YELLOW = (255, 210, 72, 255)
BLUE = (69, 138, 224, 255)
CYAN = (91, 221, 228, 255)
GREEN = (82, 196, 93, 255)
PURPLE = (140, 91, 215, 255)
PINK = (236, 96, 165, 255)
BROWN = (120, 73, 40, 255)
TAN = (218, 162, 91, 255)
GRAY = (101, 104, 113, 255)
DARK_BLUE = (31, 47, 108, 255)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


class PixelCanvas:
    def __init__(self) -> None:
        self.image = Image.new("RGBA", (GRID, GRID), TRANSPARENT)
        self.draw = ImageDraw.Draw(self.image)

    def rect(self, x: int, y: int, w: int, h: int, fill: tuple[int, int, int, int]) -> None:
        self.draw.rectangle((x, y, x + w - 1, y + h - 1), fill=fill)

    def rows(
        self,
        rows: list[str],
        x: int,
        y: int,
        palette: dict[str, tuple[int, int, int, int]],
        cell: int = 2,
    ) -> None:
        for row_index, row in enumerate(rows):
            for column_index, key in enumerate(row):
                if key == ".":
                    continue
                self.rect(x + column_index * cell, y + row_index * cell, cell, cell, palette[key])

    def text(self, text: str, y: int, fill: tuple[int, int, int, int] = WHITE) -> None:
        draft = self.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(draft)
        fnt = font(94 if len(text) <= 6 else 78)
        bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=12)
        x = (CANVAS - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, font=fnt, fill=fill, stroke_width=12, stroke_fill=INK)
        self.image = draft.resize((GRID, GRID), Image.Resampling.NEAREST)
        self.draw = ImageDraw.Draw(self.image)

    def save(self, path: Path) -> None:
        scaled = self.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
        scaled.save(path)


def add_badge_glow(canvas: PixelCanvas, color: tuple[int, int, int, int]) -> None:
    accent_pixels = [
        (24, 20, 4, 4), (96, 24, 5, 5), (18, 48, 3, 3), (105, 55, 4, 4),
        (31, 91, 5, 5), (91, 94, 3, 3), (44, 106, 4, 4), (80, 16, 3, 3),
    ]
    for x, y, w, h in accent_pixels:
        canvas.rect(x, y, w, h, color)
    canvas.rect(27, 33, 3, 3, WHITE)
    canvas.rect(99, 82, 3, 3, WHITE)


def fire_sword() -> Image.Image:
    c = PixelCanvas()
    add_badge_glow(c, ORANGE)
    for dx, dy, col in [
        (51, 17, RED), (47, 23, ORANGE), (56, 23, ORANGE), (43, 30, YELLOW),
        (52, 31, RED), (61, 31, YELLOW), (47, 39, ORANGE), (56, 40, YELLOW),
        (52, 49, RED),
    ]:
        c.rect(dx, dy, 8, 8, col)
    c.rect(59, 35, 8, 38, OUTLINE)
    c.rect(63, 31, 4, 44, WHITE)
    c.rect(67, 39, 6, 30, CYAN)
    c.rect(55, 71, 22, 6, INK)
    c.rect(60, 77, 11, 18, BROWN)
    c.rect(57, 94, 17, 7, YELLOW)
    c.text("FIRE", 826, YELLOW)
    return c.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)


def tiny_wizard() -> Image.Image:
    c = PixelCanvas()
    add_badge_glow(c, PURPLE)
    rows = [
        "........pppp........",
        ".......pppppp.......",
        "......pppwwppp......",
        ".....pppppppppp.....",
        "....pppppppppppp....",
        "......tttttttt......",
        ".....ttiiiiiiit.....",
        "....ttiwiiiiwit....",
        "....ttiiiyiiiiit....",
        ".....ttiiiiiiit.....",
        "......bbbbbbbb......",
        ".....bbbppppbbb.....",
        "....bbbppppppbbb....",
        "...bbbppppppppbbb...",
        "..bbbpppccccpppbbb..",
        ".....pppccccppp.....",
    ]
    c.rows(rows, 43, 24, {"p": PURPLE, "w": WHITE, "t": TAN, "i": INK, "y": YELLOW, "b": DARK_BLUE, "c": CYAN}, 2)
    c.rect(33, 45, 8, 8, YELLOW)
    c.rect(85, 40, 8, 8, CYAN)
    c.rect(89, 48, 6, 6, WHITE)
    c.rect(29, 54, 5, 5, WHITE)
    c.rect(96, 61, 5, 5, YELLOW)
    c.text("MAGE", 826, CYAN)
    return c.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)


def retro_racer() -> Image.Image:
    c = PixelCanvas()
    add_badge_glow(c, CYAN)
    c.rect(29, 71, 70, 8, INK)
    c.rect(33, 58, 61, 17, RED)
    c.rect(41, 48, 38, 13, ORANGE)
    c.rect(51, 40, 20, 10, WHITE)
    c.rect(78, 61, 14, 8, YELLOW)
    c.rect(23, 66, 13, 7, CYAN)
    c.rect(36, 75, 15, 15, INK)
    c.rect(40, 79, 7, 7, GRAY)
    c.rect(77, 75, 15, 15, INK)
    c.rect(81, 79, 7, 7, GRAY)
    for x in (25, 38, 86, 99):
        c.rect(x, 96, 8, 3, WHITE)
    c.rect(20, 51, 11, 4, CYAN)
    c.rect(16, 58, 8, 4, CYAN)
    c.text("TURBO", 826, ORANGE)
    return c.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)


def space_invader() -> Image.Image:
    c = PixelCanvas()
    add_badge_glow(c, GREEN)
    rows = [
        "..gg......gg..",
        "...gg....gg...",
        "..gggggggggg..",
        ".ggwwggggwwgg.",
        "gggggggggggggg",
        "gg..gggggg..gg",
        "gg..gg..gg..gg",
        "...gg....gg...",
        "..gg..gg..gg..",
        ".gg........gg.",
    ]
    c.rows(rows, 36, 29, {"g": GREEN, "w": WHITE}, 4)
    c.rect(29, 80, 8, 5, CYAN)
    c.rect(45, 88, 7, 4, YELLOW)
    c.rect(71, 84, 8, 5, PINK)
    c.rect(92, 91, 7, 4, WHITE)
    c.text("ALIEN", 826, GREEN)
    return c.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)


def loot_chest() -> Image.Image:
    c = PixelCanvas()
    add_badge_glow(c, YELLOW)
    c.rect(34, 45, 61, 12, BROWN)
    c.rect(28, 56, 73, 35, TAN)
    c.rect(28, 56, 73, 8, YELLOW)
    c.rect(56, 49, 17, 42, INK)
    c.rect(60, 61, 9, 11, YELLOW)
    c.rect(33, 68, 17, 13, BROWN)
    c.rect(78, 68, 17, 13, BROWN)
    c.rect(42, 33, 5, 5, WHITE)
    c.rect(81, 28, 8, 8, CYAN)
    c.rect(93, 39, 5, 5, YELLOW)
    c.rect(72, 31, 4, 4, PINK)
    c.rect(55, 22, 6, 6, WHITE)
    c.text("LOOT", 826, YELLOW)
    return c.image.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)


def make_checker(size: tuple[int, int], tile: int = 32) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    width, height = size
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(230, 230, 230, 255))
    return image


def create_overview(paths: list[Path]) -> None:
    thumb_size = 260
    card_width = thumb_size + 40
    card_height = thumb_size + 78
    cards: list[Image.Image] = []
    for path in paths:
        image = Image.open(path).convert("RGBA")
        checker = make_checker(image.size)
        checker.alpha_composite(image)
        thumb = ImageOps.contain(checker.convert("RGB"), (thumb_size, thumb_size), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (card_width, card_height), (250, 250, 248))
        card.paste(thumb, ((card_width - thumb.width) // 2, 18))
        draw = ImageDraw.Draw(card)
        draw.text((14, thumb_size + 32), path.name, fill=(30, 30, 30))
        cards.append(card)

    sheet = Image.new("RGB", (len(cards) * card_width, card_height), (238, 238, 235))
    for index, card in enumerate(cards):
        sheet.paste(card, (index * card_width, 0))
    sheet.save(OVERVIEW, quality=92)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prints = [
        ("retro_pixel_01_fire_sword.png", fire_sword()),
        ("retro_pixel_02_tiny_wizard.png", tiny_wizard()),
        ("retro_pixel_03_turbo_racer.png", retro_racer()),
        ("retro_pixel_04_space_invader.png", space_invader()),
        ("retro_pixel_05_loot_chest.png", loot_chest()),
    ]
    paths: list[Path] = []
    for name, image in prints:
        path = OUTPUT_DIR / name
        image.save(path)
        paths.append(path)
    create_overview(paths)
    for path in paths:
        print(path)
    print(OVERVIEW)


if __name__ == "__main__":
    main()
