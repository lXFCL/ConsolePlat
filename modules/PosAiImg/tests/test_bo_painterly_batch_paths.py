from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_bo_painterly_master_batch import (
    batch_name,
    batch_paths,
    parse_product_filename,
    project_paths,
)


def test_bo_print_and_xlsx_paths_are_grouped_by_prefix() -> None:
    paths = batch_paths("BO", 1421, 50, "2026-06-17")

    assert paths.raw_dir == Path("图库") / "BO" / "2026" / "6月" / batch_name("BO", 1421, 50, "2026-06-17") / "测试"
    assert paths.print_dir == Path("图库") / "BO" / "2026" / "6月" / batch_name("BO", 1421, 50, "2026-06-17") / "最终透明底"
    assert paths.mockup_test_dir == Path("批量贴图结果") / "BO" / "2026" / "6月" / batch_name("BO", 1421, 50, "2026-06-17") / "测试"
    assert paths.mockup_dir == Path("批量贴图结果") / "BO" / "2026" / "6月" / batch_name("BO", 1421, 50, "2026-06-17") / "最终产品图"
    assert paths.xlsx_path == Path("衣物对应的xlsx") / "BO" / f"{batch_name('BO', 1421, 50, '2026-06-17')}.xlsx"


def test_project_paths_converts_all_batch_paths_to_workspace_paths() -> None:
    paths = project_paths(batch_paths("BO", 1421, 50, "2026-06-17"))

    assert paths.print_dir.is_absolute()
    assert paths.raw_dir.is_absolute()
    assert paths.mockup_dir.is_absolute()
    assert paths.mockup_test_dir.is_absolute()
    assert paths.prompt_file.is_absolute()
    assert paths.xlsx_path.is_absolute()


def test_overview_belongs_to_mockup_test_dir_not_final_dir() -> None:
    paths = batch_paths("BO", 1421, 50, "2026-06-17")

    assert paths.mockup_test_dir / "_overview.jpg" != paths.mockup_dir / "_overview.jpg"
    assert (paths.mockup_test_dir / "_overview.jpg").parts[-2] == "测试"
    assert (paths.mockup_dir / "BO-1421_title.png").parts[-2] == "最终产品图"


def test_parse_product_filename_extracts_xlsx_fields() -> None:
    parsed = parse_product_filename(
        "BO-1421_夏季白色仿油彩名画睡莲池塘印花T恤 圆领短袖 透气微弹针织上衣 日常休闲百搭.png"
    )

    assert parsed == (
        "夏季白色仿油彩名画睡莲池塘印花T恤 圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "BO-1421",
        "白",
    )
