from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    from tshirt_print_tool import Placement, composite_one, list_images
except ModuleNotFoundError:
    from tools.tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = Path(r"C:\Users\Administrator\.codex\generated_images\019ed4d6-f333-7c53-9c71-9bed4d22290f")
OLD_DIRS = [
    ROOT / "图库" / "通用素材" / "2026" / "6月" / "线条小狗_5款_20260617" / "最终透明底",
    ROOT / "图库" / "通用素材" / "2026" / "6月" / "线条小狗生活动作_5款_20260617" / "最终透明底",
]
MODEL_DIR = ROOT / "模特图-干净"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
FONT_DIR = Path(r"C:\Windows\Fonts")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
STORE_NAME = "YUHAOBO"
STYLE_NAME = "韩系线条小狗印花"

SELLING_POINTS = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]


@dataclass(frozen=True)
class DogSpec:
    slug: str
    keyword: str
    korean: str
    source: Path | None = None


@dataclass(frozen=True)
class Paths:
    print_dir: Path
    raw_dir: Path
    mockup_dir: Path
    mockup_test_dir: Path
    prompt_file: Path
    xlsx_path: Path


@dataclass(frozen=True)
class PrintItem:
    sku: str
    spec: DogSpec
    print_path: Path


BASE_SPECS: list[DogSpec] = [
    DogSpec("head-tilt", "歪头小狗", "나 안아..."),
    DogSpec("lying", "趴趴小狗", "쉬는 중"),
    DogSpec("paws-up", "举爪小狗", "안녕!"),
    DogSpec("running", "奔跑小狗", "달려!"),
    DogSpec("wave", "招手小狗", "여기 봐"),
    DogSpec("guitar", "弹吉他小狗", "띵가띵가"),
    DogSpec("drink-cup", "喝水小狗", "물 한잔"),
    DogSpec("reading", "读书小狗", "책 좋아"),
    DogSpec("painting", "画画小狗", "그리는 중"),
    DogSpec("hug-heart", "抱心小狗", "좋아해"),
    DogSpec("cooking", "煎锅小狗", "맛있다"),
    DogSpec("noodles", "吃面小狗", "후루룩"),
    DogSpec("umbrella", "雨伞小狗", "비 와요"),
    DogSpec("skateboard", "滑板小狗", "씽씽"),
    DogSpec("camera", "拍照小狗", "찰칵"),
    DogSpec("headphones-dance", "耳机小狗", "둠칫"),
    DogSpec("watering-plant", "浇花小狗", "쑥쑥"),
    DogSpec("pillow-sleep", "抱枕小狗", "잘 자"),
    DogSpec("toothbrush", "刷牙小狗", "양치중"),
    DogSpec("balloon", "气球小狗", "둥실"),
    DogSpec("backpack", "背包小狗", "산책 가자"),
    DogSpec("laptop", "电脑小狗", "집중"),
    DogSpec("drum", "打鼓小狗", "쿵쿵"),
    DogSpec("bicycle", "骑车小狗", "바람 좋아"),
    DogSpec("fishing", "钓鱼小狗", "기다려"),
    DogSpec("dumbbell", "举哑铃小狗", "힘내"),
    DogSpec("telescope", "望远镜小狗", "별 보자"),
    DogSpec("gift-box", "礼物小狗", "선물!"),
    DogSpec("broom", "扫地小狗", "청소중"),
    DogSpec("ice-cream", "冰淇淋小狗", "달콤해"),
    DogSpec("soccer", "足球小狗", "슛!"),
    DogSpec("magic-wand", "魔法棒小狗", "반짝"),
    DogSpec("kite", "风筝小狗", "높이"),
    DogSpec("baking", "烘焙小狗", "빵 굽기"),
    DogSpec("skiing", "滑雪小狗", "눈 좋아"),
    DogSpec("surfing", "冲浪小狗", "파도 타자"),
    DogSpec("phone", "打电话小狗", "여보세요"),
    DogSpec("flower", "拿花小狗", "꽃 줄게"),
    DogSpec("bubble-bath", "泡澡小狗", "뽀송"),
    DogSpec("toy-car", "开车小狗", "부릉"),
    DogSpec("yoga", "瑜伽小狗", "후우"),
    DogSpec("lantern", "提灯小狗", "따뜻해"),
    DogSpec("cupcake", "纸杯糕小狗", "축하해"),
    DogSpec("shopping-bag", "购物袋小狗", "장보는 중"),
    DogSpec("mirror-brush", "照镜小狗", "예쁘다"),
    DogSpec("mail", "送信小狗", "편지 왔어"),
    DogSpec("puddle", "水坑小狗", "첨벙"),
    DogSpec("star", "抱星小狗", "내 별"),
    DogSpec("baseball", "棒球小狗", "홈런"),
    DogSpec("teddy", "抱玩偶小狗", "꼬옥"),
]


