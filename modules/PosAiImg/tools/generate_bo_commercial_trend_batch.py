from __future__ import annotations

import argparse
import random
import re
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comfy_print_batch import (  # noqa: E402
    CHECKPOINT,
    copy_outputs,
    queue_prompt,
    start_comfyui,
    stop_comfyui,
    wait_prompt,
    wait_server,
)
from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "生成提示词"
PRINT_DIR = ROOT / "印花图_透明底" / "商业T恤趋势印花_BO-506-BO-555_2026-06-11"
MOCKUP_DIR = ROOT / "批量贴图结果" / "商业T恤趋势印花_BO-506-BO-555_随机主图50_2026-06-11"
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"
PROMPT_FILE = PROMPT_DIR / "商业T恤趋势印花_BO-506-BO-555_2026-06-11.txt"
OUTPUT_XLSX = TEMPLATE_DIR / "商业T恤趋势印花_BO-506-BO-555_2026-06-11.xlsx"

STORE_NAME = "YUHAOBO"
CATEGORY = "T恤"
HEADERS = ("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")
SELLING_POINTS = (
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
)

ASSET_POSITIVE = (
    "single isolated graphic artwork only, plain white background, centered decal asset, "
    "large solid main motif, bold filled shapes, readable silhouette, visible from a distance, "
    "flat vector illustration, crisp edges, sticker logo style, transparent PNG preparation, "
    "occupies about 35 to 60 percent of the canvas, simple commercial graphic, "
    "high contrast against light and dark backgrounds, not faint, not tiny, not sparse"
)

ASSET_NEGATIVE = (
    "person, human, face, head, body, torso, arms, legs, portrait, model, mannequin, anatomy, skin, "
    "shirt, tee, t-shirt, hoodie, sweater, jacket, pants, dress, skirt, underwear, bikini, clothing, apparel, "
    "garment, collar, sleeve, neckline, wearable object, product mockup, fashion photo, catalog photo, "
    "hanger, folded clothes, fabric texture, chest, waist, shoulders, realistic person, "
    "brand logo, copyrighted character, celebrity, sports team, watermark, signature, messy background, "
    "floor, room, table, shadow, 3d render, frame crop, blank, empty, invisible, faint, pale, outline only, "
    "line art only, sparse, tiny, minimal, near white, washed out"
)


@dataclass(frozen=True)
class DesignSpec:
    theme: str
    title_word: str
    prompt: str


