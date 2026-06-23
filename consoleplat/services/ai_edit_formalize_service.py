from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook, load_workbook
from PIL import Image

from consoleplat.services.putaway_sync_service import PutawaySyncSummary, sync_putaway_assets


POSAI_ROOT = Path("E:/1PythonProject/PosAiImg")
if str(POSAI_ROOT) not in sys.path:
    sys.path.append(str(POSAI_ROOT))

try:
    from tools.tshirt_print_tool import Placement, composite_one  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from tshirt_print_tool import Placement, composite_one  # type: ignore


STORE_NAMES = {"BO": "YUHAOBO", "SZW": "YUHOOBO"}
PRODUCT_CATEGORY = "T恤"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_MODEL_DIR = POSAI_ROOT / "模特图/干净"
DEFAULT_WHITE_MODEL_NAMES = ["主图5-白.jpg", "主图6-白.jpg"]
DEFAULT_BLACK_MODEL_NAMES = ["主图1-黑.jpg", "主图2-黑.jpg"]
WHITE_COLOR_NAME = "白"
BLACK_COLOR_NAME = "黑"
HEADER_ROW = ["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"]


@dataclass(frozen=True)
class AIEditFormalizeSummary:
    ok: bool
    renamed_outputs: list[str]
    product_outputs: list[str]
    xlsx_path: str
    putaway: PutawaySyncSummary | None
    color_assignments: dict[str, str] | None = None
    message: str = ""


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def choose_white_model(model_dir: Path = DEFAULT_MODEL_DIR) -> Path:
    for name in DEFAULT_WHITE_MODEL_NAMES:
        path = model_dir / name
        if path.exists():
            return path
    for path in sorted(model_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and "白" in path.stem:
            return path
    raise FileNotFoundError(f"未找到白色模特图：{model_dir}")


def choose_black_model(model_dir: Path = DEFAULT_MODEL_DIR) -> Path:
    for name in DEFAULT_BLACK_MODEL_NAMES:
        path = model_dir / name
        if path.exists():
            return path
    for path in sorted(model_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and "黑" in path.stem:
            return path
    raise FileNotFoundError(f"未找到黑色模特图：{model_dir}")


def _subject_brightness(print_path: Path) -> float:
    image = Image.open(print_path).convert("RGBA")
    pixels = image.load()
    weighted_total = 0.0
    alpha_total = 0.0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha <= 0:
                continue
            brightness = red * 0.299 + green * 0.587 + blue * 0.114
            weight = alpha / 255.0
            weighted_total += brightness * weight
            alpha_total += weight
    if alpha_total <= 0:
        return 255.0
    return weighted_total / alpha_total


def choose_mockup_model_for_print(print_path: Path) -> str:
    return "white" if _subject_brightness(print_path) < 128 else "black"


def choose_mockup_models_for_batch(print_paths: list[Path]) -> dict[Path, str]:
    if not print_paths:
        return {}
    brightness_pairs = [(path, _subject_brightness(path)) for path in print_paths]
    average_brightness = sum(value for _path, value in brightness_pairs) / len(brightness_pairs)
    if average_brightness >= 210:
        return {path: "black" for path, _value in brightness_pairs}
    if average_brightness <= 45:
        return {path: "white" for path, _value in brightness_pairs}
    return {path: ("white" if brightness < 128 else "black") for path, brightness in brightness_pairs}


def _assignment_to_color_name(assignment: str) -> str:
    return WHITE_COLOR_NAME if assignment == "white" else BLACK_COLOR_NAME


def rename_split_outputs(
    *,
    split_paths: list[Path],
    final_transparent_dir: Path,
    prefix: str,
    start_number: int,
) -> list[Path]:
    final_transparent_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, source in enumerate(split_paths):
        sku = f"{prefix}-{start_number + index}"
        target = final_transparent_dir / f"{sku}.png"
        target.unlink(missing_ok=True)
        shutil.copy2(source, target)
        outputs.append(target)
    return outputs


def build_product_images(
    *,
    print_paths: list[Path],
    final_product_dir: Path,
    product_title: str,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> tuple[list[Path], dict[str, str]]:
    final_product_dir.mkdir(parents=True, exist_ok=True)
    white_model = choose_white_model(model_dir)
    black_model = choose_black_model(model_dir)
    placement = Placement(
        center_x=0.50,
        center_y=0.43,
        width=0.30,
        opacity=0.92,
        rotation=0.0,
        shadow_strength=0.32,
        wave_strength=0.012,
        remove_white_bg=False,
    )
    assignments = choose_mockup_models_for_batch(print_paths)
    outputs: list[Path] = []
    color_assignments: dict[str, str] = {}
    for print_path in print_paths:
        sku = print_path.stem
        output = final_product_dir / safe_filename(f"{sku}_{product_title}.png")
        output.unlink(missing_ok=True)
        assignment = assignments.get(print_path) or "black"
        model = white_model if assignment == "white" else black_model
        color_assignments[sku] = _assignment_to_color_name(assignment)
        composite_one(model, print_path, output, placement)
        outputs.append(output)
    return outputs, color_assignments


def _load_existing_color_assignments(xlsx_path: Path) -> dict[str, str]:
    if not xlsx_path.exists():
        return {}
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb.active
        assignments: dict[str, str] = {}
        row = 2
        while True:
            sku = ws[f"D{row}"].value
            if not sku:
                break
            color = ws[f"E{row}"].value
            if color:
                assignments[str(sku)] = str(color)
            row += 1
        return assignments
    finally:
        wb.close()


def _collect_color_assignments_from_transparent_dir(final_transparent_dir: Path) -> dict[str, str]:
    if not final_transparent_dir.exists():
        return {}
    assignments: dict[str, str] = {}
    for path in sorted(final_transparent_dir.glob("*.png")):
        if not path.is_file():
            continue
        assignments[path.stem] = _assignment_to_color_name(choose_mockup_model_for_print(path))
    return assignments


def backfill_xlsx_colors_from_transparent_dir(
    *,
    xlsx_path: Path,
    final_transparent_dir: Path,
) -> int:
    if not xlsx_path.exists() or not final_transparent_dir.exists():
        return 0
    inferred_colors = _collect_color_assignments_from_transparent_dir(final_transparent_dir)
    if not inferred_colors:
        return 0

    wb = load_workbook(xlsx_path)
    try:
        ws = wb.active
        updated = 0
        row = 2
        while True:
            sku = ws[f"D{row}"].value
            if not sku:
                break
            color_cell = ws[f"E{row}"]
            if not color_cell.value:
                inferred = inferred_colors.get(str(sku))
                if inferred:
                    color_cell.value = inferred
                    updated += 1
            row += 1
        if updated:
            wb.save(xlsx_path)
        return updated
    finally:
        wb.close()


def write_xlsx(
    *,
    xlsx_path: Path,
    prefix: str,
    start_number: int,
    count: int,
    product_title: str,
    color_assignments: dict[str, str] | None = None,
) -> Path:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    merged_color_assignments = _load_existing_color_assignments(xlsx_path)
    if color_assignments:
        merged_color_assignments.update(color_assignments)

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADER_ROW)
    store_name = STORE_NAMES[prefix]
    for number in range(start_number, start_number + count):
        sku = f"{prefix}-{number}"
        ws.append([store_name, PRODUCT_CATEGORY, product_title, sku, merged_color_assignments.get(sku, "")])
    for col, width in {"A": 16, "B": 12, "C": 90, "D": 18, "E": 10}.items():
        ws.column_dimensions[col].width = width
    wb.save(xlsx_path)
    wb.close()
    return xlsx_path


def formalize_ai_edit_outputs(
    *,
    split_paths: list[Path],
    final_transparent_dir: Path,
    final_product_dir: Path,
    xlsx_path: Path,
    putaway_data_dir: Path,
    prefix: str,
    start_number: int,
    product_title: str,
    xlsx_batch_start_number: int | None = None,
    xlsx_batch_count: int | None = None,
) -> AIEditFormalizeSummary:
    renamed_outputs = rename_split_outputs(
        split_paths=split_paths,
        final_transparent_dir=final_transparent_dir,
        prefix=prefix,
        start_number=start_number,
    )
    product_outputs, color_assignments = build_product_images(
        print_paths=renamed_outputs,
        final_product_dir=final_product_dir,
        product_title=product_title,
    )
    write_xlsx(
        xlsx_path=xlsx_path,
        prefix=prefix,
        start_number=int(xlsx_batch_start_number or start_number),
        count=max(1, int(xlsx_batch_count or len(renamed_outputs))),
        product_title=product_title,
        color_assignments=color_assignments,
    )
    putaway = sync_putaway_assets(
        source_images_dir=final_product_dir,
        source_xlsx_path=xlsx_path,
        target_data_dir=putaway_data_dir,
        replace_image_names={path.name for path in product_outputs},
    )
    ok = bool(renamed_outputs) and bool(product_outputs) and xlsx_path.exists() and putaway.ok
    return AIEditFormalizeSummary(
        ok=ok,
        renamed_outputs=[str(path) for path in renamed_outputs],
        product_outputs=[str(path) for path in product_outputs],
        xlsx_path=str(xlsx_path),
        putaway=putaway,
        color_assignments=color_assignments,
        message=(
            f"正式模式后处理完成：透明底 {len(renamed_outputs)} 张，产品图 {len(product_outputs)} 张，XLSX {xlsx_path.name}"
            if ok
            else "正式模式后处理失败"
        ),
    )
