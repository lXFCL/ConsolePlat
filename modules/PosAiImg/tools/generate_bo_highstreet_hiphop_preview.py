from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_bo_commercial_trend_batch as base  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
STYLE_NAME = "高街嘻哈印花"


@dataclass(frozen=True)
class HighstreetSpec:
    title_word: str
    prompt: str


def batch_name(start: int, count: int, batch_date: str | None = None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"{STYLE_NAME}_BO-{start}-BO-{end}_{stamp}"


def configure_paths(start: int, count: int, batch_date: str | None = None) -> None:
    name = batch_name(start, count, batch_date)
    base.PROMPT_FILE = ROOT / "生成提示词" / f"{name}.txt"
    base.PRINT_DIR = ROOT / "印花图_透明底" / name
    base.MOCKUP_DIR = ROOT / "批量贴图结果" / f"{name}_随机主图{count}"
    base.OUTPUT_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx"


def build_specs() -> list[base.DesignSpec]:
    specs = [
        HighstreetSpec(
            "皇冠涂鸦",
            "oversized streetwear hip hop graphic decal artwork only, graffiti crown emblem, bold handstyle wordmark reading KING VIBE, black ink, warm off-white stroke, muted red spray paint accents, chunky sticker silhouette, high street fashion mood, screen print texture, no garment",
        ),
        HighstreetSpec(
            "星芒锁链",
            "high street hip hop standalone decal artwork only, thick chain loop, starburst sparks, bold gothic lettering reading STREET CODE, black white and antique gold palette, strong outline, stacked badge composition, gritty screen printed texture, no garment",
        ),
        HighstreetSpec(
            "黑金徽章",
            "street luxury hip hop emblem decal, original shield badge with small crown, laurel leaves, block letters reading NO LIMIT, black and cream with dull gold accents, premium high street graphic, bold readable shape",
        ),
        HighstreetSpec(
            "街头字标",
            "urban hip hop typography decal artwork only, wildstyle inspired but readable wordmark reading CITY FLOW, underline slash, small star dots, black heavy letters, white outer stroke, red accent tag marks, modern high street graphic print asset, no garment",
        ),
        HighstreetSpec(
            "火焰唱片",
            "hip hop streetwear graphic decal, vinyl record with small flame tips, crown mark above, bold letters reading NIGHT BEAT, black gray cream and muted red palette, centered sticker logo, thick screen print outline",
        ),
        HighstreetSpec(
            "喷漆王冠",
            "high street rap style print decal, spray paint crown, rough brush lettering reading RAW CLUB, black cream and faded gold, compact chest print composition, no brand logo",
        ),
        HighstreetSpec(
            "暗星厂牌",
            "original hip hop label style decal, dark star badge, stacked block type reading LOW KEY, black ink with cream stroke and small red dots, vintage screen print texture",
        ),
        HighstreetSpec(
            "街区节拍",
            "street block hip hop emblem decal, boombox abstract icon, lightning slash, bold lettering reading BLOCK BEAT, black white gray with muted gold accent, readable from distance",
        ),
    ]
    return [
        base.DesignSpec(
            "高街嘻哈",
            spec.title_word,
            (
                f"original standalone printable streetwear graphic decal, {spec.prompt}, "
                "no real brand, no copyrighted logo, no celebrity, no character, no person, no shirt, no tee, no clothing, no mockup"
            ),
        )
        for spec in specs
    ]


def sku_for(start: int, index: int) -> str:
    return f"BO-{start + index}"


def write_prompt_file(items: list[tuple[str, base.DesignSpec]]) -> None:
    base.PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "高街嘻哈印花试样。",
        "方向：街头潮牌感、嘻哈字标、皇冠、锁链、徽章、喷漆元素；避免真实品牌 Logo、明星、版权角色。",
        "",
    ]
    lines.extend(f"{sku}: {spec.theme} / {spec.title_word} / {spec.prompt}" for sku, spec in items)
    base.PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO high street hip hop print preview batch.")
    parser.add_argument("--start", type=int, default=706)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026061205)
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
    parser.add_argument("--date", default=None, help="Batch date stamp, defaults to today (YYYY-MM-DD).")
    parser.add_argument("--prints-only", action="store_true", help="Only generate test print PNGs; skip mockups and xlsx.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = build_specs()
    if args.count > len(specs):
        raise ValueError(f"Only {len(specs)} unique high street hip hop specs are available.")

    configure_paths(args.start, args.count, args.date)
    items = [(sku_for(args.start, index), specs[index]) for index in range(args.count)]
    write_prompt_file(items)

    started_at = time.time()
    base.generate_prints(items, args)
    if args.prints_only:
        print(f"Prompt file: {base.PROMPT_FILE}")
        print(f"Print dir: {base.PRINT_DIR}")
        print(f"Elapsed seconds: {time.time() - started_at:.1f}")
        return 0

    mockups = base.make_mockups(items, args.seed)
    base.make_overview(mockups, base.MOCKUP_DIR / "_overview.jpg")
    base.write_xlsx_from_filenames(base.MOCKUP_DIR, args.count)
    base.validate_outputs(args.start, args.count)
    print(f"Prompt file: {base.PROMPT_FILE}")
    print(f"Print dir: {base.PRINT_DIR}")
    print(f"Product dir: {base.MOCKUP_DIR}")
    print(f"XLSX: {base.OUTPUT_XLSX}")
    print(f"Elapsed seconds: {time.time() - started_at:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
