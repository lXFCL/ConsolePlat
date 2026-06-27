from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_right_chest_style_tests as util  # noqa: E402
from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "模特图-干净"


@dataclass(frozen=True)
class CenterStyle:
    key: str
    zh: str
    note: str


STYLES = [
    CenterStyle("loud_vintage", "大字报复古图形", "大字、星芒、色块和旧海报感，适合中间胸前强视觉。"),
    CenterStyle("varsity_sport", "复古运动校队", "球衣数字、拱形字、学院运动感。"),
    CenterStyle("handmade_doodle", "手绘涂鸦插画", "不完美线条、随手画、亲和感。"),
    CenterStyle("rubber_food", "复古卡通食物", "橡皮管动画感食物角色，偏独立品牌周边。"),
    CenterStyle("tattoo_flash", "Tattoo Flash怀旧", "爱心、匕首、樱桃、火焰等纹身闪图语言。"),
    CenterStyle("outdoor_badge", "户外山野徽章", "山、太阳、松树、公路，复古户外 T 恤。"),
    CenterStyle("animal_graphic", "动物纹大胆图形", "虎纹、斑马、豹点、奶牛纹做大面积图形。"),
    CenterStyle("y2k_signal", "Y2K电码故障", "像素、电码、扫描线、故障切片。"),
]


def text_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill, stroke=util.WHITE, sw: int = 10):
    return util.text_center(draw, xy, text, util.font("impact.ttf", size), fill, stroke, sw)


def render_loud_vintage(draw: ImageDraw.ImageDraw, i: int) -> None:
    words = [("ANALOG", "RUSH"), ("LOUD", "SIGNAL"), ("NEON", "POSTER"), ("WILD", "TYPE"), ("MIDNIGHT", "CLUB")]
    top, bottom = words[i]
    accents = [util.RED, util.BLUE, util.PINK, util.GOLD, util.CYAN]
    accent = accents[i]
    rng = random.Random(100 + i)
    for _ in range(42):
        x = rng.randint(240, 1260)
        y = rng.randint(190, 1180)
        r = rng.randint(6, 24)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=accent if rng.random() < 0.6 else util.BLACK)
    draw.rounded_rectangle((195, 320, 1305, 950), radius=74, fill=util.CREAM, outline=util.BLACK, width=22)
    text_center(draw, (750, 555), top, 245 if len(top) <= 6 else 190, util.BLACK, util.WHITE, 14)
    text_center(draw, (750, 805), bottom, 190, accent, util.BLACK, 10)
    draw.line((260, 1005, 1240, 905), fill=util.BLACK, width=32)
    for x in (290, 1210):
        util.draw_star(draw, x, 270, 72, 29, accent)


def render_varsity_sport(draw: ImageDraw.ImageDraw, i: int) -> None:
    nums = ["86", "23", "07", "14", "99"]
    names = ["VARSITY", "TRACK CLUB", "FIELD DAY", "LOCAL TEAM", "RALLY CREW"]
    colors = [util.RED, util.BLUE, util.GREEN, util.GOLD, util.PINK]
    c = colors[i]
    draw.ellipse((265, 165, 1235, 1135), fill=util.CREAM, outline=util.BLACK, width=24)
    draw.ellipse((350, 250, 1150, 1050), outline=c, width=22)
    text_center(draw, (750, 660), nums[i], 430, util.BLACK, util.CREAM, 10)
    text_center(draw, (750, 1020), names[i], 120 if len(names[i]) <= 8 else 94, c, util.WHITE, 8)
    draw.line((450, 330, 1050, 330), fill=util.BLACK, width=20)
    util.draw_star(draw, 430, 905, 54, 23, c)
    util.draw_star(draw, 1070, 905, 54, 23, c)


