from __future__ import annotations

from pathlib import Path


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def main() -> None:
    root = Path.home() / ".cache" / "huggingface" / "hub"
    print(f"Root: {root}")
    print(f"Exists: {root.exists()}")
    if not root.exists():
        return
    files = [path for path in root.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    print(f"Total: {human_size(total)}")
    for path in sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:30]:
        print(f"{human_size(path.stat().st_size)}  {path}")


if __name__ == "__main__":
    main()
