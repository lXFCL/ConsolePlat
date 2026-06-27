from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from consoleplat.config import resolve_project_dir
from consoleplat.paths import modules_root


@dataclass(frozen=True)
class ExternalProject:
    key: str
    name: str
    path: Path
    role: str


def _project_path(key: str, name: str) -> Path:
    return resolve_project_dir(key) or modules_root() / name


EXTERNAL_PROJECTS: tuple[ExternalProject, ...] = (
    ExternalProject("sendgoods", "SendGoods", _project_path("sendgoods", "SendGoods"), "purchase export"),
    ExternalProject("posaiimg", "PosAiImg", _project_path("posaiimg", "PosAiImg"), "image generation"),
    ExternalProject("putaway", "PutawayAiRobot", _project_path("putaway", "PutawayAiRobot"), "putaway automation"),
    ExternalProject("applygoods", "ApplyGoods", _project_path("applygoods", "ApplyGoods"), "compliance workflow"),
)
