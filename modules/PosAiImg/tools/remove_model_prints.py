from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage as ndi
from skimage import color, measure, morphology


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "\u6a21\u7279\u56fe-\u9884\u89c8"
DEFAULT_EXISTING_CLEAN_DIR = ROOT / "\u53bb\u5370\u82b1\u7ed3\u679c"
DEFAULT_OUTPUT_DIR = ROOT / "\u6a21\u7279\u56fe_\u53bb\u5370\u82b1\u5e72\u51c0"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class JobStats:
    source: Path
    output: Path
    base: str
    masked_ratio: float


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def load_rgb(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def largest_central_component(mask: np.ndarray) -> np.ndarray:
    labels = measure.label(mask)
    if labels.max() == 0:
        return mask

    h, w = mask.shape
    center = np.array([h * 0.48, w * 0.50])
    best_label = 0
    best_score = -1.0
    for region in measure.regionprops(labels):
        minr, minc, maxr, maxc = region.bbox
        if maxr < h * 0.15 or minr > h * 0.90:
            continue
        cy, cx = region.centroid
        distance = np.linalg.norm((np.array([cy, cx]) - center) / np.array([h, w]))
        area_score = region.area / float(h * w)
        score = area_score - distance * 0.10
        if score > best_score:
            best_score = score
            best_label = region.label
    if best_label == 0:
        best_label = max(measure.regionprops(labels), key=lambda r: r.area).label
    return labels == best_label


def estimate_base(rgb: np.ndarray) -> str:
    hsv = color.rgb2hsv(rgb / 255.0)
    value = hsv[..., 2] * 255.0
    saturation = hsv[..., 1] * 255.0
    h, w = value.shape
    roi = np.zeros((h, w), dtype=bool)
    roi[int(h * 0.16) : int(h * 0.82), int(w * 0.16) : int(w * 0.84)] = True
    neutral = saturation < 95
    dark = roi & neutral & (value < 95)
    light = roi & neutral & (value > 155)
    return "black" if dark.sum() >= light.sum() else "white"


def make_garment_mask(rgb: np.ndarray, base: str) -> np.ndarray:
    hsv = color.rgb2hsv(rgb / 255.0)
    value = hsv[..., 2] * 255.0
    saturation = hsv[..., 1] * 255.0
    h, w = value.shape

    if base == "black":
        seed = (value < 120) & (saturation < 145)
    else:
        seed = (value > 130) & (saturation < 95)

    torso_window = np.zeros((h, w), dtype=bool)
    torso_window[int(h * 0.08) : int(h * 0.90), int(w * 0.04) : int(w * 0.96)] = True
    seed &= torso_window

    seed = morphology.binary_closing(seed, morphology.disk(max(5, min(h, w) // 90)))
    seed = morphology.remove_small_objects(seed, min_size=max(300, (h * w) // 900))
    seed = largest_central_component(seed)
    seed = ndi.binary_fill_holes(seed)
    seed = morphology.binary_closing(seed, morphology.disk(max(6, min(h, w) // 70)))
    return seed


def make_print_mask(rgb: np.ndarray, garment: np.ndarray, base: str) -> np.ndarray:
    hsv = color.rgb2hsv(rgb / 255.0)
    value = hsv[..., 2] * 255.0
    saturation = hsv[..., 1] * 255.0
    lab = color.rgb2lab(rgb / 255.0)
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    h, w = value.shape

    work_area = np.zeros((h, w), dtype=bool)
    work_area[int(h * 0.13) : int(h * 0.84), int(w * 0.07) : int(w * 0.93)] = True

    if base == "black":
        mask = (value > 82) | ((saturation > 70) & (value > 48)) | (chroma > 32)
        # Leave skin, hair, and warm background alone when they leak into the shirt component.
        mask &= ~((hsv[..., 0] > 0.03) & (hsv[..., 0] < 0.12) & (saturation > 55) & (value > 105))
    else:
        mask = (value < 158) | ((saturation > 42) & (value < 248)) | (chroma > 24)
        # Preserve soft gray folds on white fabric.
        mask &= ~((saturation < 28) & (value > 112))

    mask &= garment & work_area
    mask = morphology.remove_small_objects(mask, min_size=max(20, (h * w) // 18000))
    mask = morphology.binary_closing(mask, morphology.disk(max(2, min(h, w) // 350)))
    mask = morphology.binary_dilation(mask, morphology.disk(max(4, min(h, w) // 190)))

    # Include narrow dark or bright anti-aliased outlines around the detected print.
    near = morphology.binary_dilation(mask, morphology.disk(max(3, min(h, w) // 240))) & garment & work_area
    if base == "black":
        fringe = near & ((value > 58) | (saturation > 45))
    else:
        fringe = near & ((value < 205) | (saturation > 30))
    mask |= fringe

    mask = morphology.remove_small_holes(mask, area_threshold=max(64, (h * w) // 5000))
    mask = fill_print_components(mask)
    return mask


def fill_print_components(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    labels = measure.label(mask)
    if labels.max() == 0:
        return mask

    expanded = mask.copy()
    min_area = max(45, (h * w) // 25000)
    for region in measure.regionprops(labels):
        if region.area < min_area:
            continue
        minr, minc, maxr, maxc = region.bbox
        cy, cx = region.centroid
        nx = cx / max(1, w)
        ny = cy / max(1, h)
        # Keep this tied to the plausible chest/print zone; it avoids text in
        # the corner, sweaters held at the side, and pants/skin below the shirt.
        if not (0.22 <= nx <= 0.78 and 0.14 <= ny <= 0.70):
            continue
        if maxr - minr > h * 0.62 or maxc - minc > w * 0.82:
            continue
        pad = max(5, int(max(maxr - minr, maxc - minc) * 0.035))
        top = max(0, minr - pad)
        left = max(0, minc - pad)
        bottom = min(h, maxr + pad)
        right = min(w, maxc + pad)
        local = labels[top:bottom, left:right] == region.label
        radius = max(2, min(local.shape) // 45)
        local = morphology.binary_dilation(local, morphology.disk(radius))
        local = morphology.binary_closing(local, morphology.disk(max(2, radius)))
        local = ndi.binary_fill_holes(local)
        if local.sum() / float(local.size) > 0.88 and local.size > h * w * 0.08:
            continue
        expanded[top:bottom, left:right] |= local
    return expanded


def normalized_blur(values: np.ndarray, known: np.ndarray, sigma: float) -> np.ndarray:
    known_f = known.astype(np.float32)
    numerator = ndi.gaussian_filter(values.astype(np.float32) * known_f, sigma=sigma)
    denominator = ndi.gaussian_filter(known_f, sigma=sigma)
    fallback = float(np.median(values[known])) if np.any(known) else float(np.median(values))
    return np.where(denominator > 1e-4, numerator / np.maximum(denominator, 1e-4), fallback)


def fill_with_fabric(rgb: np.ndarray, garment: np.ndarray, mask: np.ndarray, base: str) -> np.ndarray:
    clean = garment & ~mask
    if clean.sum() < max(200, rgb.shape[0] * rgb.shape[1] // 300):
        clean = ~mask

    h, w = mask.shape
    sigma = max(14.0, min(h, w) / 18.0)
    rgb_f = rgb.astype(np.float32)
    luma = 0.2126 * rgb_f[..., 0] + 0.7152 * rgb_f[..., 1] + 0.0722 * rgb_f[..., 2]

    smooth_luma = normalized_blur(luma, clean, sigma=sigma)
    local_luma = ndi.gaussian_filter(luma, sigma=max(5.0, min(h, w) / 70.0))
    broad_luma = ndi.gaussian_filter(luma, sigma=max(18.0, min(h, w) / 23.0))
    wrinkle = np.clip(local_luma - broad_luma, -18, 18)
    filled_luma = smooth_luma + wrinkle * 0.35

    median_rgb = np.median(rgb_f[clean], axis=0) if np.any(clean) else np.median(rgb_f.reshape(-1, 3), axis=0)
    median_luma = float(0.2126 * median_rgb[0] + 0.7152 * median_rgb[1] + 0.0722 * median_rgb[2])
    neutral = median_rgb / max(median_luma, 1.0)
    neutral = np.clip(neutral, 0.55, 1.55)

    fill = filled_luma[..., None] * neutral[None, None, :]
    if base == "black":
        fill = np.minimum(fill, np.percentile(rgb_f[clean], 92, axis=0)[None, None, :] + 18)
        fill = np.clip(fill, 2, 92)
    else:
        fill = np.maximum(fill, np.percentile(rgb_f[clean], 8, axis=0)[None, None, :] - 14)
        fill = np.clip(fill, 135, 255)

    out = rgb_f.copy()
    out[mask] = fill[mask]

    # A small blur only inside the repaired area removes posterized islands while
    # leaving the surrounding person/background untouched.
    repaired = ndi.gaussian_filter(out, sigma=(0.8, 0.8, 0))
    feather = ndi.gaussian_filter(mask.astype(np.float32), sigma=1.7)[..., None]
    out = out * (1.0 - feather) + repaired * feather
    return np.clip(out, 0, 255).astype(np.uint8)


def inpaint_prints(img: Image.Image) -> tuple[Image.Image, str, float]:
    max_side = 1150
    scale = min(1.0, max_side / max(img.size))
    if scale < 1.0:
        work = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    else:
        work = img.copy()

    rgb = np.asarray(work).astype(np.uint8)
    base = estimate_base(rgb)
    garment = make_garment_mask(rgb, base)
    mask = make_print_mask(rgb, garment, base)

    # If the automatic mask is implausibly tiny, fall back to the expected print zone.
    ratio = float(mask.sum() / mask.size)
    if ratio < 0.006:
        h, w = mask.shape
        fallback = np.zeros_like(mask)
        fallback[int(h * 0.28) : int(h * 0.62), int(w * 0.25) : int(w * 0.75)] = True
        mask |= garment & fallback
        ratio = float(mask.sum() / mask.size)

    arr = np.asarray(work).astype(np.float32) / 255.0
    fixed = fill_with_fabric(rgb, garment, mask, base)
    fixed_img = Image.fromarray(fixed, "RGB")

    # Feather the repaired area so the edge does not read as a hard patch.
    feather = Image.fromarray((mask.astype(np.uint8) * 255), "L").filter(ImageFilter.GaussianBlur(radius=1.6))
    blended = Image.composite(fixed_img, work, feather)

    if scale < 1.0:
        blended = blended.resize(img.size, Image.Resampling.LANCZOS)
    return blended, base, ratio


def copy_existing_clean(existing_dir: Path, output_dir: Path) -> list[Path]:
    copied: list[Path] = []
    for path in list_images(existing_dir):
        target = output_dir / path.name
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def make_contact_sheet(paths: list[Path], output_path: Path) -> None:
    tiles: list[Image.Image] = []
    for path in paths:
        img = load_rgb(path)
        img.thumbnail((220, 260), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (240, 300), "white")
        tile.paste(img, ((240 - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((10, 274), path.name, fill=(0, 0, 0))
        tiles.append(tile)

    if not tiles:
        return
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 240, rows * 300), (235, 235, 235))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % cols) * 240, (index // cols) * 300))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch remove T-shirt prints from model photos.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--existing-clean-dir", type=Path, default=DEFAULT_EXISTING_CLEAN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--copy-existing", action="store_true")
    parser.add_argument("--contact-sheet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    stats: list[JobStats] = []
    for path in list_images(args.input_dir):
        img = load_rgb(path)
        clean, base, masked_ratio = inpaint_prints(img)
        output_path = args.output_dir / f"{path.stem}-clean.png"
        clean.save(output_path)
        stats.append(JobStats(path, output_path, base, masked_ratio))
        print(f"{path.name} -> {output_path.name} base={base} mask={masked_ratio:.3f}", flush=True)

    copied = copy_existing_clean(args.existing_clean_dir, args.output_dir) if args.copy_existing else []
    for path in copied:
        print(f"copied existing -> {path.name}", flush=True)

    output_paths = [p for p in list_images(args.output_dir) if not p.name.startswith("_")]
    if args.contact_sheet:
        make_contact_sheet(output_paths, args.output_dir / "_contact_sheet.jpg")

    print(f"done: generated={len(stats)} copied={len(copied)} output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
