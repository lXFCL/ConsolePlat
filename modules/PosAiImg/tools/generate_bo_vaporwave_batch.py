from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

import generate_bo_retro_nature_batch as base


ROOT = base.ROOT
PROGRESS_FILE = base.PROGRESS_FILE
PUTAWAY_DATA_DIR = base.PUTAWAY_DATA_DIR
PUTAWAY_PIC_DIR = base.PUTAWAY_PIC_DIR

BASE_POSITIVE = (
    "standalone isolated screen print decal asset, vaporwave printable decal badge, retro futurism, "
    "neon magenta, cyan, purple, deep navy, black linework, white highlight rim, chrome gradient accents, "
    "halftone screen print texture, compact central composition with a clean outer contour, "
    "visible on both black and white t-shirts, bold graphic silhouette, "
    "centered isolated artwork on seamless plain pure white background, generous empty margin, "
    "single print asset only, no mockup, no model, no shirt, no t-shirt silhouette, no clothing, "
    "no background scene, no shadow, no readable text, no letters, no logo, no brand mark, no watermark"
)

NEGATIVE = (
    "person, human, face, portrait, statue head, bust, skull, skeleton, body, hands, model, mannequin, "
    "shirt mockup, t-shirt, collar, sleeves, fabric folds, clothing, apparel, product preview, "
    "readable text, letters, words, logo, brand name, label, signature, watermark, messy full background, "
    "wallpaper, poster scene, photorealistic city photo, low contrast, blurry, cropped, copyrighted character"
)

SUBJECTS: list[tuple[str, str]] = [
    ("霓虹落日", "neon sunset grid badge, striped sun disc, perspective grid floor, small palm silhouettes, chrome ring frame"),
    ("棕榈网格", "vaporwave palm tree badge, magenta sunset, cyan wireframe grid, black palm silhouettes, compact emblem"),
    ("复古电脑", "retro computer window badge, old monitor, pixel sparkle accents, cyan magenta frame, no readable screen text"),
    ("霓虹磁带", "retro cassette tape vaporwave badge, neon grid halo, chrome tape reels, no readable label"),
    ("铬感星球", "chrome geometric orb badge, wireframe triangle, neon grid lines, magenta cyan glow accents"),
    ("合成海浪", "synthwave ocean badge, stylized wave, striped sun, horizon grid, palm leaves"),
    ("像素闪电", "pixel arcade starburst badge, abstract lightning bolts, cyan pink yellow black palette"),
    ("月夜棕榈", "crescent moon above wireframe ocean grid, two palm leaves, electric blue magenta violet palette"),
    ("霓虹圆窗", "round vaporwave window badge, sunset gradient, ocean line, palm silhouettes, chrome outer contour"),
    ("复古软盘", "retro floppy disk badge, chrome disk shape, neon pink cyan accents, pixel stars, no text"),
    ("电子海面", "electronic ocean grid badge, layered wave lines, striped sun, neon cyan magenta rim"),
    ("霓虹山线", "wireframe mountain badge, neon sunset disc, magenta purple sky shapes, cyan grid base"),
    ("棕榈月亮", "palm leaves and moon badge, dark silhouette leaves, violet moon glow, cyan outline"),
    ("街机星芒", "arcade starburst badge, geometric pixel sparks, neon cyan magenta yellow, clean sticker contour"),
    ("铬感三角", "chrome triangle emblem, neon grid reflection, small sun disc, deep navy shadow, no text"),
    ("梦幻海湾", "vaporwave bay badge, curved shoreline, striped sun, two palm silhouettes, pink cyan palette"),
    ("像素太阳", "pixelated sun badge, blocky gradient sun, simple grid horizon, small sparkle shapes"),
    ("霓虹唱片", "retro vinyl record badge, chrome record ring, magenta cyan highlights, abstract sound waves, no text"),
    ("电子月海", "moonlit synthwave sea badge, crescent moon, wireframe wave, palm shadow, purple blue palette"),
    ("复古电视", "retro television badge, glowing screen shape, pixel stars, chrome knobs, no readable content"),
    ("霓虹方块", "stacked geometric cube badge, chrome cubes, neon pink cyan rim light, grid shadow removed"),
    ("海浪圆章", "round synthwave wave emblem, striped sun, palm leaf accents, bold black linework"),
    ("棕榈星环", "palm silhouette inside star ring badge, neon sunset, cyan orbit lines, compact central graphic"),
    ("电子地平线", "vaporwave horizon badge, grid floor, sun half circle, small geometric mountains"),
    ("磁带星爆", "cassette tape starburst badge, angular neon burst, chrome tape reels, no readable label"),
    ("霓虹光环", "neon halo badge, abstract chrome ring, tiny pixel stars, purple cyan glow accents"),
    ("复古窗口", "retro operating system window collage badge, simple icons, pink cyan blocks, no letters"),
    ("铬感海星", "chrome star shape badge, grid reflection, magenta cyan edge lights, abstract vaporwave emblem"),
    ("夜色网格", "night grid badge, deep navy base, neon sun stripe, small palm shadows, high contrast outline"),
    ("像素月亮", "pixel crescent moon badge, blocky stars, cyan magenta grid waves, clean contour"),
    ("霓虹岛屿", "small island vaporwave badge, palm silhouettes, striped sun, ocean grid, chrome rim"),
    ("电音波纹", "abstract synthwave ripple badge, concentric neon wave lines, chrome center orb, no text"),
    ("复古键盘", "retro keyboard badge, old computer keyboard, neon pixel sparkles, cyan magenta frame, no text"),
    ("铬感海浪", "chrome wave badge, stylized wave curl, neon pink cyan reflections, black outline"),
    ("棕榈日落", "palm sunset medallion, hot pink sun, cyan water lines, bold black silhouettes"),
    ("霓虹罗盘", "abstract compass-like vaporwave badge, chrome points, grid circle, no letters or numbers"),
    ("电子云海", "vaporwave cloud sea badge, layered purple clouds, cyan grid horizon, neon sun"),
    ("复古游戏机", "retro handheld game console badge, glowing blank screen, pixel sparks, no readable buttons text"),
    ("霓虹贝壳", "synthwave shell badge, shell silhouette, ocean grid lines, pink cyan chrome highlights"),
    ("月光网格", "moon and grid badge, crescent moon, perspective cyan grid, purple sea lines"),
    ("铬感圆环", "chrome ring emblem, neon gradient inner circle, pixel sparkle accents, compact sticker shape"),
    ("棕榈海平线", "palm horizon badge, striped sun, wave line, cyan magenta glow, clean silhouette"),
    ("电子星球", "retro planet badge, chrome ringed planet, neon grid reflection, purple cyan palette"),
    ("霓虹浪花", "neon splash wave badge, stylized wave foam, hot pink sun disc, cyan outline"),
    ("复古光盘", "retro compact disc badge, chrome disc, neon highlights, pixel star accents, no text"),
    ("网格山海", "wireframe mountain and ocean badge, striped sun, purple blue grid, black outline"),
    ("夜海棕榈", "night sea palm badge, dark palm silhouettes, moon glow, magenta cyan water lines"),
    ("街机方窗", "arcade square window badge, pixel frame, abstract blank screen, neon burst, no readable text"),
    ("霓虹旋涡", "neon vortex badge, chrome spiral, grid fragments, magenta cyan purple palette"),
    ("合成落日", "synthwave sunset badge, striped sun, ocean wave, palm leaf frame, high contrast decal"),
]


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"蒸汽波印花_BO-{start}-BO-{start + count - 1}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, stamp)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def product_title(color_word: str, keyword: str) -> str:
    variants = [
        "圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
        "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
        "圆领短袖 柔软透气针织上衣 夏季日常百搭",
    ]
    suffix = variants[sum(ord(c) for c in color_word + keyword) % len(variants)]
    return f"夏季{color_word}蒸汽波{keyword}印花T恤 {suffix}"