def render_handmade_doodle(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["SUNNY", "CAFE", "DREAM", "HELLO", "LO-FI"]
    colors = [util.GOLD, util.GREEN, util.PINK, util.BLUE, util.RED]
    c = colors[i]
    rng = random.Random(300 + i)
    for _ in range(18):
        x = rng.randint(270, 1220)
        y = rng.randint(250, 1060)
        draw.arc((x - 55, y - 35, x + 55, y + 35), 0, 260, fill=util.BLACK, width=8)
    draw.ellipse((455, 300, 1045, 890), fill=util.CREAM, outline=util.BLACK, width=22)
    draw.ellipse((575, 500, 645, 570), fill=util.BLACK)
    draw.ellipse((855, 500, 925, 570), fill=util.BLACK)
    draw.arc((610, 555, 890, 770), 15, 165, fill=util.BLACK, width=24)
    for x in range(360, 1141, 120):
        draw.ellipse((x - 22, 930, x + 22, 974), fill=c)
    text_center(draw, (750, 1120), labels[i], 150, c, util.WHITE, 8)


def render_rubber_food(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["PIZZA", "COFFEE", "CHILI", "DONUT", "BURGER"]
    c = [util.RED, util.GOLD, util.GREEN, util.PINK, util.BLUE][i]
    if i == 0:
        draw.polygon([(500, 260), (1050, 715), (420, 980)], fill=(238, 194, 101, 255), outline=util.BLACK)
        draw.arc((450, 215, 1080, 780), 208, 303, fill=util.RED, width=42)
        for x, y in [(630, 545), (780, 640), (680, 780), (890, 725)]:
            draw.ellipse((x - 35, y - 35, x + 35, y + 35), fill=util.RED)
    elif i == 1:
        draw.rounded_rectangle((455, 320, 980, 830), radius=70, fill=util.CREAM, outline=util.BLACK, width=22)
        draw.arc((880, 460, 1160, 705), -85, 95, fill=util.BLACK, width=28)
        draw.line((510, 260, 930, 260), fill=util.BLACK, width=24)
    elif i == 2:
        draw.ellipse((520, 250, 960, 960), fill=util.RED, outline=util.BLACK, width=24)
        draw.arc((565, 190, 845, 390), 190, 335, fill=util.GREEN, width=42)
    elif i == 3:
        draw.ellipse((370, 275, 1130, 1035), fill=(218, 165, 109, 255), outline=util.BLACK, width=26)
        draw.ellipse((585, 490, 915, 820), fill=(255, 255, 255, 0), outline=util.BLACK, width=24)
        for x, y in [(540, 420), (790, 365), (965, 540), (520, 845), (900, 890)]:
            draw.rounded_rectangle((x - 45, y - 12, x + 45, y + 12), radius=12, fill=c)
    else:
        draw.rounded_rectangle((360, 410, 1140, 580), radius=85, fill=(227, 174, 85, 255), outline=util.BLACK, width=22)
        draw.rectangle((390, 600, 1110, 760), fill=util.GREEN, outline=util.BLACK, width=18)
        draw.rounded_rectangle((360, 790, 1140, 970), radius=85, fill=(227, 174, 85, 255), outline=util.BLACK, width=22)
    draw.ellipse((635, 620, 705, 690), fill=util.BLACK)
    draw.ellipse((795, 620, 865, 690), fill=util.BLACK)
    draw.arc((635, 675, 865, 810), 15, 165, fill=util.BLACK, width=18)
    text_center(draw, (750, 1200), labels[i], 138, c, util.WHITE, 8)


def render_tattoo_flash(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["HEART", "CHERRY", "DAGGER", "FLAME", "LUCK"]
    c = [util.RED, util.PINK, util.BLUE, util.GOLD, util.GREEN][i]
    if i == 0:
        draw.pieslice((360, 270, 760, 670), 180, 360, fill=util.RED, outline=util.BLACK)
        draw.pieslice((740, 270, 1140, 670), 180, 360, fill=util.RED, outline=util.BLACK)
        draw.polygon([(360, 470), (1140, 470), (750, 1040)], fill=util.RED, outline=util.BLACK)
        draw.line((470, 475, 1010, 900), fill=util.BLACK, width=28)
    elif i == 1:
        draw.ellipse((445, 600, 710, 865), fill=util.RED, outline=util.BLACK, width=20)
        draw.ellipse((790, 600, 1055, 865), fill=util.RED, outline=util.BLACK, width=20)
        draw.arc((530, 270, 950, 660), 200, 345, fill=util.GREEN, width=28)
        draw.arc((755, 260, 1090, 660), 190, 300, fill=util.GREEN, width=28)
    elif i == 2:
        draw.polygon([(710, 240), (790, 240), (840, 1000), (750, 1190), (660, 1000)], fill=util.CREAM, outline=util.BLACK)
        draw.rectangle((560, 420, 940, 485), fill=c, outline=util.BLACK, width=18)
    elif i == 3:
        pts = [(750, 240), (900, 560), (825, 535), (980, 1040), (720, 855), (640, 1130), (565, 800), (480, 890), (590, 520)]
        draw.polygon(pts, fill=util.RED, outline=util.BLACK)
        draw.polygon([(735, 420), (815, 615), (725, 765), (660, 615)], fill=util.GOLD)
    else:
        for x, y in [(560, 430), (850, 425), (555, 760), (845, 765)]:
            util.draw_star(draw, x, y, 130, 55, c)
        draw.ellipse((465, 505, 1035, 935), outline=util.BLACK, width=26)
    text_center(draw, (750, 1220), labels[i], 128, c, util.WHITE, 8)


def render_outdoor_badge(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["TRAIL", "CAMP", "RIDGE", "LAKE", "ROAD"]
    c = [util.GREEN, util.RED, util.GOLD, util.BLUE, util.GRAY][i]
    draw.rounded_rectangle((270, 230, 1230, 1080), radius=95, fill=util.CREAM, outline=util.BLACK, width=26)
    draw.arc((455, 245, 1045, 835), 205, 335, fill=util.GOLD, width=34)
    for y in [620, 720, 820]:
        pts = [(320, y), (500, y - 145), (690, y - 70), (840, y - 185), (1180, y - 35)]
        draw.line(pts, fill=util.BLACK, width=24, joint="curve")
    for x in [415, 1045]:
        draw.polygon([(x, 785), (x - 65, 980), (x + 65, 980)], fill=c, outline=util.BLACK)
        draw.rectangle((x - 18, 975, x + 18, 1065), fill=util.BLACK)
    text_center(draw, (750, 1010), labels[i], 150, c, util.WHITE, 8)


def render_animal_graphic(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["LEOPARD", "ZEBRA", "TIGER", "COW", "WILD"]
    rng = random.Random(800 + i)
    draw.rounded_rectangle((250, 220, 1250, 1080), radius=70, fill=util.CREAM, outline=util.BLACK, width=24)
    if i in (0, 4):
        for _ in range(42):
            x, y = rng.randint(320, 1180), rng.randint(290, 890)
            rx, ry = rng.randint(18, 70), rng.randint(14, 50)
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=util.BLACK)
            if i == 0:
                draw.ellipse((x - rx // 2, y - ry // 2, x + rx // 2, y + ry // 2), fill=util.GOLD)
    elif i == 1:
        for x in range(330, 1220, 95):
            draw.line((x, 270, x + rng.randint(-150, 150), 940), fill=util.BLACK, width=rng.randint(28, 55))
    elif i == 2:
        for y in range(310, 920, 78):
            draw.line((310, y, 1200, y + rng.randint(-70, 70)), fill=util.BLACK, width=34)
            draw.polygon([(320, y), (430, y + 60), (300, y + 88)], fill=util.GOLD)
    else:
        for _ in range(18):
            x, y = rng.randint(330, 1150), rng.randint(310, 860)
            rx, ry = rng.randint(45, 120), rng.randint(32, 85)
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=util.BLACK)
    text_center(draw, (750, 1015), labels[i], 140 if len(labels[i]) <= 5 else 110, util.RED if i == 2 else util.BLACK, util.WHITE, 8)


def render_y2k_signal(draw: ImageDraw.ImageDraw, i: int) -> None:
    labels = ["SIGNAL", "ERROR", "CTRL", "VOID", "BYTE"]
    accents = [util.CYAN, util.RED, util.PINK, util.GREEN, util.BLUE]
    c = accents[i]
    rng = random.Random(1200 + i)
    for _ in range(58):
        x, y = rng.randint(220, 1240), rng.randint(240, 1080)
        w, h = rng.randint(22, 150), rng.randint(8, 42)
        draw.rectangle((x, y, x + w, y + h), fill=c if rng.random() < 0.45 else util.BLACK)
    draw.rounded_rectangle((260, 390, 1240, 890), radius=50, outline=util.BLACK, width=28)
    text_center(draw, (750, 630), labels[i], 230 if len(labels[i]) <= 5 else 180, util.BLACK, util.WHITE, 14)
    draw.line((230, 785, 1265, 660), fill=c, width=34)
    draw.line((330, 925, 1170, 1005), fill=util.BLACK, width=20)


RENDERERS = {
    "loud_vintage": render_loud_vintage,
    "varsity_sport": render_varsity_sport,
    "handmade_doodle": render_handmade_doodle,
    "rubber_food": render_rubber_food,
    "tattoo_flash": render_tattoo_flash,
    "outdoor_badge": render_outdoor_badge,
    "animal_graphic": render_animal_graphic,
    "y2k_signal": render_y2k_signal,
}


def render_print(style: CenterStyle, index: int, path: Path) -> None:
    img = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    RENDERERS[style.key](draw, index)
    util.crop_save(img, path)


def make_center_mockups(print_paths: list[tuple[CenterStyle, Path]], output_dir: Path, seed: int) -> list[tuple[CenterStyle, Path]]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
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
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[CenterStyle, Path]] = []
    for idx, (style, print_path) in enumerate(print_paths):
        model = rng.choice(models)
        out = output_dir / f"{print_path.stem}_center_preview.png"
        composite_one(model, print_path, out, placement)
        outputs.append((style, out))
        print(f"preview {idx + 1:02d}: {out}")
    return outputs


def write_notes(styles: list[CenterStyle], output_path: Path) -> None:
    lines = [
        "中间胸前印花风格测试。",
        "只生成测试透明底印花和中间位置预览；不更新货号、不生成 xlsx、不复制到上架目录。",
        "",
    ]
    lines.extend(f"- {style.zh}：{style.note}" for style in styles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render center chest print style tests.")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--per-style", type=int, default=5)
    parser.add_argument("--styles", type=int, default=8, choices=range(5, 9))
    parser.add_argument("--seed", type=int, default=2026061240)
    parser.add_argument("--skip-mockups", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = STYLES[: args.styles]
    base_name = f"中间印花风格测试_{args.date}"
    print_root = ROOT / "印花图_透明底" / base_name
    preview_root = ROOT / "AI印花贴图测试" / f"{base_name}_中间预览"
    notes_path = ROOT / "生成提示词" / f"{base_name}.txt"

    print_paths: list[tuple[CenterStyle, Path]] = []
    for style in selected:
        style_dir = print_root / style.zh
        for i in range(args.per_style):
            path = style_dir / f"{style.key}_{i + 1:02d}.png"
            render_print(style, i, path)
            print_paths.append((style, path))
            print(f"print {style.zh} {i + 1}: {path}")

    util.make_overview(print_paths, print_root / "_all_prints_overview.jpg", "center chest print style tests")
    write_notes(selected, notes_path)

    if not args.skip_mockups:
        previews = make_center_mockups(print_paths, preview_root, args.seed)
        util.make_overview(previews, preview_root / "_center_overview.jpg", "center chest placement preview")

    print(f"Print root: {print_root}")
    print(f"Preview root: {preview_root}")
    print(f"Notes: {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
