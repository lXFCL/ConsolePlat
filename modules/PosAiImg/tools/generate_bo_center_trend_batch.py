from __future__ import annotations

import argparse
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_bo_commercial_trend_batch as sheet  # noqa: E402
import render_center_style_tests as center  # noqa: E402
import render_right_chest_style_tests as util  # noqa: E402
from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"

STYLE_TITLES = {
    "loud_vintage": ["复古大字报", "强视觉字标", "旧海报字标", "星芒色块", "午夜俱乐部"],
    "varsity_sport": ["复古校队86", "运动校队23", "田径数字07", "本地球队14", "校队徽章99"],
    "handmade_doodle": ["手绘笑脸", "咖啡涂鸦", "梦境涂鸦", "你好笑脸", "低保真涂鸦"],
    "rubber_food": ["披萨卡通", "咖啡卡通", "辣椒卡通", "甜甜圈卡通", "汉堡卡通"],
    "tattoo_flash": ["爱心闪图", "樱桃闪图", "匕首闪图", "火焰闪图", "幸运星标"],
    "outdoor_badge": ["山野步道", "露营山线", "山脊日落", "湖畔山景", "公路远山"],
    "animal_graphic": ["豹纹图形", "斑马纹图形", "虎纹图形", "奶牛纹图形", "野性斑点"],
    "y2k_signal": ["信号故障", "错误电码", "控制电码", "虚空电码", "字节故障"],
}

ACCENTS = [util.RED, util.BLUE, util.GREEN, util.GOLD, util.PINK, util.CYAN]


@dataclass(frozen=True)
class BatchItem:
    sku: str
    style: center.CenterStyle
    variant_index: int
    cycle: int
    title_word: str


def batch_name(start: int, count: int, batch_date: str | None = None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"中间潮流印花_BO-{start}-BO-{end}_{stamp}"


def configure_paths(start: int, count: int, batch_date: str | None = None) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, batch_date)
    print_dir = ROOT / "印花图_透明底" / name
    mockup_dir = ROOT / "批量贴图结果" / f"{name}_随机主图{count}"
    prompt_file = ROOT / "生成提示词" / f"{name}.txt"
    output_xlsx = TEMPLATE_DIR / f"{name}.xlsx"
    sheet.PRINT_DIR = print_dir
    sheet.MOCKUP_DIR = mockup_dir
    sheet.PROMPT_FILE = prompt_file
    sheet.OUTPUT_XLSX = output_xlsx
    sheet.TEMPLATE_DIR = TEMPLATE_DIR
    return print_dir, mockup_dir, prompt_file, output_xlsx


def sku_for(start: int, index: int) -> str:
    return f"BO-{start + index}"


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def build_items(start: int, count: int) -> list[BatchItem]:
    styles = center.STYLES
    seen: dict[str, int] = {style.key: 0 for style in styles}
    items: list[BatchItem] = []
    for index in range(count):
        style = styles[index % len(styles)]
        style_seq = seen[style.key]
        seen[style.key] += 1
        variant_index = style_seq % 5
        cycle = style_seq // 5
        base_title = STYLE_TITLES[style.key][variant_index]
        title_word = base_title if cycle == 0 else f"{base_title}{cycle + 1}版"
        items.append(BatchItem(sku_for(start, index), style, variant_index, cycle, title_word))
    return items


def add_variant_marks(path: Path, item_index: int, cycle: int) -> None:
    img = Image.open(path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    color = ACCENTS[item_index % len(ACCENTS)]
    x0 = max(18, img.width - 118)
    y0 = 18
    for offset in range(3):
        r = 10 + (cycle * 2)
        x = x0 + offset * 34
        y = y0 + (item_index % 4) * 4
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=util.BLACK, width=3)
    img.save(path)


def render_prints(items: list[BatchItem], print_dir: Path) -> list[Path]:
    print_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, item in enumerate(items):
        path = print_dir / f"{item.sku}.png"
        center.render_print(item.style, item.variant_index, path)
        add_variant_marks(path, index, item.cycle)
        paths.append(path)
        print(f"{item.sku}: print {item.style.zh} / {item.title_word}")
    return paths


def title_for(color_word: str, item: BatchItem, index: int) -> str:
    suffix = sheet.SELLING_POINTS[index % len(sheet.SELLING_POINTS)]
    return f"夏季{color_word}{item.style.zh}{item.title_word}印花T恤 {suffix}"


def make_mockups(items: list[BatchItem], print_dir: Path, mockup_dir: Path, seed: int) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.97,
        rotation=0.0,
        shadow_strength=0.22,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    output_paths: list[Path] = []
    for index, item in enumerate(items):
        print_path = print_dir / f"{item.sku}.png"
        model_path = rng.choice(models)
        color_word, _ = sheet.shirt_color(model_path)
        title = title_for(color_word, item, index)
        output_path = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        output_paths.append(output_path)
        print(f"{item.sku}: mockup {output_path.name}")
    return output_paths


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 230, 310
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet_img = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((210, 245), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:30], fill=(0, 0, 0))
        sheet_img.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_img.save(output_path, quality=92)


def write_prompt_file(items: list[BatchItem], prompt_file: Path) -> None:
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "中间胸前潮流印花正式批次。",
        "来源：上一轮中间印花风格测试，包含大字报复古、复古运动、手绘涂鸦、复古卡通食物、Tattoo Flash、户外山野、动物纹、Y2K 电码。",
        "要求：原创、无真实品牌、无版权角色、无明星球队、透明底、适合黑白 T 恤居中胸前贴图。",
        "",
    ]
    lines.extend(f"{item.sku}: {item.style.zh} / {item.title_word}" for item in items)
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO center trend print batch, mockups, and xlsx.")
    parser.add_argument("--start", type=int, default=706)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=2026061250)
    parser.add_argument("--date", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_dir, mockup_dir, prompt_file, output_xlsx = configure_paths(args.start, args.count, args.date)
    items = build_items(args.start, args.count)
    started = time.time()
    write_prompt_file(items, prompt_file)
    render_prints(items, print_dir)
    mockups = make_mockups(items, print_dir, mockup_dir, args.seed)
    make_overview(mockups, mockup_dir / "_overview.jpg")
    sheet.write_xlsx_from_filenames(mockup_dir, args.count)
    sheet.validate_outputs(args.start, args.count)
    print(f"Prompt file: {prompt_file}")
    print(f"Print dir: {print_dir}")
    print(f"Product dir: {mockup_dir}")
    print(f"XLSX: {output_xlsx}")
    print(f"Elapsed seconds: {time.time() - started:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
