from __future__ import annotations

from pathlib import Path

from scripts.build_release_package import _ensure_portable_dirs, should_include_path


def test_release_packaging_excludes_generated_and_sensitive_paths():
    root = Path("E:/repo")
    excluded = [
        root / ".git" / "config",
        root / ".browser-profile" / "Default" / "Cookies",
        root / "modules" / "PosAiImg" / "ComfyUI" / "main.py",
        root / "modules" / "PosAiImg" / ".hf_cache" / "model.bin",
        root / "modules" / "PosAiImg" / "批量贴图结果" / "old.png",
        root / "modules" / "ApplyGoods" / "settings.json",
        root / "modules" / "PutawayAiRobot" / "browser_profile" / "Default" / "Cookies",
        root / "modules" / "PutawayAiRobot" / "data" / "pic" / "1" / "SZW-3534.png",
        root / "modules" / "PutawayAiRobot" / "data" / "batch.xlsx",
        root / "modules" / "SendGoods" / "outputs" / "old.xlsx",
        root / "dist" / "old.zip",
        root / "build" / "artifact",
        root / "pytest_ai_transparent.log",
    ]

    for path in excluded:
        assert should_include_path(path, root=root, package_kind="portable") is False


def test_release_packaging_includes_required_source_and_templates():
    root = Path("E:/repo")
    included = [
        root / "main.py",
        root / "consoleplat" / "config.py",
        root / "modules" / "SendGoods" / "1.cleaned.xlsx",
        root / "modules" / "PutawayAiRobot" / "browser_dom_automation.py",
        root / "modules" / "ApplyGoods" / "temu_goods.py",
        root / "modules" / "PosAiImg" / "tools" / "comfy_print_batch.py",
        root / "resources" / "prints" / "README.md",
    ]

    for path in included:
        assert should_include_path(path, root=root, package_kind="portable") is True


def test_release_packaging_keeps_empty_putaway_image_directories(tmp_path):
    _ensure_portable_dirs(tmp_path)

    assert (tmp_path / "modules" / "PutawayAiRobot" / "data" / "pic" / "1" / ".gitkeep").is_file()
    assert (tmp_path / "modules" / "PutawayAiRobot" / "data" / "pic" / "2" / ".gitkeep").is_file()
