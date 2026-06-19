from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExternalProject:
    key: str
    name: str
    path: Path
    role: str


EXTERNAL_PROJECTS: tuple[ExternalProject, ...] = (
    ExternalProject("sendgoods", "SendGoods", Path(r"E:\1PythonProject\SendGoods"), "备货采集与拿货表"),
    ExternalProject("posaiimg", "PosAiImg", Path(r"E:\1PythonProject\PosAiImg"), "印花生成、贴图与 xlsx"),
    ExternalProject("putaway", "PutawayAiRobot", Path(r"E:\1PythonProject\PutawayAiRobot"), "自动上架"),
    ExternalProject("applygoods", "ApplyGoods", Path(r"E:\1PythonProject\ApplyGoods"), "申请商品与合规后置"),
)
