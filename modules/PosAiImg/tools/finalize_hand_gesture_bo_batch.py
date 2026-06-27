from __future__ import annotations

import math
import re
import shutil
import sys
import zipfile
from collections import deque
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.tshirt_print_tool import Placement, cloth_blend, fit_print, load_rgba  # noqa: E402


START = 1371
COUNT = 50
STAMP = "2026-06-16"
BATCH_TITLE = f"写实黑白手势英文印花_BO-{START}-BO-{START + COUNT - 1}_{STAMP}"

BASE = ROOT / "爆款印花知识库" / "爆款1" / "hand_print_imggen_50"
PREV5 = ROOT / "爆款印花知识库" / "爆款1" / "hand_print_imggen_5"
SPLIT45 = BASE / "new45_raw_split"
MODEL_DIR = ROOT / "模特图-干净"
PRINT_DIR = ROOT / "印花图_透明底" / BATCH_TITLE
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH_TITLE}_随机主图50"
PROMPT_FILE = ROOT / "生成提示词" / f"{BATCH_TITLE}.txt"
XLSX_PATH = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH_TITLE}.xlsx"
REPLACEMENT_DIR = BASE / "replacements"
REPLACEMENT_RAW = REPLACEMENT_DIR / "hand_18_speak_in_signs_replacement_raw.png"
REPLACEMENT_BY_INDEX = {
    2: "BO-1372_replacement_raw.png",
    3: "BO-1373_replacement_raw.png",
    4: "BO-1374_replacement_raw.png",
    5: "BO-1375_replacement_raw.png",
    18: "BO-1388_replacement_raw.png",
    33: "BO-1403_replacement_raw.png",
    45: "BO-1415_replacement_raw.png",
    46: "BO-1416_replacement_raw.png",
    48: "BO-1418_replacement_raw.png",
}

CAPTIONS = [
    "code of silence",
    "peace signal",
    "pinkie oath",
    "finger talk",
    "rock okay",
    "stay silent",
    "trust no shadow",
    "coded in calm",
    "soft rebellion",
    "guard your peace",
    "no hard feelings",
    "quiet signal",
    "hands remember",
    "never fold",
    "low key forever",
    "silver promise",
    "after midnight",
    "speak in signs",
    "hush mode",
    "keep it sacred",
    "cold hands warm heart",
    "still outside",
    "private motion",
    "no second guess",
    "almost famous",
    "calm pressure",
    "double meaning",
    "sign language",
    "silent proof",
    "shadow talk",
    "hold the line",
    "coded touch",
    "rare gesture",
    "one more secret",
    "nothing obvious",
    "faith in motion",
    "small revenge",
    "unseen energy",
    "quiet luxury",
    "ring language",
    "soft warning",
    "sacred noise",
    "inner circle",
    "money fingers",
    "gentle chaos",
    "never explain",
    "midnight code",
    "hand signal",
    "silent season",
    "private code",
]

PHRASES_CN = [
    "爱心",
    "和平",
    "拉钩",
    "手枪",
    "摇滚",
    "静默",
    "暗号",
    "冷静",
    "叛逆",
    "守护",
    "随性",
    "信号",
    "记忆",
    "交叉",
    "低调",
    "银饰",
    "午夜",
    "捏指",
    "祈祷",
    "神圣",
    "点赞",
    "向下",
    "握手",
    "摇滚",
    "合掌",
    "花枝",
    "双关",
    "手语",
    "交叉",
    "戒指",
    "立掌",
    "三角",
    "稀有",
    "托举",
    "拳头",
    "竖指",
    "小众",
    "弯指",
    "张掌",
    "手腕",
    "警告",
    "举掌",
    "内圈",
    "拳头",
    "混沌",
    "解释",
    "午夜暗号",
    "手部信号",
    "季节",
    "私密暗号",
]

TITLE_SUFFIXES = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    return re.sub(r"_+", "_", "".join("_" if c in invalid or ord(c) < 32 else c for c in text)).strip(" ._")


