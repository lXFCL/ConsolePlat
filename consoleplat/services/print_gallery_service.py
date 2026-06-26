from __future__ import annotations

import shutil
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import quote


PRINT_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
Downloader = Callable[[str, Path], bool]


@dataclass(frozen=True)
class PrintGalleryResult:
    copied: int = 0
    missing_skus: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    copied_files: list[str] = field(default_factory=list)


def collect_print_gallery(
    *,
    skus: list[str],
    source: str,
    local_dir: str | Path,
    github_raw_base_url: str,
    target_dir: str | Path,
    downloader: Downloader | None = None,
) -> PrintGalleryResult:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    local = Path(local_dir) if str(local_dir or "").strip() else None
    if local is not None:
        local.mkdir(parents=True, exist_ok=True)

    unique_skus = _unique_skus(skus)
    copied_files: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    download = downloader or _download_file
    normalized_source = source if source in {"local", "github"} else "local"

    for sku in unique_skus:
        found = _find_local_print(local, sku, warnings)
        if found is None and normalized_source == "github":
            found = _download_github_print(
                sku=sku,
                local_dir=local,
                github_raw_base_url=github_raw_base_url,
                downloader=download,
            )
        if found is None:
            missing.append(sku)
            continue
        destination = target / found.name
        shutil.copy2(found, destination)
        copied_files.append(str(destination))

    return PrintGalleryResult(
        copied=len(copied_files),
        missing_skus=missing,
        warnings=warnings,
        copied_files=copied_files,
    )


def _unique_skus(skus: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for sku in skus:
        clean = str(sku or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _find_local_print(local_dir: Path | None, sku: str, warnings: list[str]) -> Path | None:
    if local_dir is None or not local_dir.exists():
        return None
    matches = [
        path
        for path in local_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in PRINT_IMAGE_SUFFIXES and path.stem == sku
    ]
    if not matches:
        return None
    newest = max(matches, key=lambda path: path.stat().st_mtime)
    if len(matches) > 1:
        warnings.append(f"{sku} 命中多张印花，已使用最新文件：{newest}")
    return newest


def _download_github_print(
    *,
    sku: str,
    local_dir: Path | None,
    github_raw_base_url: str,
    downloader: Downloader,
) -> Path | None:
    if local_dir is None:
        return None
    base_url = (github_raw_base_url or "").rstrip("/")
    if not base_url:
        return None
    for suffix in PRINT_IMAGE_SUFFIXES:
        destination = local_dir / f"{sku}{suffix}"
        url = f"{base_url}/{quote(sku)}{suffix}"
        if downloader(url, destination):
            return destination
        destination.unlink(missing_ok=True)
    return None


def _download_file(url: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ConsolePlat/print-gallery"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if getattr(response, "status", 200) != 200:
                return False
            destination.write_bytes(response.read())
            return destination.exists() and destination.stat().st_size > 0
    except Exception:  # noqa: BLE001 - missing GitHub image should not stop export.
        return False