def batch_name(start: int, count: int, stamp: str) -> str:
    end = start + count - 1
    return f"{STYLE_NAME}_BO-{start}-BO-{end}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> Paths:
    name = batch_name(start, count, stamp)
    year, month = stamp.split("-")[0], f"{int(stamp.split('-')[1])}月"
    gallery_batch = ROOT / "图库" / "BO" / year / month / name
    mockup_batch = ROOT / "批量贴图结果" / "BO" / year / month / name
    return Paths(
        print_dir=gallery_batch / "最终透明底",
        raw_dir=gallery_batch / "测试",
        mockup_dir=mockup_batch / "最终产品图",
        mockup_test_dir=mockup_batch / "测试",
        prompt_file=ROOT / "生成提示词" / f"{name}.txt",
        xlsx_path=ROOT / "衣物对应的xlsx" / "BO" / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def load_korean_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("malgun.ttf", "malgunbd.ttf", "Inkfree.ttf", "comic.ttf"):
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def white_to_alpha(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    value = np.mean(rgb, axis=2)
    transparent = (value >= 218) & (spread < 22)
    soft = (value >= 178) & (value < 218) & (spread < 32)
    alpha = arr[..., 3].astype(np.float32)
    alpha[transparent] = 0
    alpha[soft] = np.clip((218 - value[soft]) * 6.4, 0, 255)
    arr[..., :3] = 0
    arr[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def trim_alpha(img: Image.Image, padding: int = 28) -> Image.Image:
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return img
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(img.width, bbox[2] + padding)
    bottom = min(img.height, bbox[3] + padding)
    return img.crop((left, top, right, bottom))


def draw_rotated_text(canvas: Image.Image, xy: tuple[int, int], text: str, size: int, angle: float) -> None:
    font = load_korean_font(size)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    w = bbox[2] - bbox[0] + 28
    h = bbox[3] - bbox[1] + 24
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((14 - bbox[0], 10 - bbox[1]), text, font=font, fill=(0, 0, 0, 255), stroke_width=1, stroke_fill=(0, 0, 0, 120))
    layer = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    canvas.alpha_composite(layer, xy)


def make_print_panel(subject: Image.Image, korean: str, index: int) -> Image.Image:
    subject = trim_alpha(subject, padding=20)
    canvas_size = 1400
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    max_w, max_h = 840, 880
    subject.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    x = (canvas_size - subject.width) // 2
    y = int(canvas_size * 0.26)
    if subject.height > 780:
        y = int(canvas_size * 0.22)
    canvas.alpha_composite(subject, (x, y))

    rng = random.Random(2026061704 + index)
    parts = korean.split(" ", 1)
    first = parts[0]
    second = parts[1] if len(parts) > 1 else ""
    base_y = max(70, y - 132)
    draw_rotated_text(canvas, (max(120, x + rng.randint(-30, 30)), base_y), first, rng.randint(82, 96), rng.uniform(-4.5, 3.0))
    if second:
        draw_rotated_text(canvas, (min(900, x + 250 + rng.randint(-24, 30)), base_y + rng.randint(-12, 22)), second, rng.randint(76, 90), rng.uniform(-3.5, 4.0))
    elif len(korean) <= 4:
        draw_rotated_text(canvas, (min(940, x + 330 + rng.randint(-18, 28)), base_y + rng.randint(0, 28)), "..", rng.randint(72, 86), rng.uniform(-2.5, 3.5))

    return trim_alpha(canvas, padding=36)


def collect_sources(paths: Paths) -> list[DogSpec]:
    old_files: list[Path] = []
    for folder in OLD_DIRS:
        old_files.extend(sorted(folder.glob("*.png")))
    old_by_slug = {p.stem.replace("line-dog-", ""): p for p in old_files}

    raw_backup = paths.raw_dir / "白底原图"
    raw_backup.mkdir(parents=True, exist_ok=True)
    latest_new = sorted(GENERATED_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)[-40:]
    if len(latest_new) != 40:
        raise RuntimeError(f"Expected 40 newly generated images, found {len(latest_new)}")

    specs: list[DogSpec] = []
    for index, spec in enumerate(BASE_SPECS[:50]):
        if index < 10:
            src = old_by_slug.get(spec.slug)
            if src is None:
                raise FileNotFoundError(f"Missing existing source for {spec.slug}")
            specs.append(DogSpec(spec.slug, spec.keyword, spec.korean, src))
        else:
            src = latest_new[index - 10]
            backup = raw_backup / f"{index + 1:02d}_{spec.slug}.png"
            shutil.copy2(src, backup)
            specs.append(DogSpec(spec.slug, spec.keyword, spec.korean, backup))
    return specs


def prepare_prints(start: int, count: int, paths: Paths) -> list[PrintItem]:
    if count != 50:
        raise ValueError("This formal line-dog batch is fixed to 50 prints.")
    specs = collect_sources(paths)
    paths.print_dir.mkdir(parents=True, exist_ok=True)
    items: list[PrintItem] = []
    lines = [
        batch_name(start, count, date.today().isoformat()),
        "imgGen 生成线条小狗主体；本地后处理去白底并添加真实韩文手写风文字。",
        "韩文为真实文本叠加，避免模型伪字；最终透明 PNG 按 BO 货号命名。",
        "",
    ]
    for index, spec in enumerate(specs):
        sku = f"BO-{start + index}"
        assert spec.source is not None
        if index < 10:
            subject = ImageOps.exif_transpose(Image.open(spec.source)).convert("RGBA")
        else:
            subject = white_to_alpha(spec.source)
        final = make_print_panel(subject, spec.korean, index)
        output = paths.print_dir / f"{sku}.png"
        final.save(output)
        items.append(PrintItem(sku=sku, spec=spec, print_path=output))
        lines.append(f"{sku}\t{spec.keyword}\t{spec.korean}\t{spec.source}")
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    paths.prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    make_transparent_overview([item.print_path for item in items], paths.raw_dir / "透明底总览.jpg")
    return items


def shirt_color(model_path: Path) -> tuple[str, str]:
    if "白" in model_path.stem:
        return "白色", "白"
    if "黑" in model_path.stem:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def product_title(color_word: str, keyword: str, index: int) -> str:
    suffix = SELLING_POINTS[index % len(SELLING_POINTS)]
    return f"夏季{color_word}韩系线条小狗{keyword}印花T恤 {suffix}"


def make_transparent_overview(paths_to_images: list[Path], output: Path, cols: int = 10) -> None:
    tile_w, tile_h = 220, 270
    rows = max(1, math.ceil(len(paths_to_images) / cols))
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (245, 245, 245))
    try:
        font = ImageFont.truetype(str(FONT_DIR / "msyh.ttc"), 12)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths_to_images):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if bbox:
            img = img.crop(bbox)
        img.thumbnail((200, 210), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        d = ImageDraw.Draw(tile)
        for y in range(0, 220, 18):
            for x in range(0, tile_w, 18):
                fill = (235, 235, 235) if ((x // 18 + y // 18) % 2 == 0) else (255, 255, 255)
                d.rectangle((x, y, x + 17, y + 17), fill=fill)
        tile.paste(img, ((tile_w - img.width) // 2, (220 - img.height) // 2), img)
        d.text((6, 230), path.stem[:28], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def make_product_overview(paths_to_images: list[Path], output: Path, cols: int = 10) -> None:
    tile_w, tile_h = 250, 320
    rows = max(1, math.ceil(len(paths_to_images) / cols))
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype(str(FONT_DIR / "msyh.ttc"), 12)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths_to_images):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((230, 260), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 6))
        ImageDraw.Draw(tile).text((6, 274), path.stem[:30], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def make_products(items: list[PrintItem], paths: Paths, seed: int) -> list[Path]:
    models = [p for p in list_images(MODEL_DIR) if "白" in p.stem]
    if not models:
        raise FileNotFoundError(f"No white model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(
        center_x=0.50,
        center_y=0.49,
        width=0.22,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.20,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    paths.mockup_dir.mkdir(parents=True, exist_ok=True)
    paths.mockup_test_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, item in enumerate(items):
        model = rng.choice(models)
        color_word, _ = shirt_color(model)
        title = product_title(color_word, item.spec.keyword, index)
        output = paths.mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model, item.print_path, output, placement)
        outputs.append(output)
    make_product_overview(outputs, paths.mockup_test_dir / "_overview.jpg")
    return outputs


def validate_placement_geometry(paths: Paths, base_size: tuple[int, int] = (1350, 1800)) -> dict:
    min_top = 520
    max_bottom = 1385
    width = 0.22
    center_y = 0.49
    rows = []
    for path in sorted(paths.print_dir.glob("BO-*.png")):
        img = Image.open(path).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"Empty print alpha: {path}")
        crop_w = bbox[2] - bbox[0]
        crop_h = bbox[3] - bbox[1]
        target_w = int(base_size[0] * width)
        target_h = int(crop_h * (target_w / crop_w))
        top = int(base_size[1] * center_y - target_h / 2)
        bottom = top + target_h
        rows.append((path.name, top, bottom, target_w, target_h))
    too_high = [row for row in rows if row[1] < min_top]
    too_low = [row for row in rows if row[2] > max_bottom]
    summary = {
        "placement_width": width,
        "placement_center_y": center_y,
        "min_top": min(row[1] for row in rows),
        "max_bottom": max(row[2] for row in rows),
        "too_high": too_high[:5],
        "too_low": too_low[:5],
    }
    if too_high or too_low:
        raise RuntimeError(f"Placement geometry validation failed: {summary}")
    return summary


def parse_product_filename(filename: str) -> tuple[str, str, str]:
    match = re.match(r"^(BO-\d+)_(.+)\.png$", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unexpected product filename: {filename}")
    sku, title = match.groups()
    if "白色" in title:
        color = "白"
    elif "黑色" in title:
        color = "黑"
    else:
        color = ""
    return title, sku.upper(), color


def product_rows(paths: Paths) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for path in list_images(paths.mockup_dir):
        if path.name.startswith("_"):
            continue
        title, sku, color = parse_product_filename(path.name)
        rows.append((STORE_NAME, "T恤", title, sku, color))
    return sorted(rows, key=lambda row: int(row[3].split("-")[1]))


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_idx, values in enumerate(rows, 1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:E{len(rows)}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def find_template(output_xlsx: Path) -> Path:
    dirs = [ROOT / "衣物对应的xlsx" / "BO", ROOT / "衣物对应的xlsx" / "简约200"]
    templates: list[Path] = []
    for directory in dirs:
        if directory.exists():
            templates.extend(p for p in directory.glob("*.xlsx") if not p.name.startswith("~$") and p != output_xlsx)
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {dirs}")
    return sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def write_xlsx(paths: Paths, count: int) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *product_rows(paths)]
    if len(rows) != count + 1:
        raise RuntimeError(f"Expected {count + 1} xlsx rows including header, got {len(rows)}")
    paths.xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.xlsx_path.with_suffix(".tmp.xlsx")
    shutil.copy2(find_template(paths.xlsx_path), tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(paths.xlsx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = build_sheet_xml(rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename)
            dst.writestr(info, data)
    tmp.unlink(missing_ok=True)


def sku_numbers(files: list[Path]) -> list[int]:
    values = []
    for path in files:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs(start: int, count: int, paths: Paths) -> dict:
    expected = list(range(start, start + count))
    print_files = sorted(p for p in list_images(paths.print_dir) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    product_files = sorted(p for p in list_images(paths.mockup_dir) if p.name.startswith("BO-"))
    rows = product_rows(paths)
    transparency = []
    corners_ok = []
    for path in print_files:
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        transparency.append(alpha.getextrema()[0] == 0 and alpha.getextrema()[1] == 255)
        corners_ok.append(all(img.getpixel(pos)[3] == 0 for pos in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]))
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_skus": sku_numbers(print_files),
        "product_skus": sku_numbers(product_files),
        "transparent_pngs_ok": all(transparency),
        "transparent_corners_ok": all(corners_ok),
        "xlsx_exists": paths.xlsx_path.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "store_names": sorted({row[0] for row in rows}),
        "overview_exists": (paths.mockup_test_dir / "_overview.jpg").exists(),
        "placement_geometry": validate_placement_geometry(paths),
    }
    if len(print_files) != count or len(product_files) != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if summary["print_skus"] != expected or summary["product_skus"] != expected:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not summary["transparent_pngs_ok"] or not summary["transparent_corners_ok"]:
        raise RuntimeError(f"Transparency validation failed: {summary}")
    if not paths.xlsx_path.exists() or len(rows) != count or summary["store_names"] != [STORE_NAME]:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    if summary["xlsx_first_sku"] != f"BO-{start}" or summary["xlsx_last_sku"] != f"BO-{start + count - 1}":
        raise RuntimeError(f"XLSX SKU range failed: {summary}")
    return summary


def sync_putaway(paths: Paths) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(paths.mockup_dir):
        if path.name.startswith("BO-"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.xlsx_path, PUTAWAY_DATA_DIR / paths.xlsx_path.name)


def validate_putaway(start: int, count: int, paths: Paths) -> dict:
    expected = list(range(start, start + count))
    files = [p for p in list_images(PUTAWAY_PIC_DIR) if p.name.startswith("BO-")]
    skus = sku_numbers(files)
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": skus,
        "putaway_range_ok": skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / paths.xlsx_path.name).exists(),
    }
    if len(files) != count or skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_bo_progress(start: int, count: int, paths: Paths, validation: dict, putaway: dict, stamp: str) -> None:
    end = start + count - 1
    next_start = end + 1
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到：\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从：\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张韩系线条小狗印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{paths.print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在，四角透明；小狗旁韩文为本地真实文本叠加。\n"
        f"- `{paths.mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；贴图位置为胸前正中，白色主图优先以保证黑线印花可见。\n"
        f"- `{paths.xlsx_path}` 当前校验为 {count + 1} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}，店铺名称为 YUHAOBO。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg` 和透明底总览；需人工确认个别道具动作识别度以及韩文位置是否都接近参考图的松散手写感。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Formalize BO Korean line-dog imgGen batch.")
    parser.add_argument("--start", type=int, default=1471)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--stamp", default=date.today().isoformat())
    parser.add_argument("--mockup-seed", type=int, default=2026061704)
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-progress", action="store_true")
    parser.add_argument("--sync-existing", action="store_true", help="Only sync existing batch outputs and update progress.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = batch_paths(args.start, args.count, args.stamp)
    if args.sync_existing:
        validation = validate_outputs(args.start, args.count, paths)
        sync_putaway(paths)
        putaway = validate_putaway(args.start, args.count, paths)
        if not args.skip_progress:
            update_bo_progress(args.start, args.count, paths, validation, putaway, args.stamp)
        products = list_images(paths.mockup_dir)
    else:
        items = prepare_prints(args.start, args.count, paths)
        products = make_products(items, paths, args.mockup_seed)
        write_xlsx(paths, args.count)
        validation = validate_outputs(args.start, args.count, paths)
        putaway = {}
        if not args.skip_sync:
            sync_putaway(paths)
            putaway = validate_putaway(args.start, args.count, paths)
        if not args.skip_progress and putaway:
            update_bo_progress(args.start, args.count, paths, validation, putaway, args.stamp)
    print(json.dumps({
        "batch": batch_name(args.start, args.count, args.stamp),
        "print_dir": str(paths.print_dir),
        "raw_dir": str(paths.raw_dir),
        "mockup_dir": str(paths.mockup_dir),
        "xlsx": str(paths.xlsx_path),
        "prompt": str(paths.prompt_file),
        "product_count": len([p for p in products if p.name.startswith("BO-")]),
        "validation": validation,
        "putaway": putaway,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
