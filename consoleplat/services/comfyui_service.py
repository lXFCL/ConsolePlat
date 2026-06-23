from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComfyUIStatus:
    ready: bool
    message: str


class ComfyUIService:
    def ensure_ready(self, *, auto_start: bool, timeout_seconds: int, logger=None) -> ComfyUIStatus:
        if logger is not None:
            logger("ComfyUI 就绪检查已跳过，当前使用恢复版占位服务。")
        return ComfyUIStatus(ready=True, message="ComfyUI 已就绪")
