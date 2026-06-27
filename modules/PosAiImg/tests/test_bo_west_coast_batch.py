from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.generate_bo_west_coast_batch import (  # noqa: E402
    STYLE_NAME,
    WEST_COAST_THEMES,
    batch_name,
    batch_paths,
    selected_theme_range,
    product_title,
)


def test_west_coast_batch_paths_use_new_gallery_structure() -> None:
    paths = batch_paths("BO", 1521, 45, "2026-06-17")
    name = batch_name("BO", 1521, 45, "2026-06-17")

    assert name == f"{STYLE_NAME}_BO-1521-BO-1565_2026-06-17"
    assert paths.raw_dir == Path("图库") / "BO" / "2026" / "6月" / name / "测试"
    assert paths.print_dir == Path("图库") / "BO" / "2026" / "6月" / name / "最终透明底"
    assert paths.mockup_test_dir == Path("批量贴图结果") / "BO" / "2026" / "6月" / name / "测试"
    assert paths.mockup_dir == Path("批量贴图结果") / "BO" / "2026" / "6月" / name / "最终产品图"
    assert paths.xlsx_path == Path("衣物对应的xlsx") / "BO" / f"{name}.xlsx"


def test_west_coast_theme_count_matches_formal_batch_size() -> None:
    assert len(WEST_COAST_THEMES) == 45
    assert len({theme.keyword for theme in WEST_COAST_THEMES}) == 45


def test_selected_theme_range_can_resume_inside_batch() -> None:
    selected = selected_theme_range(batch_start=1521, only_start=1552, only_count=14)

    assert selected[0][0] == 31
    assert selected[0][1] == 1552
    assert selected[-1][0] == 44
    assert selected[-1][1] == 1565
    assert len(selected) == 14


def test_west_coast_product_title_matches_bo_rules() -> None:
    title = product_title("白色", "棕榈日落", 0)

    assert title.startswith("夏季白色西海岸棕榈日落印花T恤 ")
    assert "情侣" not in title
    assert "男" not in title
    assert "女" not in title
