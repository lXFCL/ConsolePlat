from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
COMFY_MODELS = ROOT / "ComfyUI" / "models"

JOBS = [
    {
        "name": "openpose_sdxl",
        "repo": "xinsir/controlnet-openpose-sdxl-1.0",
        "filename": "diffusion_pytorch_model.safetensors",
        "dst": COMFY_MODELS / "controlnet" / "controlnet-openpose-sdxl-1.0.safetensors",
    },
    {
        "name": "ipadapter_sdxl_plus",
        "repo": "h94/IP-Adapter",
        "filename": "sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
        "dst": COMFY_MODELS / "ipadapter" / "ip-adapter-plus_sdxl_vit-h.safetensors",
    },
    {
        "name": "clip_vit_h",
        "repo": "h94/IP-Adapter",
        "filename": "models/image_encoder/model.safetensors",
        "dst": COMFY_MODELS
        / "clip_vision"
        / "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
    },
]

LIMIT_BYTES = 30 * 1024**3


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def remote_size(api: HfApi, repo: str, filename: str) -> int:
    info = api.model_info(repo, files_metadata=True)
    for sibling in info.siblings:
        if sibling.rfilename == filename:
            return int(sibling.size or 0)
    raise FileNotFoundError(f"{repo}:{filename}")


def main() -> None:
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    api = HfApi()
    planned = []
    total = 0

    jobs = JOBS
    if args.only:
        wanted = set(args.only)
        jobs = [job for job in JOBS if job["name"] in wanted]
        missing = wanted - {job["name"] for job in jobs}
        if missing:
            raise SystemExit(f"Unknown model name(s): {', '.join(sorted(missing))}")

    for job in jobs:
        dst = job["dst"]
        if dst.exists() and dst.stat().st_size > 0:
            size = dst.stat().st_size
            planned.append((job, size, True))
            continue
        size = remote_size(api, job["repo"], job["filename"])
        total += size
        planned.append((job, size, False))

    print("Planned new download:", human_size(total))
    for job, size, exists in planned:
        status = "exists" if exists else "download"
        print(f"- {status}: {job['dst'].name} ({human_size(size)})")

    if total > LIMIT_BYTES:
        raise SystemExit(f"Refusing to download more than 30GB: {human_size(total)}")

    for job, _, exists in planned:
        dst = job["dst"]
        if exists:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {job['repo']}:{job['filename']}")
        src = hf_hub_download(repo_id=job["repo"], filename=job["filename"])
        shutil.copy2(src, dst)
        print(f"Saved {dst} ({human_size(dst.stat().st_size)})")


if __name__ == "__main__":
    main()
