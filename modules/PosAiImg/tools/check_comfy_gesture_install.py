from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT / "ComfyUI"

PATHS = [
    COMFY / "custom_nodes" / "ComfyUI-Manager",
    COMFY / "custom_nodes" / "comfyui_controlnet_aux",
    COMFY / "custom_nodes" / "ComfyUI_IPAdapter_plus",
    COMFY / "custom_nodes" / "ComfyUI-Impact-Pack",
    COMFY / "models" / "controlnet",
    COMFY / "models" / "clip_vision",
    COMFY / "models" / "ipadapter",
]

MODELS = [
    COMFY / "models" / "controlnet" / "controlnet-openpose-sdxl-1.0.safetensors",
    COMFY
    / "models"
    / "clip_vision"
    / "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
    COMFY / "models" / "ipadapter" / "ip-adapter-plus_sdxl_vit-h.safetensors",
]

MODULES = [
    "torch",
    "cv2",
    "mediapipe",
    "onnxruntime",
    "segment_anything",
    "skimage",
    "transformers",
    "git",
]


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main() -> None:
    print("Directories")
    for path in PATHS:
        print(f"- {path}: exists={path.exists()} size={human_size(dir_size(path))}")

    print("\nModels")
    total_models = 0
    for path in MODELS:
        size = path.stat().st_size if path.exists() else 0
        total_models += size
        print(f"- {path.name}: exists={path.exists()} size={human_size(size)}")
    print(f"Total selected models: {human_size(total_models)}")

    print("\nPython modules")
    for module in MODULES:
        print(f"- {module}: {bool(importlib.util.find_spec(module))}")


if __name__ == "__main__":
    main()