def build_specs() -> list[DesignSpec]:
    outdoor_subjects = [
        ("复古山径日落", "retro sun over pine trail badge, mountain path, hand drawn ink texture"),
        ("露营松林徽章", "campfire pine forest badge, small stars, weathered outdoor club mood"),
        ("湖畔远山", "quiet lake and distant mountain emblem, sunrise reflection, vintage hiking sticker"),
        ("旷野公路", "desert road and low sun badge, western outdoor travel mood, worn screen print"),
        ("森林月光", "moon over dark pine trees, simple trail badge, rustic weekend graphic"),
        ("海岸远行", "coastal road, small wave and setting sun badge, faded surf hiking mood"),
        ("山野俱乐部", "alpine trail club round badge, pine trees, old postcard print feel"),
        ("营地清晨", "morning campsite badge, tent silhouette, soft sun rays, earthy palette"),
        ("峡谷日光", "canyon sun and simple river line, retro national park inspired badge"),
        ("远山慢行", "slow walk mountain badge, layered hills, cream outline and muted red accent"),
    ]
    typography_subjects = [
        ("好日子", 'large imperfect hand lettered words "GOOD DAYS", star dots and underline accents'),
        ("慢慢来", 'large imperfect hand lettered words "TAKE TIME", wavy baseline and tiny spark marks'),
        ("周末模式", 'bold retro words "WEEKEND MODE", playful script mixed with block letters'),
        ("轻松一点", 'large hand lettered words "EASY NOW", soft curves, small corner marks'),
        ("保持温柔", 'expressive words "STAY SOFT", nostalgic graphic tee revival, small flower dots'),
        ("自在呼吸", 'large words "FRESH AIR", casual handwritten type, clean standalone typography decal'),
        ("今天不错", 'large words "NICE DAY", uneven hand lettering, cherry red and navy accents'),
        ("低调日常", 'bold words "LOW KEY", compact vintage layout, dot and slash accents'),
        ("小小快乐", 'large words "SMALL JOY", cute imperfect lettering, simple sun mark'),
        ("放空一会", 'large words "DAY OFF", relaxed hand type, underline and star accents'),
    ]
    botanical_subjects = [
        ("咖啡小花", "small flowers with coffee cup icon, micro polka dots, vintage cafe picnic mood"),
        ("雏菊杯子", "daisy flowers around simple cup icon, dark green and cocoa palette"),
        ("花园早餐", "toast, tiny flowers and dots, soft botanical cafe lifestyle graphic"),
        ("野花便签", "wildflower bouquet with small note shape, delicate vintage print layout"),
        ("柠檬花园", "lemon branch, little blossoms and dot accents, fresh picnic mood"),
        ("周末花束", "casual flower bouquet in simple vase, hand drawn lifestyle graphic"),
        ("奶油玫瑰", "cream rose sprig and tiny stars, balanced soft botanical badge"),
        ("薄荷咖啡", "mint leaves, coffee cup and small dots, warm relaxed cafe graphic"),
        ("夏日小花", "tiny summer flowers and simple oval frame, delicate screen print friendly"),
        ("露台花园", "terrace plant pot, small blossoms and coffee steam, cozy lifestyle emblem"),
    ]
    pattern_subjects = [
        ("斑马条纹", "abstract black white zebra stripe pattern badge mixed with bold cabana club stripes"),
        ("豹纹拼条", "abstract tan black leopard spot pattern badge mixed with vertical cabana stripes"),
        ("热带条纹", "palm leaf brush marks and bold resort stripes, modern streetwear pattern badge"),
        ("海岸条纹", "wave stripe pattern and abstract animal brush marks, refined summer graphic"),
        ("蓝棕拼纹", "sky blue tan black brush stripe collage, modern pattern square badge"),
        ("野性笔触", "abstract wildlife inspired ink marks and geometric dots, cream frame, not literal animal or person"),
        ("度假竖条", "cabana vertical stripes with small sun stamp, clean resort streetwear badge"),
        ("斑点条带", "soft animal spot pattern marks and thick stripe layout, standalone commercial decal"),
        ("都市纹样", "black cream tan geometric brush stripes, modern urban graphic decal"),
        ("沙滩条纹", "beach stripe collage with brush marks, cream tan sky blue palette"),
    ]
    psychedelic_subjects = [
        ("迷幻海浪", "retro 1960s swirling sun and wave motif, electric blue orange pink cream palette"),
        ("日落波纹", "swirling sunset rings and simple wave lines, bold playful poster style"),
        ("夏日漩涡", "psychedelic summer swirl, sunburst, wave and tiny star accents"),
        ("彩色太阳", "radiating sun with wavy retro lines, vivid orange blue pink palette"),
        ("冲浪日光", "surf wave under oversized retro sun, maximalist but centered graphic"),
        ("复古花浪", "psychedelic flower and wave mix, bold clean vector poster style"),
        ("热浪圆徽", "hot summer sun badge with swirling heat lines and wave accents"),
        ("蓝橙海岸", "blue orange coast swirl, retro travel poster style, crisp screen print"),
        ("粉色浪潮", "hot pink wave and sun spiral, bright summer graphic decal"),
        ("阳光派对", "sun party swirl, waves, rays and small stars, playful commercial graphic"),
    ]

    groups = [
        ("复古户外", outdoor_subjects),
        ("复古文字", typography_subjects),
        ("植物咖啡", botanical_subjects),
        ("动物纹条纹", pattern_subjects),
        ("迷幻夏日", psychedelic_subjects),
    ]
    specs: list[DesignSpec] = []
    for group_name, subjects in groups:
        for title_word, subject_prompt in subjects:
            prompt = (
                f"original standalone printable graphic decal, {subject_prompt}, {group_name} style, "
                "single isolated artwork only on plain white background, centered logo-like illustration, "
                "flat vector sticker asset, crisp edges, dark main shapes with cream or white outline, "
                "limited color palette, transparent PNG asset style, no apparel silhouette, no wearable object, "
                "no person, no face, no body, no model, no mannequin, no shirt, no tee, no t-shirt, "
                "no collar, no sleeves, no garment, no clothing, no mockup, no product photo, no brand, "
                "no copyrighted logo, no famous character, no watermark, no background scene"
            )
            specs.append(DesignSpec(group_name, title_word, prompt))
    return specs


