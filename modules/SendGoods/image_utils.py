from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageOps


def to_high_res_url(url: str) -> str:
    """Return Temu/Kwcdn original image URL when a thumbnail URL is given."""
    if not url:
        return ""
    return url.split("?", 1)[0]


def _extension_from_url(url: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return ".jpg"


def safe_image_name(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}{_extension_from_url(url)}"


def download_image(url: str, output_dir: Path, timeout: int = 20) -> Path:
    high_res_url = to_high_res_url(url)
    if not high_res_url:
        raise ValueError("图片地址为空")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / safe_image_name(high_res_url)
    if target.exists() and target.stat().st_size > 0:
        return target

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    response = requests.get(high_res_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def make_excel_thumbnail(source: Path, output_dir: Path, max_width: int = 112, max_height: int = 126) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}_excel.png"
    if target.exists() and target.stat().st_size > 0:
        return target

    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (max_width, max_height), "white")
        x = (max_width - img.width) // 2
        y = (max_height - img.height) // 2
        canvas.paste(img, (x, y))
        canvas.save(target, "PNG")
    return target


def prepare_excel_image(source: Path, output_dir: Path, max_long_side: int = 1400) -> Path:
    """Normalize an image for Excel while keeping it much sharper than page thumbnails."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}_excel_full.png"
    if target.exists() and target.stat().st_size > 0:
        return target

    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((max_long_side, max_long_side), Image.Resampling.LANCZOS)
        img.save(target, "PNG")
    return target


def fit_dimensions(source: Path, max_width: int = 112, max_height: int = 126) -> tuple[int, int]:
    with Image.open(source) as img:
        width, height = img.size
    if width <= 0 or height <= 0:
        return max_width, max_height
    scale = min(max_width / width, max_height / height)
    return max(1, int(width * scale)), max(1, int(height * scale))
