from __future__ import annotations

import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class PosAiResourceDefinition:
    key: str
    label: str
    url: str
    install_dir_name: str
    min_free_bytes: int = 0


@dataclass(frozen=True)
class PosAiResourceInstallResult:
    ok: bool
    message: str
    installed_path: str = ""
    archive_path: str = ""


DEFAULT_POSAI_RESOURCE_DEFINITIONS: dict[str, PosAiResourceDefinition] = {
    "comfyui": PosAiResourceDefinition(
        key="comfyui",
        label="ComfyUI",
        url="",
        install_dir_name="ComfyUI",
        min_free_bytes=5 * 1024 * 1024 * 1024,
    ),
    "posai_models": PosAiResourceDefinition(
        key="posai_models",
        label="PosAiImg 模型",
        url="",
        install_dir_name="models",
        min_free_bytes=5 * 1024 * 1024 * 1024,
    ),
}


def install_posai_resource(
    resource: PosAiResourceDefinition,
    *,
    download_dir: str | Path,
    resources_dir: str | Path,
    progress_cb=None,
    should_cancel=None,
) -> PosAiResourceInstallResult:
    url = (resource.url or "").strip()
    if not url:
        return PosAiResourceInstallResult(False, f"{resource.label} 下载地址待配置")

    download_root = Path(download_dir)
    resources_root = Path(resources_dir)
    download_root.mkdir(parents=True, exist_ok=True)
    resources_root.mkdir(parents=True, exist_ok=True)
    if resource.min_free_bytes:
        usage = shutil.disk_usage(resources_root)
        free = usage.free if hasattr(usage, "free") else usage[2]
        if free < resource.min_free_bytes:
            return PosAiResourceInstallResult(
                False,
                f"{resource.label} 安装空间不足：需要至少 {resource.min_free_bytes // (1024 * 1024)} MB 可用空间",
            )

    archive_path = download_root / _archive_name(resource, url)
    try:
        _download(url, archive_path, progress_cb=progress_cb, should_cancel=should_cancel)
        if should_cancel and should_cancel():
            return PosAiResourceInstallResult(False, f"{resource.label} 下载已取消", archive_path=str(archive_path))
        install_dir = resources_root / resource.install_dir_name
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(install_dir)
    except Exception as exc:  # noqa: BLE001 - UI should surface a clear download failure.
        return PosAiResourceInstallResult(False, f"{resource.label} 安装失败：{exc}", archive_path=str(archive_path))

    return PosAiResourceInstallResult(
        True,
        f"{resource.label} 已安装到 {install_dir}",
        installed_path=str(install_dir),
        archive_path=str(archive_path),
    )


def _archive_name(resource: PosAiResourceDefinition, url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name if parsed.path else ""
    if not name.lower().endswith(".zip"):
        name = f"{resource.key}.zip"
    return name


def _download(url: str, dest: Path, *, progress_cb=None, should_cancel=None) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        source = Path(urllib.request.url2pathname(parsed.path))
        total = source.stat().st_size
        copied = 0
        with source.open("rb") as src, dest.open("wb") as out:
            while True:
                if should_cancel and should_cancel():
                    break
                chunk = src.read(64 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                copied += len(chunk)
                if progress_cb:
                    progress_cb(copied, total)
        return

    request = urllib.request.Request(url, headers={"User-Agent": "ConsolePlat PosAi resource installer"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - URL is user/config provided.
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        with dest.open("wb") as out:
            while True:
                if should_cancel and should_cancel():
                    break
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                received += len(chunk)
                if progress_cb:
                    progress_cb(received, total)
