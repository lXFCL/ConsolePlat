from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_release_package import should_include_path


RUNTIME_ROOTS = ("modules", "resources")
EXE_EXCLUDED_DIRS = {"tests", "test", "__pycache__"}


def copy_runtime_payload(root: Path, output_dir: Path) -> None:
    for name in RUNTIME_ROOTS:
        source_root = root / name
        if not source_root.exists():
            continue
        for source in source_root.rglob("*"):
            if not source.is_file():
                continue
            if EXE_EXCLUDED_DIRS.intersection(source.relative_to(root).parts):
                continue
            if not should_include_path(source, root=root, package_kind="portable"):
                continue
            destination = output_dir / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    required_dirs = [
        "modules/PutawayAiRobot/data/pic/1",
        "modules/PutawayAiRobot/data/pic/2",
        "resources/prints",
        "runtime/outputs",
        "runtime/data",
        "runtime/downloads/posai",
    ]
    for relative in required_dirs:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)


def build_exe(root: Path, env_name: str = "flask") -> Path:
    root = root.resolve()
    dist_dir = root / "dist"
    output_dir = dist_dir / "ConsolePlat"
    build_dir = root / "build" / "pyinstaller"

    if output_dir.exists():
        shutil.rmtree(output_dir, onerror=_remove_readonly)
    if build_dir.exists():
        shutil.rmtree(build_dir, onerror=_remove_readonly)

    command = [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        env_name,
        "python",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--workpath",
        str(build_dir),
        "--distpath",
        str(dist_dir),
        str(root / "ConsolePlat.spec"),
    ]
    subprocess.run(command, cwd=root, check=True)
    copy_runtime_payload(root, output_dir)
    return output_dir / "ConsolePlat.exe"


def _remove_readonly(func, path, _exc_info) -> None:
    os.chmod(path, 0o700)
    func(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="构建精简的 ConsolePlat Windows EXE")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--env", default="flask")
    args = parser.parse_args()
    executable = build_exe(Path(args.root), args.env)
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
