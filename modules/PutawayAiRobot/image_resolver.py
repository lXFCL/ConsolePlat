import os
from typing import Optional

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def _project_base_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _pick_first_existing(base_dir: str, stem: str, exts):
    for ext in exts:
        p = os.path.join(base_dir, f"{stem}{ext}")
        if os.path.exists(p):
            return p
    return ""


def _iter_image_files(base_dir: str, exts):
    try:
        items = list(os.scandir(base_dir))
    except FileNotFoundError:
        return []
    except Exception:
        return []
    ext_set = {e.lower() for e in exts}
    files = []
    for it in items:
        try:
            if not it.is_file():
                continue
        except Exception:
            continue
        stem, ext = os.path.splitext(it.name)
        if ext.lower() in ext_set:
            files.append((stem, ext.lower(), it.path))
    return files


def _sku_match_rank(stem: str, sku: str):
    stem_l = (stem or "").strip().lower()
    sku_l = (sku or "").strip().lower()
    if not stem_l or not sku_l:
        return None
    if stem_l == sku_l:
        return (0, len(stem_l), stem_l)
    if stem_l.startswith(sku_l):
        rest = stem_l[len(sku_l) :]
        if not rest:
            return (0, len(stem_l), stem_l)
        if rest[0] in {"_", "-", " ", "　", ".", "(", "[", "【"}:
            return (1, len(stem_l), stem_l)
        return (2, len(stem_l), stem_l)
    pos = stem_l.find(sku_l)
    if pos >= 0:
        return (3, pos, len(stem_l), stem_l)
    return None


def _pick_sku_containing_file(base_dir: str, sku: str, exts):
    matches = []
    for stem, _ext, path in _iter_image_files(base_dir, exts):
        rank = _sku_match_rank(stem, sku)
        if rank is not None:
            matches.append((rank, path))
    if not matches:
        return ""
    matches.sort(key=lambda x: x[0])
    return matches[0][1]


def validate_sku_images(skus, base_dir: Optional[str] = None):
    base_dir = base_dir or os.path.join(_project_base_dir(), "data", "pic", "1")
    normalized = []
    seen = set()
    for sku in skus or []:
        s = (sku or "").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(s)

    image_files = _iter_image_files(base_dir, IMAGE_EXTS)
    result = {
        "base_dir": base_dir,
        "exists": os.path.isdir(base_dir),
        "image_count": len(image_files),
        "missing": [],
        "matched": {},
    }
    if not result["exists"] or not image_files:
        result["missing"] = normalized
        return result

    for sku in normalized:
        p = _pick_first_existing(base_dir, sku, IMAGE_EXTS) or _pick_sku_containing_file(base_dir, sku, IMAGE_EXTS)
        if p:
            result["matched"][sku] = p
        else:
            result["missing"].append(sku)
    return result


def resolve_sku_image_path(sku: str, base_dir: Optional[str] = None):
    sku = (sku or "").strip()
    if not sku:
        raise RuntimeError("产品序列号为空")
    base_dir = base_dir or os.path.join(_project_base_dir(), "data", "pic", "1")
    p = _pick_first_existing(base_dir, sku, IMAGE_EXTS)
    if p:
        return p
    p = _pick_sku_containing_file(base_dir, sku, IMAGE_EXTS)
    if p:
        return p
    raise RuntimeError(f"未找到序列号对应图片：{sku}（支持完整文件名或文件名包含货号，目录：{base_dir}）")


def _normalize_color_key(color: str):
    c = (color or "").strip()
    if not c:
        return ""
    if "白" in c or c.lower() in {"white", "w"}:
        return "白"
    if "黑" in c or c.lower() in {"black", "b"}:
        return "黑"
    return c


def resolve_color_pack_paths(color: str, base_dir: Optional[str] = None):
    key = _normalize_color_key(color)
    if key not in {"白", "黑"}:
        raise RuntimeError(f"颜色不支持：{color}（仅支持：白/黑）")
    base_dir = base_dir or os.path.join(_project_base_dir(), "data", "pic", "2")
    paths = []
    missing = []
    for i in range(1, 5):
        stem = f"{key}{i}"
        p = _pick_first_existing(base_dir, stem, IMAGE_EXTS)
        if p:
            paths.append(p)
        else:
            missing.append(stem)
    if missing:
        raise RuntimeError(f"缺少颜色素材图：{', '.join(missing)}（目录：{base_dir}）")
    return paths


def resolve_variant_image_paths(sku: str, color: str):
    first = resolve_sku_image_path(sku)
    rest = resolve_color_pack_paths(color)
    return [first, *rest]
