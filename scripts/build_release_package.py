from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from pathlib import Path


VERSION = "1.7.1"
PORTABLE_NAME = f"ConsolePlat-v{VERSION}-portable"
PRINTS_NAME = f"ConsolePlat-prints-v{VERSION}"

EXCLUDED_NAMES = {
    ".git",
    ".idea",
    ".trae",
    ".pytest_cache",
    ".browser-profile",
    "browser_profile",
    "__pycache__",
    ".hf_cache",
    ".buildvenv",
    ".venv",
    "venv",
    "build",
    "dist",
    "generated",
    "cache",
    ".cache",
    "tmp",
    "temp",
    "outputs",
    "downloads",
    "log",
    "logs",
    "ComfyUI",
    "_consoleplat_ai_edits",
    "_consoleplat_tests",
    "批量贴图结果",
    "印花图_透明底",
    "衣物对应的xlsx",
    "爆款印花知识库",
    "模特图-干净",
    "模特图-预览",
    "临时输出",
    "raw",
    "replacements",
    "sheets_raw",
    "最终透明底",
    "最终产品图",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".tmp", ".bak", ".swp", ".spec"}
PORTABLE_POSAI_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
EXCLUDED_FILES = {"settings.json", ".env"}
EXCLUDED_FILE_PREFIXES = {"build_exe", "tools_test", "~$"}


def should_include_path(path: str | Path, *, root: str | Path, package_kind: str = "portable") -> bool:
    path = Path(path)
    root = Path(root)
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = set(rel.parts)
    name = path.name
    if name in EXCLUDED_FILES or name.startswith(".env."):
        return False
    if any(name.startswith(prefix) for prefix in EXCLUDED_FILE_PREFIXES):
        return False
    if any(part in EXCLUDED_NAMES for part in parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if package_kind == "portable" and _is_putaway_business_data(rel):
        return False
    if package_kind == "portable" and "图库" in parts:
        return False
    if package_kind == "portable" and "PosAiImg" in parts and path.suffix.lower() in PORTABLE_POSAI_IMAGE_SUFFIXES:
        return False
    return True


def _is_putaway_business_data(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 3 and parts[:3] == ("modules", "PutawayAiRobot", "data")


def build_release(root: Path, dist_dir: Path | None = None) -> tuple[Path, Path]:
    root = root.resolve()
    dist_dir = (dist_dir or root / "dist").resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)
    stage = root / "build" / PORTABLE_NAME
    if stage.exists():
        shutil.rmtree(stage, onerror=_remove_readonly)
    stage.mkdir(parents=True)

    for source in _iter_portable_sources(root):
        rel = source.relative_to(root)
        if not should_include_path(source, root=root, package_kind="portable"):
            continue
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

    _ensure_portable_dirs(stage)
    portable_zip = dist_dir / f"{PORTABLE_NAME}.zip"
    prints_zip = dist_dir / f"{PRINTS_NAME}.zip"
    _write_zip(stage, portable_zip, root_name=PORTABLE_NAME)
    _write_prints_zip(root, prints_zip)
    return portable_zip, prints_zip


def _iter_portable_sources(root: Path):
    include_roots = [
        root / "main.py",
        root / "README.md",
        root / "AGENTS.md",
        root / "requirements.txt",
        root / "assets",
        root / "chrome-extension",
        root / "consoleplat",
        root / "modules",
        root / "scripts",
        root / "resources",
        root / "启动ConsolePlat.bat",
    ]
    for entry in include_roots:
        if not entry.exists():
            continue
        if entry.is_file():
            yield entry
            continue
        yield from (path for path in entry.rglob("*") if path.is_file())


def _ensure_portable_dirs(stage: Path) -> None:
    keep_dirs = [
        "modules/SendGoods",
        "modules/PosAiImg",
        "modules/PutawayAiRobot/data/pic/1",
        "modules/PutawayAiRobot/data/pic/2",
        "modules/ApplyGoods",
        "resources/prints",
        "runtime/outputs",
        "runtime/data",
        "runtime/downloads/posai",
    ]
    for rel in keep_dirs:
        target = stage / rel
        target.mkdir(parents=True, exist_ok=True)
        if rel.startswith("runtime/") or rel.startswith("modules/PutawayAiRobot/data/"):
            (target / ".gitkeep").write_text("", encoding="utf-8")
    readme = stage / "resources" / "prints" / "README.md"
    if not readme.exists():
        readme.write_text(
            f"完整图集请从 GitHub Release 下载 {PRINTS_NAME}.zip 后解压到本目录。\n",
            encoding="utf-8",
        )


def _write_zip(source_dir: Path, output: Path, *, root_name: str) -> None:
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, Path(root_name) / path.relative_to(source_dir))


def _write_prints_zip(root: Path, output: Path) -> None:
    if output.exists():
        output.unlink()
    candidates = [
        root.parent / "PosAiImg" / "图库",
        root / "resources" / "prints",
    ]
    source = next((candidate for candidate in candidates if candidate.exists()), None)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if source is None:
            zf.writestr(f"{PRINTS_NAME}/README.md", "未找到完整图集目录，请自行配置 PosAiImg 图库。\n")
            return
        for path in source.rglob("*"):
            if path.is_file() and should_include_path(path, root=source, package_kind="prints"):
                zf.write(path, Path(PRINTS_NAME) / path.relative_to(source))


def _remove_readonly(func, path, _exc_info) -> None:
    os.chmod(path, 0o700)
    func(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--dist", default="")
    args = parser.parse_args()
    root = Path(args.root)
    dist = Path(args.dist) if args.dist else None
    portable, prints = build_release(root, dist)
    print(portable)
    print(prints)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