def make_asset_workflow(prompt: str, seed: int, steps: int, width: int, height: int) -> dict:
    positive = f"{prompt}, {ASSET_POSITIVE}"
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ASSET_NEGATIVE, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "posai_print", "images": ["8", 0]},
        },
    }


def sku_for(start: int, index: int) -> str:
    return f"BO-{start + index}"


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def shirt_color(model_path: Path) -> tuple[str, str]:
    name = model_path.stem
    if "白" in name:
        return "白色", "白"
    if "黑" in name:
        return "黑色", "黑"

    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def title_for(color_word: str, spec: DesignSpec, index: int) -> str:
    suffix = SELLING_POINTS[index % len(SELLING_POINTS)]
    return f"夏季{color_word}{spec.theme}{spec.title_word}印花T恤 {suffix}"


def find_template_xlsx() -> Path:
    candidates = sorted(
        path for path in TEMPLATE_DIR.glob("*.xlsx")
        if not path.name.startswith("~$")
    )
    if not candidates:
        raise FileNotFoundError(f"No xlsx template found in {TEMPLATE_DIR}")
    return candidates[0]


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml: list[str] = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    dimension = f"A1:E{len(rows)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )


def rows_from_product_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append((STORE_NAME, CATEGORY, title, sku, color))
    rows.sort(key=lambda row: int(row[3].split("-")[1]))
    return rows


def write_xlsx_from_filenames(mockup_dir: Path, expected_count: int) -> None:
    rows_without_header = rows_from_product_filenames(mockup_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} product rows, got {len(rows_without_header)}")

    rows = [HEADERS]
    rows.extend(rows_without_header)
    template = find_template_xlsx()
    OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = OUTPUT_XLSX.with_suffix(".tmp.xlsx")
    shutil.copy2(template, tmp_path)
    with zipfile.ZipFile(tmp_path, "r") as src, zipfile.ZipFile(OUTPUT_XLSX, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp_path.unlink(missing_ok=True)


def write_prompt_file(items: list[tuple[str, DesignSpec]]) -> None:
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "商业T恤趋势印花 50 款，方向包含复古户外、复古文字、植物咖啡、动物纹条纹、迷幻夏日。",
        "要求原创、无品牌、无版权角色、无明星球队、无水印，适合黑白T恤高对比显示。",
        "",
    ]
    lines.extend(f"{sku}: {spec.theme} / {spec.title_word} / {spec.prompt}" for sku, spec in items)
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_prints(items: list[tuple[str, DesignSpec]], args: argparse.Namespace) -> list[Path]:
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    started = None
    if args.auto_start_comfyui:
        started = start_comfyui(args.comfy_timeout)
    else:
        wait_server()

    try:
        output_paths: list[Path] = []
        for index, (sku, spec) in enumerate(items):
            final_path = PRINT_DIR / f"{sku}.png"
            if final_path.exists() and not args.regenerate_existing:
                output_paths.append(final_path)
                print(f"{sku}: reuse {final_path}")
                continue

            workflow = make_asset_workflow(
                spec.prompt,
                args.seed + index * 9973,
                args.steps,
                args.width,
                args.height,
            )
            prompt_id = queue_prompt(workflow)
            print(f"{sku}: queued {spec.theme} / {spec.title_word}")
            history = wait_prompt(prompt_id, timeout_seconds=args.prompt_timeout)
            copied = copy_outputs(
                history,
                PRINT_DIR,
                sku,
                args.bg_threshold,
                args.bg_color_distance,
                keep_raw_comfy_output=False,
            )
            if len(copied) != 1:
                raise RuntimeError(f"{sku}: expected one generated output, got {len(copied)}")
            copied[0].replace(final_path)
            output_paths.append(final_path)
            print(f"{sku}: saved {final_path}")
        return output_paths
    finally:
        if not args.keep_comfyui:
            stop_comfyui(started)