def chroma_to_alpha(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            score = g - max(r, b)
            # Be conservative: grayscale hand highlights can pick up mild green spill.
            # Only remove pixels that are clearly the saturated chroma background.
            if g > 165 and score > 58 and r < 150 and b < 150:
                alpha = 0 if score > 84 or (g > 205 and r < 120 and b < 120) else max(0, min(255, int((92 - score) * 6)))
                px[x, y] = (r, g, b, alpha)
            else:
                px[x, y] = (r, g, b, a)
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a and g > max(r, b) + 12:
                px[x, y] = (r, int(max(r, b) * 0.75 + g * 0.18), b, a)
    return img


def remove_small_alpha_components(img: Image.Image, min_area: int = 1600) -> Image.Image:
    img = img.convert("RGBA")
    alpha = np.array(img.getchannel("A"))
    h, w = alpha.shape
    seen = np.zeros((h, w), dtype=bool)
    arr = np.array(img)

    for start_y in range(h):
        for start_x in range(w):
            if seen[start_y, start_x] or alpha[start_y, start_x] == 0:
                continue
            stack = [(start_x, start_y)]
            seen[start_y, start_x] = True
            pixels: list[tuple[int, int]] = []
            min_x = max_x = start_x
            min_y = max_y = start_y
            while stack:
                x, y = stack.pop()
                pixels.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and alpha[ny, nx] > 0:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            area = len(pixels)
            comp_w = max_x - min_x + 1
            comp_h = max_y - min_y + 1
            density = area / max(1, comp_w * comp_h)
            skinny_edge_speck = (min_x < 4 or max_x > w - 5) and comp_w < 36 and comp_h < 220
            touches_edge = min_x < 8 or min_y < 8 or max_x > w - 9 or max_y > h - 9
            frame_like = touches_edge and density < 0.12 and (comp_w > w * 0.45 or comp_h > h * 0.45)
            if area < min_area or skinny_edge_speck or frame_like:
                for x, y in pixels:
                    arr[y, x, 3] = 0
    return Image.fromarray(arr, "RGBA")


def remove_flat_dark_panel(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[..., :3].astype(np.int16)
    alpha = arr[..., 3]
    # Generated replacements sometimes include a flat dark preview panel after
    # chroma removal. Keep real black ink, but drop low-contrast dark fill.
    dark_panel = (
        (alpha > 0)
        & (rgb[..., 0] >= 24)
        & (rgb[..., 0] <= 72)
        & (rgb[..., 1] >= 24)
        & (rgb[..., 1] <= 72)
        & (rgb[..., 2] >= 24)
        & (rgb[..., 2] <= 72)
        & ((np.max(rgb, axis=2) - np.min(rgb, axis=2)) < 18)
    )
    arr[..., 3] = np.where(dark_panel, 0, arr[..., 3])
    return Image.fromarray(arr, "RGBA")


def remove_thin_vertical_artifacts(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    arr = np.array(img)
    alpha = arr[..., 3]
    h, w = alpha.shape
    # Some generated panels leave a 1-3 px vertical divider attached near the
    # far side of a hand. Remove only long, very thin, locally isolated runs.
    for x in range(int(w * 0.55), w - 2):
        mask = alpha[:, x] > 0
        if int(mask.sum()) < int(h * 0.20):
            continue
        y = 0
        while y < h:
            if not mask[y]:
                y += 1
                continue
            start = y
            while y < h and mask[y]:
                y += 1
            end = y
            if end - start < int(h * 0.16):
                continue
            local = alpha[start:end, max(0, x - 2) : min(w, x + 3)] > 0
            row_widths = local.sum(axis=1)
            if float(np.percentile(row_widths, 85)) <= 2.0:
                arr[start:end, max(0, x - 1) : min(w, x + 2), 3] = 0
    return Image.fromarray(arr, "RGBA")


def remove_border_light_bg(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    q: deque[tuple[int, int]] = deque()

    def idx(x: int, y: int) -> int:
        return y * w + x

    def removable(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a == 0:
            return True
        if min(r, g, b) > 208 and max(r, g, b) - min(r, g, b) < 58:
            return True
        return a < 245 and min(r, g, b) > 165

    for x in range(w):
        for y in (0, h - 1):
            if removable(x, y) and not seen[idx(x, y)]:
                seen[idx(x, y)] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if removable(x, y) and not seen[idx(x, y)]:
                seen[idx(x, y)] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        if px[x, y][3] != 0:
            px[x, y] = (px[x, y][0], px[x, y][1], px[x, y][2], 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[idx(nx, ny)] and removable(nx, ny):
                seen[idx(nx, ny)] = 1
                q.append((nx, ny))
    return img


def crop_alpha(img: Image.Image, pad: int = 16) -> Image.Image:
    img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        return img
    left, top, right, bottom = bbox
    return img.crop((max(0, left - pad), max(0, top - pad), min(img.width, right + pad), min(img.height, bottom + pad)))


def clear_lower_old_text(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    h, w = arr.shape[:2]
    for y in range(int(h * 0.70), h):
        for x in range(w):
            r, g, b, a = arr[y, x]
            if a > 0 and max(r, g, b) < 170:
                arr[y, x, 3] = 0
    return Image.fromarray(arr, "RGBA")


def clear_lower_ghosts(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    arr = np.array(img)
    alpha = arr[..., 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return img

    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())
    content_h = max(1, max_y - min_y + 1)
    content_w = max(1, max_x - min_x + 1)
    yy, xx = np.indices(alpha.shape)
    rgb = arr[..., :3].astype(np.int16)
    brightness = rgb.max(axis=2)
    color_range = rgb.max(axis=2) - rgb.min(axis=2)

    # Remove only weak preview/text residue near the original image bottom.
    # Real dark hand linework and the new handwritten caption are added later.
    lower = yy > min_y + int(content_h * 0.68)
    inside = (xx >= min_x + int(content_w * 0.05)) & (xx <= max_x - int(content_w * 0.05))
    pale_ghost = (
        (alpha > 0)
        & (alpha < 245)
        & lower
        & inside
        & (brightness > 132)
        & (color_range < 56)
    )
    very_faint = (
        (alpha > 0)
        & (alpha < 42)
        & lower
        & (brightness > 95)
    )
    arr[..., 3] = np.where(pale_ghost | very_faint, 0, arr[..., 3])
    return Image.fromarray(arr, "RGBA")


def font_path() -> Path:
    for name in ("segoesc.ttf", "Inkfree.ttf", "Gabriola.ttf"):
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return path
    raise FileNotFoundError("No script font found")


def make_text_layer(text: str, max_w: int, seed: int) -> Image.Image:
    fp = font_path()
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    font_size = 78
    while font_size > 32:
        font = ImageFont.truetype(str(fp), font_size)
        bbox = probe.textbbox((0, 0), text, font=font, stroke_width=2)
        if bbox[2] - bbox[0] <= max_w:
            break
        font_size -= 3
    font = ImageFont.truetype(str(fp), font_size)
    bbox = probe.textbbox((0, 0), text, font=font, stroke_width=2)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    layer = Image.new("RGBA", (tw + 38, th + 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text((21 - bbox[0], 18 - bbox[1]), text, font=font, fill=(248, 248, 242, 218), stroke_width=2, stroke_fill=(248, 248, 242, 178))
    draw.text((19 - bbox[0], 16 - bbox[1]), text, font=font, fill=(18, 18, 18, 242), stroke_width=1, stroke_fill=(245, 245, 238, 148))
    angle = [-2.2, -1.3, 0.7, 1.4, -0.6][seed % 5]
    return layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))


def build_print(subject: Image.Image, caption: str, index: int) -> Image.Image:
    subject = ImageEnhance.Contrast(crop_alpha(subject, 18)).enhance(1.08)
    canvas_w = 1300
    subject.thumbnail((int(canvas_w * 0.90), int(canvas_w * 0.76)), Image.Resampling.LANCZOS)
    text_layer = make_text_layer(caption, int(canvas_w * 0.46), index)
    text_gap = 28
    canvas = Image.new("RGBA", (canvas_w, subject.height + text_gap + max(text_layer.height + 18, 72)), (0, 0, 0, 0))
    canvas.alpha_composite(subject, ((canvas_w - subject.width) // 2, 0))
    canvas.alpha_composite(text_layer, ((canvas_w - text_layer.width) // 2 + (index % 5 - 2) * 4, subject.height + text_gap))
    return crop_alpha(remove_thin_vertical_artifacts(canvas), 12)


def clean_bo1372_lower_residue(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    alpha = arr[..., 3]
    rgb = arr[..., :3].astype(np.int16)
    yy, xx = np.indices(alpha.shape)
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    residue = (
        (alpha > 0)
        & (yy > 790)
        & (yy < 1015)
        & (xx > 95)
        & (xx < 455)
        & (maxc > 135)
        & ((maxc - minc) < 105)
    )
    arr[..., 3] = np.where(residue, 0, arr[..., 3])
    return Image.fromarray(arr, "RGBA")


def newest_generated_image() -> Path:
    images = [p for p in Path("C:/Users/Administrator/.codex/generated_images").rglob("*.png") if p.is_file()]
    if not images:
        raise FileNotFoundError("No generated images found")
    return sorted(images, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def prepare_prints() -> None:
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPLACEMENT_DIR.mkdir(parents=True, exist_ok=True)
    for old in PRINT_DIR.glob("*.png"):
        old.unlink()

    raw5 = sorted(PREV5.glob("hand_*_raw.png"))[:5]
    raw45 = sorted(SPLIT45.glob("hand_*_raw.png"))
    if len(raw5) != 5 or len(raw45) != 45:
        raise RuntimeError(f"bad source counts raw5={len(raw5)} raw45={len(raw45)}")

    sources = raw5 + raw45
    for index, filename in REPLACEMENT_BY_INDEX.items():
        replacement = REPLACEMENT_DIR / filename
        if replacement.exists():
            sources[index - 1] = replacement
    lines = [BATCH_TITLE, "source\tsku\tcaption\tpath"]
    for index, source in enumerate(sources, 1):
        sku = f"BO-{START + index - 1}"
        subject = remove_border_light_bg(chroma_to_alpha(ImageOps.exif_transpose(Image.open(source)).convert("RGBA")))
        subject = remove_flat_dark_panel(subject)
        subject = remove_small_alpha_components(subject)
        subject = clear_lower_ghosts(subject)
        if index <= 5:
            subject = clear_lower_old_text(subject)
        final_print = build_print(subject, CAPTIONS[index - 1], index)
        if index == 2:
            final_print = clean_bo1372_lower_residue(final_print)
        final_print.save(PRINT_DIR / f"{sku}.png")
        lines.append(f"{index}\t{sku}\t{CAPTIONS[index - 1]}\t{source}")
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def shirt_color(model_path: Path) -> tuple[str, str]:
    if "白" in model_path.stem:
        return "白色", "白"
    return "黑色", "黑"


def make_products() -> list[tuple[str, str, str, str, str]]:
    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(MOCKUP_DIR.glob("*.png")) + list(MOCKUP_DIR.glob("*.jpg")) + list(MOCKUP_DIR.glob("*.txt")):
        old.unlink()
    models = sorted(p for p in MODEL_DIR.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    placement = Placement(width=0.39, opacity=0.96, shadow_strength=0.25, wave_strength=0.006, remove_white_bg=False)
    rows: list[tuple[str, str, str, str, str]] = []
    made: list[Path] = []
    place_rows: list[tuple[str, str, int, int, int, int]] = []
    for index in range(1, COUNT + 1):
        sku = f"BO-{START + index - 1}"
        model = models[(index - 1) % len(models)]
        color_word, color_col = shirt_color(model)
        title = f"夏季{color_word}写实黑白手势{PHRASES_CN[index - 1]}印花T恤 {TITLE_SUFFIXES[(index - 1) % len(TITLE_SUFFIXES)]}"
        output = MOCKUP_DIR / safe_filename(f"{sku}_{title}.png")
        base_img = load_rgba(model)
        fitted = fit_print(load_rgba(PRINT_DIR / f"{sku}.png"), base_img.size, placement)
        max_h = int(base_img.height * 0.385)
        if fitted.height > max_h:
            new_w = max(1, int(fitted.width * max_h / fitted.height))
            fitted = fitted.resize((new_w, max_h), Image.Resampling.LANCZOS)
        top_y = int(base_img.height * (0.345 if fitted.height < base_img.height * 0.25 else 0.315))
        x = int(base_img.width * 0.50 - fitted.width / 2)
        result = cloth_blend(base_img, fitted, x, top_y, placement)
        result.save(output)
        rows.append(("YUHAOBO", "T恤", title, sku, color_col))
        made.append(output)
        place_rows.append((output.name, model.name, fitted.width, fitted.height, x, top_y))

    make_overview(made, MOCKUP_DIR / "_overview.jpg")
    with (MOCKUP_DIR / "_placement_log.txt").open("w", encoding="utf-8") as f:
        f.write("name\tmodel\tdesign_w\tdesign_h\tx\ty\n")
        for row in place_rows:
            f.write("\t".join(map(str, row)) + "\n")
    return rows


def make_overview(paths: list[Path], output: Path) -> None:
    cols, tile_w, tile_h = 10, 220, 290
    sheet = Image.new("RGB", (cols * tile_w, math.ceil(len(paths) / cols) * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((205, 236), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 6))
        ImageDraw.Draw(tile).text((6, 252), path.stem[:28], font=font, fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    sheet.save(output, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml: list[str] = []
    for row_idx, values in enumerate(rows, 1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:E{len(rows)}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def write_xlsx(rows: list[tuple[str, str, str, str, str]]) -> None:
    xlsx_root = ROOT / "衣物对应的xlsx" / "简约200"
    templates = [p for p in xlsx_root.glob("*.xlsx") if "BO-" in p.name and not p.name.startswith("~$")]
    if not templates:
        raise FileNotFoundError("No BO xlsx template found")
    template = sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    all_rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *rows]
    tmp = XLSX_PATH.with_suffix(".tmp.xlsx")
    shutil.copy2(template, tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(XLSX_PATH, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, build_sheet_xml(all_rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename))
    tmp.unlink(missing_ok=True)


def main() -> int:
    prepare_prints()
    rows = make_products()
    write_xlsx(rows)
    print(f"batch={BATCH_TITLE}")
    print(f"print_dir={PRINT_DIR}")
    print(f"mockup_dir={MOCKUP_DIR}")
    print(f"xlsx={XLSX_PATH}")
    print(f"prompt={PROMPT_FILE}")
    print(f"replacement_raw={REPLACEMENT_RAW}")
    print(f"prints={len(list(PRINT_DIR.glob('*.png')))}")
    print(f"products={len([p for p in MOCKUP_DIR.glob('*.png') if not p.name.startswith('_')])}")
    print(f"first_sku=BO-{START}")
    print(f"last_sku=BO-{START + COUNT - 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