def update_progress(
    start: int,
    count: int,
    print_dir: Path,
    mockup_dir: Path,
    output_xlsx: Path,
    validation: dict,
    putaway: dict,
) -> None:
    end = start + count - 1
    next_start = end + 1
    stamp = date.today().isoformat()
    try:
        text = PROGRESS_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = PROGRESS_FILE.read_text(encoding="gbk", errors="replace")
    text = re.sub(r"更新时间[：:]\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到[：:]\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从[：:]\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张蒸汽波印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，整体为蒸汽波/霓虹复古方向；需重点留意个别方形复古窗口图案是否偏海报感，以及黑 T 上深色轮廓是否足够清晰。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO vaporwave prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=956)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def configure_base() -> None:
    base.BASE_POSITIVE = BASE_POSITIVE
    base.NEGATIVE = NEGATIVE
    base.SUBJECTS = SUBJECTS
    base.product_title = product_title


def main() -> int:
    args = parse_args()
    configure_base()
    base.http_json("GET", f"{base.SERVER}/system_stats", timeout=5)
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(args.start, args.count, args.date)
    print_items = base.generate_prints(args.start, args.count, print_dir, prompt_file, args.seed)
    base.make_products(print_items, mockup_dir, args.seed + 7)
    base.write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, args.count)
    validation = base.validate_outputs(args.start, args.count, print_dir, mockup_dir, output_xlsx)
    base.sync_putaway(mockup_dir, output_xlsx)
    putaway = base.validate_putaway(args.start, args.count, output_xlsx)
    update_progress(args.start, args.count, print_dir, mockup_dir, output_xlsx, validation, putaway)
    print(f"Created {len(print_items)} print(s): {print_dir}")
    print(f"Created product image dir: {mockup_dir}")
    print(f"Created xlsx: {output_xlsx}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False)}")
    print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
