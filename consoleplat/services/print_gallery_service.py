from __future__ import annotations

import json
import random
import shutil
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import quote, unquote, urlparse


PRINT_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
Downloader = Callable[[str, Path], bool]
JsonFetcher = Callable[[str], object]
Chooser = Callable[[Sequence[dict]], dict]


@dataclass(frozen=True)
class PrintGalleryResult:
    copied: int = 0
    missing_skus: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    copied_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GithubPrintTestResult:
    ok: bool
    message: str
    saved_path: str = ""
    source_url: str = ""


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


def pull_random_github_print(
    *,
    github_url: str,
    local_gallery_dir: str | Path,
    fetch_json: JsonFetcher | None = None,
    downloader: Downloader | None = None,
    chooser: Chooser | None = None,
    now: Callable[[], datetime] | None = None,
) -> GithubPrintTestResult:
    clean_url = str(github_url or "").strip()
    if not clean_url:
        return GithubPrintTestResult(False, "请先填写 GitHub 图集地址")

    local_root = Path(local_gallery_dir)
    try:
        local_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 - UI needs a readable error instead of a traceback.
        return GithubPrintTestResult(False, f"本地图集目录无法创建：{exc}")

    try:
        repo = _parse_github_gallery_url(clean_url, fetch_json or _fetch_json)
        files = _list_github_print_files(repo, fetch_json or _fetch_json)
    except ValueError as exc:
        return GithubPrintTestResult(False, str(exc))
    except Exception as exc:  # noqa: BLE001 - network/API failures should be shown as UI text.
        return GithubPrintTestResult(False, f"GitHub 图集访问失败：{exc}")

    image_files = [
        item
        for item in files
        if str(item.get("type") or "") == "file"
        and str(item.get("name") or "").lower().endswith(PRINT_IMAGE_SUFFIXES)
        and str(item.get("download_url") or "")
    ]
    if not image_files:
        return GithubPrintTestResult(False, "GitHub 目录下没有可下载的图片")

    selected = (chooser or random.choice)(image_files)
    filename = str(selected.get("name") or "").strip()
    source_url = str(selected.get("download_url") or "").strip()
    if not filename or not source_url:
        return GithubPrintTestResult(False, "GitHub 图片信息不完整")

    stamp = (now or datetime.now)()
    destination = (
        local_root
        / "github拉取"
        / _classify_print_filename(filename)
        / str(stamp.year)
        / f"{stamp.month}月"
        / "最终透明底"
        / filename
    )
    download = downloader or _download_file
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        ok = download(source_url, destination)
        if not ok or not destination.exists() or destination.stat().st_size <= 0:
            destination.unlink(missing_ok=True)
            return GithubPrintTestResult(False, "下载失败或文件为空", source_url=source_url)
    except Exception as exc:  # noqa: BLE001 - clean up partial files and report in UI.
        destination.unlink(missing_ok=True)
        return GithubPrintTestResult(False, f"下载失败：{exc}", source_url=source_url)

    return GithubPrintTestResult(True, f"已下载：{destination}", saved_path=str(destination), source_url=source_url)


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


@dataclass(frozen=True)
class _GithubGalleryRepo:
    owner: str
    repo: str
    branch: str
    path: str


def _parse_github_gallery_url(url: str, fetch_json: JsonFetcher) -> _GithubGalleryRepo:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if host == "github.com":
        if len(parts) < 2:
            raise ValueError("GitHub 仓库地址不完整")
        owner, repo = parts[0], parts[1]
        branch = ""
        gallery_path = "prints"
        if len(parts) >= 5 and parts[2] in {"tree", "blob"}:
            branch = parts[3]
            gallery_path = "/".join(parts[4:]) or "prints"
        if not branch:
            branch = _fetch_default_branch(owner, repo, fetch_json)
        return _GithubGalleryRepo(owner=owner, repo=repo, branch=branch, path=gallery_path.strip("/") or "prints")

    if host == "raw.githubusercontent.com":
        if len(parts) < 4:
            raise ValueError("GitHub Raw 地址不完整")
        owner, repo, branch = parts[0], parts[1], parts[2]
        gallery_path = "/".join(parts[3:]) or "prints"
        return _GithubGalleryRepo(owner=owner, repo=repo, branch=branch, path=gallery_path.strip("/") or "prints")

    raise ValueError("仅支持 github.com 仓库地址或 raw.githubusercontent.com Raw 地址")


def _fetch_default_branch(owner: str, repo: str, fetch_json: JsonFetcher) -> str:
    data = fetch_json(f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}")
    if isinstance(data, dict):
        branch = str(data.get("default_branch") or "").strip()
        if branch:
            return branch
    return "main"


def _list_github_print_files(repo: _GithubGalleryRepo, fetch_json: JsonFetcher) -> list[dict]:
    path = "/".join(quote(part) for part in repo.path.split("/") if part)
    url = (
        f"https://api.github.com/repos/{quote(repo.owner)}/{quote(repo.repo)}"
        f"/contents/{path}?ref={quote(repo.branch)}"
    )
    data = fetch_json(url)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and data.get("message"):
        raise ValueError(str(data.get("message")))
    raise ValueError("GitHub 返回的目录内容格式不正确")


def _classify_print_filename(filename: str) -> str:
    stem = Path(filename).stem.upper()
    if stem.startswith("BO-"):
        return "BO"
    if stem.startswith("SZW-"):
        return "SZW"
    return "通用素材"


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


def _fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "ConsolePlat/print-gallery"})
    with urllib.request.urlopen(request, timeout=20) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError(f"HTTP {getattr(response, 'status', '?')}")
        return json.loads(response.read().decode("utf-8"))