def make_mockups(items: list[tuple[str, DesignSpec]], seed: int) -> list[Path]:
    rng = random.Random(seed)
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")

    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    output_paths: list[Path] = []
    for index, (sku, spec) in enumerate(items):
        print_path = PRINT_DIR / f"{sku}.png"
        if not print_path.exists():
            raise FileNotFoundError(f"Missing print: {print_path}")
        model_path = rng.choice(models)
        color_word, _ = shirt_color(model_path)
        title = title_for(color_word, spec, index)
        output_path = MOCKUP_DIR / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        output_paths.append(output_path)
        print(f"{sku}: mockup {output_path.name}")
    return output_paths


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 230, 310
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((210, 245), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:30], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def validate_outputs(start: int, count: int) -> None:
    prints = sorted(path for path in PRINT_DIR.glob("BO-*.png") if path.is_file())
    products = sorted(path for path in MOCKUP_DIR.glob("BO-*.png") if path.is_file())
    rows = rows_from_product_filenames(MOCKUP_DIR)
    expected = [f"BO-{start + i}" for i in range(count)]
    print_skus = [path.stem for path in prints]
    product_skus = [path.name.split("_", 1)[0] for path in products]
    row_skus = [row[3] for row in rows]
    if print_skus != expected:
        raise RuntimeError(f"Print SKU mismatch: {print_skus[:3]} ... {print_skus[-3:]}")
    if product_skus != expected:
        raise RuntimeError(f"Product SKU mismatch: {product_skus[:3]} ... {product_skus[-3:]}")
    if row_skus != expected:
        raise RuntimeError(f"Excel row SKU mismatch: {row_skus[:3]} ... {row_skus[-3:]}")
    if len(set(path.stat().st_size for path in prints)) < count * 0.9:
        print("Warning: many print files have similar sizes; visual duplicate check is still recommended.")
    print(f"Validated prints={len(prints)}, products={len(products)}, rows={len(rows) + 1}")
    print(f"First SKU={expected[0]}, last SKU={expected[-1]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 50 BO commercial trend t-shirt prints, mockups, and xlsx.")
    parser.add_argument("--start", type=int, default=506)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=2026061102)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--bg-color-distance", type=float, default=42.0)
    parser.add_argument("--auto-start-comfyui", action="store_true")
    parser.add_argument("--comfy-timeout", type=int, default=240)
    parser.add_argument("--prompt-timeout", type=int, default=900)
    parser.add_argument("--keep-comfyui", action="store_true")
    parser.add_argument("--regenerate-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = build_specs()
    if args.count > len(specs):
        raise ValueError(f"Only {len(specs)} unique specs are available.")
    items = [(sku_for(args.start, index), specs[index]) for index in range(args.count)]
    write_prompt_file(items)

    started_at = time.time()
    generate_prints(items, args)
    mockups = make_mockups(items, args.seed)
    make_overview(mockups, MOCKUP_DIR / "_overview.jpg")
    write_xlsx_from_filenames(MOCKUP_DIR, args.count)
    validate_outputs(args.start, args.count)
    print(f"Prompt file: {PROMPT_FILE}")
    print(f"Print dir: {PRINT_DIR}")
    print(f"Product dir: {MOCKUP_DIR}")
    print(f"XLSX: {OUTPUT_XLSX}")
    print(f"Elapsed seconds: {time.time() - started_at:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
